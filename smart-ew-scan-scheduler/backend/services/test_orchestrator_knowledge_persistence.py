"""Focused lifecycle tests for completed-run persistent knowledge saves."""

from types import SimpleNamespace

from integration.repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

from history_manager import BandHistoryManager  # noqa: E402
from schemas.simulation import Metrics, ScenarioConfig  # noqa: E402
from services import orchestrator as orchestrator_module  # noqa: E402


class RecordingStore:
    def __init__(self) -> None:
        self.saved = []

    def save(self, knowledge) -> None:
        self.saved.append(knowledge)


def make_completed_orchestrator(monkeypatch, store: RecordingStore):
    history_manager = BandHistoryManager()
    orchestrator = orchestrator_module.SimulationOrchestrator()
    orchestrator.scheduler_adapter = SimpleNamespace(
        _hm=history_manager,
        last_predictions={},
        last_reason=None,
    )
    orchestrator.scenario = ScenarioConfig(
        strategy="sequential",
        duration=5,
        num_bands=64,
        scenario_seed=123,
        noise_level="low",
    )
    observation = SimpleNamespace(
        time=5,
        scanned_band=9,
        detected=True,
        measured_power_db=-50.0,
        pulse_width_us=None,
        pri_us=None,
    )
    engine = SimpleNamespace(
        current_time=4,
        environment=SimpleNamespace(ground_truth_log=[]),
    )

    def step_once():
        engine.current_time = 5
        return [observation]

    engine.step_once = step_once
    orchestrator.live_metrics = SimpleNamespace(
        update=lambda observation, records: None,
        finalize=lambda: None,
        result=object(),
    )
    monkeypatch.setattr(orchestrator_module.simulation_service, "get_simulation_engine", lambda: engine)
    monkeypatch.setattr(orchestrator_module, "PersistentKnowledgeStore", lambda: store)
    monkeypatch.setattr(orchestrator_module, "ground_truth_records_at", lambda *args: [])
    monkeypatch.setattr(orchestrator_module, "simulation_result_to_metrics", lambda result: Metrics())
    return orchestrator, history_manager


def test_completed_run_saves_one_snapshot_and_repeated_completion_does_not_save_twice(monkeypatch) -> None:
    store = RecordingStore()
    orchestrator, history_manager = make_completed_orchestrator(monkeypatch, store)
    history_manager.ingest({"time": 2, "band": 9, "detected": True})

    orchestrator.tick()
    orchestrator.tick()

    assert len(store.saved) == 1
    assert orchestrator._completed_run_knowledge_saved is True


def test_pre_step_completed_tick_does_not_save_without_a_completion_step(monkeypatch) -> None:
    store = RecordingStore()
    orchestrator, history_manager = make_completed_orchestrator(monkeypatch, store)
    history_manager.ingest({"time": 2, "band": 9, "detected": True})
    engine = orchestrator_module.simulation_service.get_simulation_engine()
    engine.current_time = orchestrator.scenario.duration

    orchestrator.tick()

    assert store.saved == []


def test_manual_pause_does_not_save_knowledge(monkeypatch) -> None:
    store = RecordingStore()
    orchestrator, _ = make_completed_orchestrator(monkeypatch, store)

    orchestrator.pause()

    assert store.saved == []
    assert orchestrator._completed_run_knowledge_saved is False


def test_reset_clears_completed_run_save_flag(monkeypatch) -> None:
    orchestrator = orchestrator_module.SimulationOrchestrator()
    orchestrator._completed_run_knowledge_saved = True
    adapter = SimpleNamespace()
    engine = SimpleNamespace()

    def reset_engine(scenario, scheduler_adapter) -> None:
        engine.scenario = scenario

    engine.reset = reset_engine
    monkeypatch.setattr(orchestrator_module.scheduler_service, "build_scheduler_adapter", lambda *args, **kwargs: adapter)
    monkeypatch.setattr(orchestrator_module.simulation_service, "get_simulation_engine", lambda: engine)

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator._completed_run_knowledge_saved is False


def test_completed_knowledge_contains_only_observed_band_evidence(monkeypatch) -> None:
    store = RecordingStore()
    orchestrator, history_manager = make_completed_orchestrator(monkeypatch, store)
    history_manager.ingest({"time": 1, "band": 12, "detected": False})
    history_manager.ingest({"time": 4, "band": 12, "detected": True})

    orchestrator.tick()

    knowledge = store.saved[0]
    assert [band.band_id for band in knowledge.bands] == [12]
    assert knowledge.bands[0].observation_count == 2
    assert knowledge.bands[0].hit_count == 1
    assert knowledge.bands[0].last_scan_time == 4
    assert knowledge.source_scenario_seed == 123
    assert knowledge.source_noise_level == "low"


def test_persistence_failure_does_not_crash_or_mark_snapshot_saved(monkeypatch, caplog) -> None:
    class FailingStore:
        def save(self, knowledge) -> None:
            raise OSError("disk unavailable")

    orchestrator, _ = make_completed_orchestrator(monkeypatch, FailingStore())
    monkeypatch.setattr(orchestrator_module, "PersistentKnowledgeStore", FailingStore)

    orchestrator.tick()

    assert orchestrator._completed_run_knowledge_saved is False
    assert "Could not persist completed run knowledge" in caplog.text
