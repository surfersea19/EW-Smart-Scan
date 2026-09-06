"""
orchestrator.py -- the only place that calls Person 1 + Person 2's real
code together, now against the real modules instead of mocks.

CLOCK OWNERSHIP: Person 1's SimulationEngine owns the only clock. This
orchestrator calls `engine.step_once()` exactly once per tick() call --
it does not advance time itself, and does not call environment.step()
directly anywhere.

GROUND TRUTH ISOLATION: `environment.ground_truth_log` is read ONLY in
this file's `tick()` method, ONLY to feed `LiveMetricsTracker.update()`
for evaluation and waterfall visualization. It is never passed to
`scheduler_adapter` or anything inside integration/scheduler_adapter.py.

ARCHITECTURE NOTE ON "NEXT BAND": the earlier mock-based design showed
a "next scan" band chosen ahead of when it would actually be scanned.
Person 1's real SimulationEngine.step() decides a band AND scans it in
the same atomic call -- there is no observable moment where a decision
exists before its execution, short of peeking inside step() (not
possible without modifying P1's code, which is out of scope).
WSDelta.next_band is therefore populated with THIS tick's chosen band
(== current_band) rather than a genuine look-ahead; the frontend's
"Scheduler Decision" panel is relabeled accordingly (see frontend
changes) to describe why this tick's band was chosen, not to promise
a preview of the future.
"""

import logging
from uuid import uuid4

from knowledge import PersistentKnowledge, PersistentKnowledgeStore, build_knowledge
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
logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    def __init__(self):
        self.state = SimulationState()
        self.scheduler_adapter = None
        self.live_metrics: LiveMetricsTracker | None = None
        self.playback_speed: int = 5
        self._completed_run_knowledge_saved = False
        self.loaded_prior_knowledge: PersistentKnowledge | None = None

    def reset(self, scenario: ScenarioConfig) -> None:
        """
        May raise services.prediction_service.PredictorNotAvailableError
        if scenario.strategy == "smart_ml" and no trained model exists.
        This is intentionally NOT caught here -- see
        api/simulation_routes.py, which turns it into a clear HTTP error
        instead of silently training on the spot.
        """
        self._completed_run_knowledge_saved = False
        self._load_prior_knowledge()

        self.scheduler_adapter = scheduler_service.build_scheduler_adapter(
            scenario.strategy,
            scheduler_seed=scenario.scheduler_seed,
            model_name=scenario.model_name,
            prior_knowledge=self.loaded_prior_knowledge,
            current_num_bands=scenario.num_bands,
        )

        engine = simulation_service.get_simulation_engine()
        engine.reset(scenario, self.scheduler_adapter)

        # engine.reset() overwrites scenario.num_bands with the real
        # spectrum's band count -- read it back rather than trusting
        # the pre-reset value.
        self.scenario = engine.scenario
        self.playback_speed = getattr(scenario, "playback_speed", 5)

        self.live_metrics = LiveMetricsTracker(
            scheduler_name=scenario.strategy
        )

        # "Warm" means the persistent knowledge is not only present,
        # but is compatible with the current Smart ML scenario and can
        # actually be used by the scheduler.
        knowledge_is_compatible = (
            scenario.strategy == "smart_ml"
            and self.loaded_prior_knowledge is not None
            and self.loaded_prior_knowledge.num_bands == self.scenario.num_bands
        )

        self.state = SimulationState(
            scenario=self.scenario,
            playback_speed=self.playback_speed,
            running=False,
            completed=False,
            knowledge_status="warm" if knowledge_is_compatible else "cold",
        )

    def _load_prior_knowledge(self) -> None:
        """Load prior evidence without modifying the new run's scheduler state."""
        self.loaded_prior_knowledge = None

        try:
            self.loaded_prior_knowledge = PersistentKnowledgeStore().load()
        except Exception:
            logger.warning(
                "Could not load persistent knowledge",
                exc_info=True,
            )

    def _save_completed_run_knowledge(self) -> None:
        """Persist receiver-observation evidence once after duration completion."""
        if self._completed_run_knowledge_saved:
            return

        try:
            engine = simulation_service.get_simulation_engine()

            knowledge = build_knowledge(
                history_manager=self.scheduler_adapter._hm,
                current_time=engine.current_time,
                run_id=str(uuid4()),
                num_bands=self.scenario.num_bands,
                scenario_seed=self.scenario.scenario_seed,
                noise_level=self.scenario.noise_level,
            )

            PersistentKnowledgeStore().save(knowledge)

        except Exception:
            logger.warning(
                "Could not persist completed run knowledge",
                exc_info=True,
            )
            return

        self._completed_run_knowledge_saved = True

    def set_playback_speed(self, speed: int) -> None:
        self.playback_speed = max(1, speed)
        self.state.playback_speed = self.playback_speed

        if hasattr(self, "scenario") and self.scenario is not None:
            self.scenario.playback_speed = self.playback_speed

    def start(self) -> None:
        engine = simulation_service.get_simulation_engine()

        if (
            engine.engine is not None
            and engine.current_time >= self.scenario.duration
        ):
            self.state.running = False
            self.state.completed = True
            return

        self.state.running = True
        self.state.completed = False

    def pause(self) -> None:
        self.state.running = False

        # Resolve any bursts still open (ground-truth active,
        # not yet intercepted) so the metrics shown after stopping are
        # conclusive rather than silently omitting whatever was pending.
        # Safe to call repeatedly.
        if self.live_metrics is not None:
            self.live_metrics.finalize()
            self.state.metrics = simulation_result_to_metrics(
                self.live_metrics.result
            )

    def tick(self) -> WSDelta:
        engine = simulation_service.get_simulation_engine()

        # ------------------------------------------------------------------
        # Already completed
        # ------------------------------------------------------------------
        if engine.current_time >= self.scenario.duration:
            self.pause()
            self.state.completed = True

            return WSDelta(
                time=self.state.simulation_time,
                current_band=self.state.current_band,
                detected=(
                    self.state.last_observation.detected
                    if self.state.last_observation
                    else False
                ),
                power=(
                    self.state.last_observation.measured_power_db
                    if self.state.last_observation
                    else None
                ),
                top_predictions=self.state.predictions,
                next_band=self.state.next_band,
                scheduler_reason=self.state.scheduler_reason,
                behavior=self.state.behavior,
                behavior_confidence=self.state.behavior_confidence,
                predicted_activity=self.state.predicted_activity,
                running=False,
                completed=True,
                metrics=self.state.metrics,
                playback_speed=self.playback_speed,
                active_emitters=self.state.active_emitters,
            )

        # ------------------------------------------------------------------
        # One real P1 simulation decision + scan.
        # ------------------------------------------------------------------
        observations = engine.step_once()

        environment = engine.environment

        # Ground truth is used ONLY for evaluation.
        # It never enters the scheduler or predictor.
        for obs in observations:
            gt_records = ground_truth_records_at(
                environment.ground_truth_log,
                obs.time,
            )
            self.live_metrics.update(obs, gt_records)

        last_obs = observations[-1]

        # ------------------------------------------------------------------
        # Ground truth for visualization ONLY.
        # ------------------------------------------------------------------
        latest_gt = ground_truth_records_at(
            environment.ground_truth_log,
            last_obs.time,
        )

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

        # ------------------------------------------------------------------
        # Duration enforcement.
        # ------------------------------------------------------------------
        if engine.current_time >= self.scenario.duration:
            self._save_completed_run_knowledge()
            self.pause()
            self.state.completed = True
        else:
            self.state.completed = False

        # ------------------------------------------------------------------
        # Prediction / scheduler information.
        # ------------------------------------------------------------------
        predictions = self._top_predictions()
        predicted_activity = self._predicted_activity(predictions)

        # Read AFTER duration check because pause() may have finalized
        # the metrics for a completed run.
        metrics = simulation_result_to_metrics(
            self.live_metrics.result
        )

        # ------------------------------------------------------------------
        # Update authoritative state.
        # ------------------------------------------------------------------
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
        self.state.next_band = last_obs.scanned_band

        self.state.scheduler_reason = self.scheduler_adapter.last_reason

        # Behavior is diagnostic information supplied by the scheduler
        # adapter. Use getattr so lightweight test doubles and
        # non-Smart-ML schedulers remain compatible.
        self.state.behavior = getattr(
            self.scheduler_adapter,
            "last_behavior",
            None,
        )

        self.state.behavior_confidence = getattr(
            self.scheduler_adapter,
            "last_behavior_confidence",
            0.0,
        )

        self.state.predicted_activity = predicted_activity
        self.state.metrics = metrics
        self.state.playback_speed = self.playback_speed
        self.state.active_emitters = active_emitters

        # ------------------------------------------------------------------
        # WebSocket delta.
        #
        # IMPORTANT:
        # Use the authoritative state values above rather than directly
        # reading optional adapter attributes. This keeps the response
        # compatible with simple test adapters and all scheduler types.
        # ------------------------------------------------------------------
        return WSDelta(
            time=last_obs.time,
            current_band=last_obs.scanned_band,
            detected=last_obs.detected,
            power=last_obs.measured_power_db,
            top_predictions=predictions,
            next_band=last_obs.scanned_band,
            scheduler_reason=self.state.scheduler_reason,
            behavior=self.state.behavior,
            behavior_confidence=self.state.behavior_confidence,
            predicted_activity=predicted_activity,
            running=self.state.running,
            completed=self.state.completed,
            metrics=metrics,
            playback_speed=self.playback_speed,
            active_emitters=active_emitters,
        )

    def _top_predictions(self) -> list[BandPrediction]:
        preds = self.scheduler_adapter.last_predictions
        ranked = sorted(
            preds.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )

        return [
            BandPrediction(
                band=band,
                probability=round(prob, 4),
            )
            for band, prob in ranked[:TOP_K_PREDICTIONS]
        ]

    def _predicted_activity(
        self,
        predictions: list[BandPrediction],
    ) -> list[PredictedActivity]:
        return [
            PredictedActivity(
                rank=i + 1,
                band=p.band,
                probability=p.probability,
            )
            for i, p in enumerate(
                predictions[:TOP_K_PREDICTED_ACTIVITY]
            )
        ]


_orchestrator: SimulationOrchestrator | None = None


def get_orchestrator() -> SimulationOrchestrator:
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = SimulationOrchestrator()

        # Backend initial strategy matches the frontend default.
        #
        # This still cannot perform runtime model training, so if no
        # trained model exists yet, "smart_ml" is not startable -- in
        # that specific case ONLY, fall back to sequential.
        try:
            _orchestrator.reset(
                ScenarioConfig(strategy="smart_ml")
            )

        except PredictorNotAvailableError:
            print(
                "WARNING: no trained model found -- starting with "
                "'sequential' instead of the default 'smart_ml'. Run "
                "`python3 scripts/train_predictor.py`, then restart, to "
                "use Smart ML. The current strategy is always visible "
                "via GET /simulation/state; the frontend reconciles to "
                "it automatically on load."
            )

            _orchestrator.reset(
                ScenarioConfig(strategy="sequential")
            )

    return _orchestrator