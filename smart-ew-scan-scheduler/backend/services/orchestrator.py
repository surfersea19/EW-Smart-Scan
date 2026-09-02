"""
Orchestrator: the only place that calls Person 1 + Person 2's code together.

This is Person 3's core responsibility: connect, don't reimplement.

Ground truth is fetched ONLY here, ONLY for metrics computation, and is
never attached to SimulationState or WSDelta (the receiver/frontend-facing
models). This is the enforcement point for the ground-truth/observation
separation described in the project brief.
"""
from __future__ import annotations
from collections import deque

from schemas.observation import Observation
from schemas.simulation import SimulationState, ScenarioConfig, Metrics, WSDelta
from schemas.scheduler import TrackInfo
from services.simulation_service import get_simulation_engine
from services.prediction_service import get_predictor
from services.scheduler_service import get_scheduler


class SimulationOrchestrator:
    def __init__(self):
        self.state = SimulationState()
        self.engine = get_simulation_engine()
        self.predictor = get_predictor()
        self._obs_history: list[Observation] = []
        self._recent_bands: deque[int] = deque(maxlen=10)
        self._intercept_times: list[int] = []
        self._last_hit_time: dict[str, int] = {}  # emitter_id -> last intercept tick

    def reset(self, scenario: ScenarioConfig) -> None:
        self.engine.reset(scenario)
        self._obs_history = []
        self._recent_bands.clear()
        self._intercept_times = []
        self._last_hit_time = {}
        self.state = SimulationState(scenario=scenario, current_band=self.engine.current_band)

    def start(self) -> None:
        self.state.running = True

    def pause(self) -> None:
        self.state.running = False

    def tick(self) -> WSDelta:
        scenario = self.state.scenario
        scheduler = get_scheduler(scenario.strategy)

        # 1. advance world, take observation at current tuned band
        self.engine.step()
        obs = self.engine.observe()
        self._obs_history.append(obs)
        self._recent_bands.append(obs.band)

        # 2. ML prediction from observation history only (no ground truth)
        predictions = self.predictor.predict(
            self._obs_history, num_bands=scenario.num_bands, top_k=5
        )

        # 3. scheduler decision
        decision = scheduler.decide(
            predictions=predictions,
            current_band=obs.band,
            num_bands=scenario.num_bands,
            recently_scanned=set(self._recent_bands),
        )

        # 4. evaluation against ground truth (backend-only, not forwarded)
        gt = self.engine.ground_truth()
        self._update_metrics(obs, gt)

        # 5. tune receiver for next tick
        self.engine.tune(decision.next_band)

        # 6. update authoritative state
        self.state.simulation_time = obs.time
        self.state.current_band = obs.band
        self.state.last_observation = obs
        self.state.predictions = predictions
        self.state.next_band = decision.next_band
        self.state.scheduler_reason = decision.reason
        self.state.tracks = self._tracks_from_predictions(predictions)

        return WSDelta(
            time=obs.time,
            current_band=obs.band,
            detected=obs.detected,
            power=obs.power,
            top_predictions=predictions,
            next_band=decision.next_band,
            scheduler_reason=decision.reason,
            tracks=self.state.tracks,
            metrics=self.state.metrics,
        )

    def _tracks_from_predictions(self, predictions) -> list[TrackInfo]:
        # Simple derived view for the Emitter/Track panel -- anonymized,
        # never claims to know real emitter identity.
        tracks = []
        for i, p in enumerate(predictions[:3]):
            if p.probability > 0.3:
                tracks.append(
                    TrackInfo(
                        track_id=f"Track {i+1}",
                        emitter_type="unknown",
                        current_band=p.band,
                        confidence=p.probability,
                    )
                )
        return tracks

    def _update_metrics(self, obs: Observation, gt) -> None:
        m = self.state.metrics
        m.ticks_run += 1
        if obs.detected:
            m.hits += 1
            for eid in gt.active_emitters:
                if eid not in self._last_hit_time:
                    self._intercept_times.append(gt.time)
                self._last_hit_time[eid] = gt.time
        else:
            if obs.band in gt.active_bands:
                # shouldn't happen if detection model is consistent, kept for safety
                pass
            m.misses += 1

        total_active_ticks = max(
            1, sum(1 for _ in range(1)) * m.ticks_run
        )  # placeholder normalizer
        m.detection_probability = round(m.hits / m.ticks_run, 3) if m.ticks_run else 0.0
        false_positive = obs.detected and obs.band not in gt.active_bands
        m.false_alarm_probability = round(
            (m.false_alarm_probability * (m.ticks_run - 1) + (1 if false_positive else 0))
            / m.ticks_run,
            3,
        ) if m.ticks_run else 0.0
        m.avg_intercept_time = (
            round(sum(self._intercept_times) / len(self._intercept_times), 2)
            if self._intercept_times
            else 0.0
        )
        m.intercept_rate = round(
            len(self._last_hit_time) / max(1, len(gt.active_emitters) or 1), 3
        )


_orchestrator: SimulationOrchestrator | None = None


def get_orchestrator() -> SimulationOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SimulationOrchestrator()
        _orchestrator.reset(ScenarioConfig())
    return _orchestrator
