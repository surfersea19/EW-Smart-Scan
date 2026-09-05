"""Focused lifecycle tests for completed-run persistent knowledge saves."""

from types import SimpleNamespace

from integration.repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

from history_manager import BandHistoryManager  # noqa: E402
from schemas.simulation import Metrics, ScenarioConfig  # noqa: E402
from services import orchestrator as orchestrator_module  # noqa: E402
from knowledge import BandKnowledge, PersistentKnowledge  # noqa: E402


class RecordingStore:
    def __init__(self) -> None:
        self.saved = []

    def save(self, knowledge) -> None:
        self.saved.append(knowledge)


def make_reset_orchestrator(monkeypatch, store):
    orchestrator = orchestrator_module.SimulationOrchestrator()
    adapter = SimpleNamespace(_hm=BandHistoryManager())
    engine = SimpleNamespace()

    def reset_engine(scenario, scheduler_adapter) -> None:
        engine.scenario = scenario

    engine.reset = reset_engine
    monkeypatch.setattr(
        orchestrator_module.scheduler_service,
        "build_scheduler_adapter",
        lambda *args, **kwargs: adapter,
    )
    monkeypatch.setattr(orchestrator_module.simulation_service, "get_simulation_engine", lambda: engine)
    monkeypatch.setattr(orchestrator_module, "PersistentKnowledgeStore", lambda: store)
    return orchestrator, adapter


def sample_knowledge() -> PersistentKnowledge:
    return PersistentKnowledge(
        schema_version=1,
        source_run_id="previous-run",
        created_at="2026-09-05T12:00:00+00:00",
        num_bands=64,
        bands=[
            BandKnowledge(
                band_id=12,
                observation_count=3,
                hit_count=1,
                hit_ratio=1 / 3,
                last_hit_time=3,
                last_scan_time=5,
                confidence=0.3,
                last_updated_time=5,
            )
        ],
    )


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
    store = SimpleNamespace(load=lambda: None)
    orchestrator, _ = make_reset_orchestrator(monkeypatch, store)
    orchestrator._completed_run_knowledge_saved = True

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator._completed_run_knowledge_saved is False


def test_reset_loads_valid_prior_knowledge_without_populating_run_history(monkeypatch) -> None:
    knowledge = sample_knowledge()
    orchestrator, adapter = make_reset_orchestrator(
        monkeypatch,
        SimpleNamespace(load=lambda: knowledge),
    )

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator.loaded_prior_knowledge == knowledge
    assert adapter._hm.observed_bands() == []


def test_reset_passes_loaded_prior_and_band_count_to_scheduler_service(monkeypatch) -> None:
    knowledge = sample_knowledge()
    orchestrator, adapter = make_reset_orchestrator(
        monkeypatch,
        SimpleNamespace(load=lambda: knowledge),
    )
    captured = {}

    def build_scheduler_adapter(*args, **kwargs):
        captured.update(kwargs)
        return adapter

    monkeypatch.setattr(
        orchestrator_module.scheduler_service,
        "build_scheduler_adapter",
        build_scheduler_adapter,
    )

    orchestrator.reset(ScenarioConfig(strategy="sequential", num_bands=64))

    assert captured["prior_knowledge"] == knowledge
    assert captured["current_num_bands"] == 64


def test_reset_with_no_persisted_knowledge_uses_cold_start(monkeypatch) -> None:
    orchestrator, _ = make_reset_orchestrator(monkeypatch, SimpleNamespace(load=lambda: None))

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator.loaded_prior_knowledge is None


def test_reset_discards_malformed_knowledge_and_continues(monkeypatch, caplog) -> None:
    def load() -> None:
        raise ValueError("invalid persisted knowledge")

    orchestrator, _ = make_reset_orchestrator(monkeypatch, SimpleNamespace(load=load))

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator.loaded_prior_knowledge is None
    assert "Could not load persistent knowledge" in caplog.text


def test_reset_replaces_old_prior_knowledge_when_store_is_empty(monkeypatch) -> None:
    orchestrator, _ = make_reset_orchestrator(monkeypatch, SimpleNamespace(load=lambda: None))
    orchestrator.loaded_prior_knowledge = sample_knowledge()

    orchestrator.reset(ScenarioConfig(strategy="sequential"))

    assert orchestrator.loaded_prior_knowledge is None


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


def test_reset_reports_warm_when_compatible_smart_ml_knowledge_exists(monkeypatch) -> None:
    knowledge = sample_knowledge()
    orchestrator, _ = make_reset_orchestrator(
        monkeypatch,
        SimpleNamespace(load=lambda: knowledge),
    )

    orchestrator.reset(ScenarioConfig(strategy="smart_ml", num_bands=64))

    assert orchestrator.state.knowledge_status == "warm"


def test_reset_reports_cold_when_band_count_is_incompatible(monkeypatch) -> None:
    knowledge = sample_knowledge()
    orchestrator, _ = make_reset_orchestrator(
        monkeypatch,
        SimpleNamespace(load=lambda: knowledge),
    )

    orchestrator.reset(ScenarioConfig(strategy="smart_ml", num_bands=180))

    assert orchestrator.state.knowledge_status == "cold"


def test_reset_reports_cold_when_knowledge_exists_but_strategy_is_not_smart_ml(monkeypatch) -> None:
    knowledge = sample_knowledge()
    orchestrator, _ = make_reset_orchestrator(
        monkeypatch,
        SimpleNamespace(load=lambda: knowledge),
    )

    orchestrator.reset(ScenarioConfig(strategy="sequential", num_bands=64))

    assert orchestrator.state.knowledge_status == "cold"
