"""
orchestrator.py -- the only place that calls Person 1 + Person 2's real
code together, now against the real modules instead of mocks.

CLOCK OWNERSHIP: Person 1's SimulationEngine owns the only clock. This
orchestrator calls `engine.step_once()` exactly once per tick() call --
it does not advance time itself, and does not call environment.step()
directly anywhere.

GROUND TRUTH ISOLATION: `environment.ground_truth_log` is read ONLY in
this file's `tick()` method, ONLY to feed `LiveMetricsTracker.update()`
for evaluation. It is never passed to `scheduler_adapter` or anything
inside integration/scheduler_adapter.py.

ARCHITECTURE NOTE ON "NEXT BAND": the earlier mock-based design showed
a "next scan" band chosen ahead of when it would actually be scanned.
Person 1's real SimulationEngine.step() decides a band AND scans it in
the same atomic call (see simulation_engine.py) -- there is no
observable moment where a decision exists before its execution, short
of peeking inside step() (not possible without modifying P1's code,
which is out of scope). WSDelta.next_band is therefore populated with
THIS tick's chosen band (== current_band) rather than a genuine
look-ahead; the frontend's "Scheduler Decision" panel is relabeled
accordingly (see frontend changes) to describe why this tick's band was
chosen, not to promise a preview of the future.
"""
from schemas.simulation import (
    ScenarioConfig,
    SimulationState,
    ObservationView,
    ActiveEmitterInfo,
    WSDelta,
)
from schemas.prediction import BandPrediction
from schemas.scheduler import PredictedActivity

from services import simulation_service, scheduler_service
from services.prediction_service import PredictorNotAvailableError
from integration.evaluation_adapter import (
    LiveMetricsTracker,
    ground_truth_records_at,
    simulation_result_to_metrics,
)

TOP_K_PREDICTIONS = 5
TOP_K_PREDICTED_ACTIVITY = 3


class SimulationOrchestrator:
    def __init__(self):
        self.state = SimulationState()
        self.scheduler_adapter = None
        self.live_metrics: LiveMetricsTracker | None = None
        self.playback_speed: int = 5

    def reset(self, scenario: ScenarioConfig) -> None:
        """
        May raise services.prediction_service.PredictorNotAvailableError
        if scenario.strategy == "smart_ml" and no trained model exists.
        This is intentionally NOT caught here -- see api/simulation_routes.py,
        which turns it into a clear HTTP error instead of silently
        training on the spot.
        """
        self.scheduler_adapter = scheduler_service.build_scheduler_adapter(
            scenario.strategy,
            scheduler_seed=scenario.scheduler_seed,
            model_name=scenario.model_name,
        )

        engine = simulation_service.get_simulation_engine()
        engine.reset(scenario, self.scheduler_adapter)
        # engine.reset() overwrites scenario.num_bands with the real
        # spectrum's band count -- read it back rather than trusting the
        # pre-reset value.
        self.scenario = engine.scenario
        self.playback_speed = getattr(scenario, "playback_speed", 5)

        self.live_metrics = LiveMetricsTracker(scheduler_name=scenario.strategy)
        self.state = SimulationState(
            scenario=self.scenario,
            playback_speed=self.playback_speed,
            running=False,
            completed=False,
        )

    def set_playback_speed(self, speed: int) -> None:
        self.playback_speed = max(1, speed)
        self.state.playback_speed = self.playback_speed
        if hasattr(self, "scenario") and self.scenario is not None:
            self.scenario.playback_speed = self.playback_speed

    def start(self) -> None:
        engine = simulation_service.get_simulation_engine()
        if engine.engine is not None and engine.current_time >= self.scenario.duration:
            self.state.running = False
            self.state.completed = True
            return
        self.state.running = True
        self.state.completed = False

    def pause(self) -> None:
        self.state.running = False
        # BUG FIX: resolve any bursts still open (ground-truth active,
        # not yet intercepted) so the metrics shown after stopping are
        # conclusive rather than silently omitting whatever was pending
        # -- see LiveMetricsTracker.finalize(). Safe to call repeatedly;
        # if the user resumes afterward and a band goes active again,
        # a fresh burst simply opens as normal.
        if self.live_metrics is not None:
            self.live_metrics.finalize()
            self.state.metrics = simulation_result_to_metrics(self.live_metrics.result)

    def tick(self) -> WSDelta:
        engine = simulation_service.get_simulation_engine()
        if engine.current_time >= self.scenario.duration:
            self.pause()
            self.state.completed = True
            return WSDelta(
                time=self.state.simulation_time,
                current_band=self.state.current_band,
                detected=self.state.last_observation.detected if self.state.last_observation else False,
                power=self.state.last_observation.measured_power_db if self.state.last_observation else None,
                top_predictions=self.state.predictions,
                next_band=self.state.next_band,
                scheduler_reason=self.state.scheduler_reason,
                predicted_activity=self.state.predicted_activity,
                running=False,
                completed=True,
                metrics=self.state.metrics,
                playback_speed=self.playback_speed,
                active_emitters=self.state.active_emitters,
            )

        observations = engine.step_once()  # real P1 decision + scan, atomic

        environment = engine.environment
        for obs in observations:
            gt_records = ground_truth_records_at(environment.ground_truth_log, obs.time)
            self.live_metrics.update(obs, gt_records)

        last_obs = observations[-1]

        # Extract simulated RF environment activity for this tick for waterfall visualization ONLY.
        # This ground-truth activity is never passed to the ML predictor or scheduler.
        latest_gt = ground_truth_records_at(environment.ground_truth_log, last_obs.time)
        active_emitters = [
            ActiveEmitterInfo(
                band=r.band,
                emitter_id=r.emitter_id,
                emitter_type=r.emitter_type,
                power_db=r.power_db,
            )
            for r in latest_gt
            if r.active and r.band is not None
        ]

        # DURATION ENFORCEMENT (bug fix): P1's SimulationEngine has no
        # concept of a target run length -- it just runs however many
        # decisions you call step() for. P3's ScenarioConfig.duration is
        # therefore enforced entirely on the P3 side, by comparing
        # against P1's own real clock (`engine.current_time`, the same
        # value already surfaced to the user as `simulation_time`) after
        # each decision completes. This introduces no second clock: the
        # check only ever *reads* P1's existing clock, never advances or
        # substitutes it. Because P1's engine can only be observed at
        # decision boundaries (not modified to preempt mid-decision,
        # which is out of scope), the actual stop point is the first
        # decision boundary at or after `duration` raw ticks -- with the
        # default receiver config (dwell_time=1, tuning_time=0) this
        # lands exactly at `duration`; a nonzero tuning_time could
        # overshoot by at most tuning_time + dwell_time - 1 ticks.
        #
        # Stopping reuses pause() itself (not a separate code path), so
        # metrics finalization is identical to a manual /stop -- see
        # pause()'s own finalize() call above.
        if engine.current_time >= self.scenario.duration:
            self.pause()
            self.state.completed = True
        else:
            self.state.completed = False

        predictions = self._top_predictions()
        predicted_activity = self._predicted_activity(predictions)
        # Read AFTER the duration check above: if this tick just
        # triggered pause()'s finalize(), this must reflect the
        # finalized numbers, not the pre-finalize snapshot.
        metrics = simulation_result_to_metrics(self.live_metrics.result)

        # Update authoritative state (for the /simulation/state REST route)
        self.state.simulation_time = last_obs.time
        self.state.current_band = last_obs.scanned_band
        self.state.last_observation = ObservationView(
            time=last_obs.time,
            scanned_band=last_obs.scanned_band,
            detected=last_obs.detected,
            measured_power_db=last_obs.measured_power_db,
            pulse_width_us=last_obs.pulse_width_us,
            pri_us=last_obs.pri_us,
        )
        self.state.predictions = predictions
        self.state.next_band = last_obs.scanned_band  # see module docstring
        self.state.scheduler_reason = self.scheduler_adapter.last_reason
        self.state.predicted_activity = predicted_activity
        self.state.metrics = metrics
        self.state.playback_speed = self.playback_speed
        self.state.active_emitters = active_emitters

        return WSDelta(
            time=last_obs.time,
            current_band=last_obs.scanned_band,
            detected=last_obs.detected,
            power=last_obs.measured_power_db,
            top_predictions=predictions,
            next_band=last_obs.scanned_band,
            scheduler_reason=self.scheduler_adapter.last_reason,
            predicted_activity=predicted_activity,
            running=self.state.running,  # reflects an auto-stop from THIS tick, if any
            completed=self.state.completed,
            metrics=metrics,
            playback_speed=self.playback_speed,
            active_emitters=active_emitters,
        )

    def _top_predictions(self) -> list[BandPrediction]:
        preds = self.scheduler_adapter.last_predictions  # {} for non-ML schedulers
        ranked = sorted(preds.items(), key=lambda kv: kv[1], reverse=True)
        return [
            BandPrediction(band=band, probability=round(prob, 4))
            for band, prob in ranked[:TOP_K_PREDICTIONS]
        ]

    def _predicted_activity(self, predictions: list[BandPrediction]) -> list[PredictedActivity]:
        return [
            PredictedActivity(rank=i + 1, band=p.band, probability=p.probability)
            for i, p in enumerate(predictions[:TOP_K_PREDICTED_ACTIVITY])
        ]


_orchestrator: SimulationOrchestrator | None = None


def get_orchestrator() -> SimulationOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SimulationOrchestrator()
        # BUG FIX: previously defaulted to "sequential" here, independently
        # of the frontend's own default ("smart_ml") -- two hardcoded
        # constants in two places that could (and did) drift apart. The
        # backend's initial strategy now matches the frontend default.
        #
        # This still cannot perform runtime model training (see
        # services/prediction_service.py), so if no trained model exists
        # yet, "smart_ml" is not startable -- in that specific case ONLY,
        # this falls back to "sequential" for this process, and prints a
        # clear warning. This fallback is never silent to the frontend:
        # Dashboard.tsx fetches GET /simulation/state once on mount and
        # reconciles its local scenario (including strategy) to whatever
        # the backend actually reports, so the two cannot silently
        # disagree even in the fallback case -- and explicitly requesting
        # "smart_ml" via /simulation/scenario still returns a clear 409
        # (see api/simulation_routes.py), never a silent substitution.
        try:
            _orchestrator.reset(ScenarioConfig(strategy="smart_ml"))
        except PredictorNotAvailableError:
            print(
                "WARNING: no trained model found -- starting with "
                "'sequential' instead of the default 'smart_ml'. Run "
                "`python3 scripts/train_predictor.py`, then restart, to "
                "use Smart ML. The current strategy is always visible "
                "via GET /simulation/state; the frontend reconciles to "
                "it automatically on load."
            )
            _orchestrator.reset(ScenarioConfig(strategy="sequential"))
    return _orchestrator
