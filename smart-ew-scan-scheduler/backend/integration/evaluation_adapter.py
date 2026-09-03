"""
evaluation_adapter.py

GROUND TRUTH LIVES HERE AND ONLY HERE (besides offline training).
Nothing in this file is ever passed to a Scheduler or Predictor -- it
only reads `environment.ground_truth_log` (Person 1) to score what
already happened, using Person 2's real metric definitions
(ew_scheduler.backend.evaluation.metrics.SimulationResult /
comparison.compare_results), reused unmodified.

Why a new update loop instead of reusing P2's experiment_runner.py
directly: `experiment_runner.run_simulation()` drives its OWN toy
detector (a flat noise_prob coin flip) instead of Person 1's real
RFEnvironment/DetectionModel -- it's P2's standalone test harness, not
meant to sit downstream of a real simulation. Rather than re-simulate
detection a second time, `LiveMetricsTracker.update()` below replays
the SAME burst-tracking / Pd / Pfa bookkeeping P2's experiment_runner
performs (see its steps 2-8), but driven by P1's real, already-decided
detection outcomes, one real tick at a time. The metric *definitions*
(SimulationResult's pd/pfa/intercept_rate/avg_intercept_time/
scan_efficiency properties) are P2's real, unmodified code.
"""
import sys
from .repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

from metrics import SimulationResult  # noqa: E402  (P2, path registered above)
from comparison import compare_results  # noqa: E402


class LiveMetricsTracker:
    """
    Streaming equivalent of experiment_runner.run_simulation()'s
    aggregation loop, fed one real P1 tick at a time. Wraps a real
    SimulationResult -- all metric properties (pd, pfa, intercept_rate,
    avg_intercept_time, scan_efficiency, bursts_intercepted) are P2's
    own code, completely unmodified.
    """

    def __init__(self, scheduler_name: str):
        self.result = SimulationResult(scheduler_name=scheduler_name)
        self._open_bursts: dict[int, dict] = {}  # band -> {"start": t, "intercepted": bool}

    def update(self, obs, ground_truth_records_this_tick: list) -> None:
        """
        obs: a Person 1 Observation for this tick (already produced by
             the real receiver/detection model -- we do not re-decide
             detection here).
        ground_truth_records_this_tick: Person 1 GroundTruthRecord
             entries for this exact time step (across ALL emitters/bands,
             not just the scanned one) -- used ONLY to label this
             already-completed tick for evaluation.
        """
        t = obs.time
        active_bands_now = {
            r.band for r in ground_truth_records_this_tick
            if r.active and r.band is not None
        }

        r = self.result
        r.total_steps += 1
        if obs.detected:
            r.total_hits += 1
        else:
            r.total_misses += 1

        r.decision_log.append({
            "time": t,
            "band": obs.scanned_band,
            "detected": obs.detected,
            "ground_truth_active": obs.scanned_band in active_bands_now,
        })

        # Every currently-active (band, time) cell counts once toward
        # total_active_steps, matching experiment_runner's
        # `total_active_steps = len(gt_active)` (a set of all active
        # (band, time) pairs across the whole spectrum, not just the
        # scanned band).
        r.total_active_steps += len(active_bands_now)

        # Burst open/close bookkeeping across ALL bands (a burst can be
        # missed entirely if never scanned while active).
        for band in active_bands_now:
            if band not in self._open_bursts:
                self._open_bursts[band] = {"start": t, "intercepted": False}
            burst = self._open_bursts[band]
            if not burst["intercepted"] and band == obs.scanned_band and obs.detected:
                burst["intercepted"] = True
                r.intercept_times.append(t - burst["start"])

        for band in list(self._open_bursts.keys()):
            if band not in active_bands_now:
                if not self._open_bursts[band]["intercepted"]:
                    r.missed_bursts += 1
                del self._open_bursts[band]

    def finalize(self) -> None:
        """
        BUG FIX: previously, a burst still active (ground-truth-wise) at
        the moment a bounded run ended was left sitting in
        self._open_bursts forever -- never counted as intercepted or
        missed. This under-counted missed_bursts and made
        (bursts_intercepted + missed_bursts) not sum to the true total
        number of bursts that occurred.

        This matches P2's own semantics exactly (experiment_runner.py):
        `extract_bursts()` closes every burst at whatever the last known
        active time was for that band -- it does not require a burst to
        have already ended before counting it -- and the aggregation
        loop after `run_simulation()`'s main loop unconditionally counts
        every non-intercepted burst as missed:

            for band_bursts in bursts.values():
                for burst in band_bursts:
                    if burst["intercepted"]:
                        result.intercept_times.append(...)
                    else:
                        result.missed_bursts += 1

        i.e. a burst still open when the observed window ends is, by
        P2's own definition, resolved as either intercepted (if it was)
        or missed (if it wasn't) -- there is no third "still pending,
        don't count" case in P2's semantics. finalize() reproduces that
        same unconditional resolution for whatever bursts are still open
        in THIS tracker.

        Call this once at the definitive end of a bounded run: the
        /comparison endpoint calls it after each strategy's fixed-
        duration loop; the live orchestrator calls it on pause() so a
        user who stops a live session also sees conclusive final numbers
        for that session. Idempotent -- a second call sees an already-
        empty pending-burst set and does nothing. Reads only ground
        truth already captured into self._open_bursts by previous
        update() calls -- introduces no new ground-truth access, and
        never touches the live decision path (Scheduler/Predictor are
        not involved here at all).
        """
        for band in list(self._open_bursts.keys()):
            if not self._open_bursts[band]["intercepted"]:
                self.result.missed_bursts += 1
            del self._open_bursts[band]


def ground_truth_records_at(ground_truth_log: list, t: int) -> list:
    """Small helper: filter P1's full ground_truth_log down to one tick's
    records. Evaluation-only use (see module docstring)."""
    return [rec for rec in ground_truth_log if rec.time == t]


def build_comparison_table(results: list) -> "object":
    """Thin pass-through to Person 2's real compare_results(), so the
    comparison endpoint doesn't need to import ew_scheduler paths itself."""
    return compare_results(results)


def simulation_result_to_metrics(result: SimulationResult):
    """
    Converts a real (unmodified) P2 SimulationResult into P3's frontend-
    facing Metrics schema. Only place two things are handled:

    1. avg_intercept_time is float('inf') by P2's own definition when no
       burst has been intercepted yet (metrics.py: "if not
       self.intercept_times: return float('inf')"). float('inf') is not
       valid JSON (JavaScript's JSON.parse rejects the literal
       "Infinity") -- we substitute 0.0 for display only. The real
       SimulationResult object (used for internal comparison/printing)
       is untouched.
    2. prediction_accuracy has no direct P2 counterpart; scan_efficiency
       ("fraction of scans that caught a real active transmission") is
       the closest real, non-fabricated analogue, so it's used directly.
    """
    from schemas.simulation import Metrics  # local import avoids a cycle at module load

    avg_intercept = result.avg_intercept_time
    if avg_intercept == float("inf"):
        avg_intercept = 0.0

    return Metrics(
        ticks_run=result.total_steps,
        hits=result.total_hits,
        misses=result.total_misses,
        detection_probability=round(result.pd, 4),
        false_alarm_probability=round(result.pfa, 4),
        avg_intercept_time=round(avg_intercept, 2),
        intercept_rate=round(result.intercept_rate, 4),
        prediction_accuracy=round(result.scan_efficiency, 4),
    )
