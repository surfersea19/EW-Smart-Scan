"""
scheduler_adapter.py

THE core interface adapter for this integration.

Person 1's SimulationEngine drives the only clock and calls:
    scheduler.choose_band(t: int, observation_log: list, spectrum: Spectrum) -> int

Person 2's schedulers implement a different interface:
    scheduler.select_band(bands: list[int], history_manager: BandHistoryManager,
                           current_time: int) -> int

SchedulerAdapter implements P1's interface by delegating to a P2
scheduler instance, translating observations via observation_adapter as
it goes. It is the ONLY class that touches both P1's Observation objects
and P2's BandHistoryManager.

GROUND TRUTH ISOLATION: this class never receives, imports, or
references RFEnvironment or GroundTruthRecord. It only ever sees
`observation_log` (receiver-observed data, per P1's Scheduler ABC
contract) and `spectrum` (structural config, not ground truth -- see
P1 HANDOFF.md #8). This is the same guarantee P1's own Scheduler ABC
already enforces by its signature; this adapter does not weaken it.

REASONING WITHOUT MODIFYING P2: SmartScheduler.select_band() computes
an internal score for the winning band already, but only returns the
band index -- it doesn't expose the full breakdown for display, and
explain_decision() only prints, it doesn't return data. Rather than
duplicating SmartScheduler's scoring formula here (which would risk
silently drifting out of sync with the real one if P2 ever retunes it),
this adapter calls SmartScheduler's own (private-by-convention)
`_score_band` method directly to reconstruct the same breakdown the
real decision used. Python does not enforce access modifiers, so this
requires no modification to smart_scheduler.py. If P2 ever renames or
removes these internals, this degrades gracefully to a generic reason
string (see _update_reasoning) rather than raising -- reasoning display
is diagnostic only and must never affect the live decision path.
"""
from typing import Optional

from .repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

from history_manager import BandHistoryManager  # noqa: E402  (P2, path registered above)


class SchedulerAdapter:
    """Implements Person 1's Scheduler interface by delegating to a
    Person 2 BaseScheduler. Pass an instance of this directly as the
    `scheduler=` argument to P1's SimulationEngine."""

    def __init__(self, p2_scheduler, max_history_per_band: int = 200):
        self.p2_scheduler = p2_scheduler
        self._max_history = max_history_per_band
        self._hm = BandHistoryManager(max_history_per_band=max_history_per_band)
        self._ingested = 0

        # Diagnostic/display-only state, read by the orchestrator after
        # each choose_band() call. Never fed back into any decision logic.
        self.last_predictions: dict = {}
        self.last_breakdown: list = []
        self.last_reason: Optional[str] = None

    def reset(self) -> None:
        """Called between simulation runs (new scenario, or re-running
        the same scenario under a different strategy for comparison)."""
        self._hm = BandHistoryManager(max_history_per_band=self._max_history)
        self._ingested = 0
        self.last_predictions = {}
        self.last_breakdown = []
        self.last_reason = None
        self.p2_scheduler.reset()

    # ------------------------------------------------------------------
    # P1's Scheduler interface
    # ------------------------------------------------------------------

    def choose_band(self, t: int, observation_log: list, spectrum) -> int:
        self._ingest_new_observations(observation_log)

        bands = spectrum.list_bands()
        prev_last_scanned = getattr(self.p2_scheduler, "_last_scanned", None)

        chosen = self.p2_scheduler.select_band(bands, self._hm, current_time=t)

        self._update_reasoning(bands, t, prev_last_scanned, chosen)
        return chosen

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ingest_new_observations(self, observation_log: list) -> None:
        # observation_log is P1's full history to date; only translate
        # and ingest what's new since our last call.
        from .observation_adapter import p1_observation_to_p2_dict

        for obs in observation_log[self._ingested:]:
            self._hm.ingest(p1_observation_to_p2_dict(obs))
        self._ingested = len(observation_log)

    def _update_reasoning(self, bands, t, prev_last_scanned, chosen) -> None:
        predictor = getattr(self.p2_scheduler, "predictor", None)
        score_fn = getattr(self.p2_scheduler, "_score_band", None)
        has_last_scanned = hasattr(self.p2_scheduler, "_last_scanned")

        if predictor is None or score_fn is None:
            # SequentialScheduler / RandomScheduler / any future non-ML
            # scheduler: no scoring internals to reflect on. Describe
            # plainly and accurately instead of fabricating a reason.
            self.last_predictions = {}
            self.last_breakdown = []
            self.last_reason = self._describe_non_ml_scheduler()
            return

        try:
            predictions = predictor.predict_all_bands(bands, self._hm, t)
            self.last_predictions = dict(predictions)

            # select_band() already advanced self.p2_scheduler._last_scanned
            # to `chosen` before returning. To reconstruct the score
            # breakdown AS IT WAS SEEN during the real decision (which
            # compared candidate bands against the PREVIOUS last-scanned
            # band, not this tick's outcome), temporarily restore it,
            # score, then put the real post-call value back exactly as
            # select_band left it.
            if has_last_scanned:
                self.p2_scheduler._last_scanned = prev_last_scanned

            breakdown = [
                {"band": band, "probability": prob, "score": score_fn(band, prob, self._hm, t)}
                for band, prob in predictions.items()
            ]

            if has_last_scanned:
                self.p2_scheduler._last_scanned = chosen

            breakdown.sort(key=lambda r: r["score"], reverse=True)
            self.last_breakdown = breakdown

            # select_band()'s non-exploration branch always picks
            # argmax(scores). If the real chosen band isn't the top of
            # our reconstructed breakdown, the real call must have taken
            # the epsilon-exploration branch instead (we can't observe
            # that branch directly since it's an internal RNG draw).
            top = breakdown[0] if breakdown else None
            explored = top is not None and top["band"] != chosen

            if explored:
                self.last_reason = "exploration (least recently scanned band)"
            else:
                chosen_row = next((r for r in breakdown if r["band"] == chosen), None)
                if chosen_row:
                    self.last_reason = (
                        f"predicted activity {chosen_row['probability']:.0%}, "
                        f"score {chosen_row['score']:.2f}"
                    )
                else:
                    self.last_reason = "smart scheduler decision"

        except Exception:
            # Reasoning/display is best-effort only. A failure here must
            # never surface as a failure of the live decision path --
            # choose_band() has already returned `chosen` successfully.
            self.last_predictions = {}
            self.last_breakdown = []
            self.last_reason = "smart scheduler decision"

    def _describe_non_ml_scheduler(self) -> str:
        name = type(self.p2_scheduler).__name__
        if name == "SequentialScheduler":
            return "sequential sweep"
        if name == "RandomScheduler":
            return "random exploration"
        return name
