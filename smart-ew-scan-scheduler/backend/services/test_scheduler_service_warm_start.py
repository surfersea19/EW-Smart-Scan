"""Integration-boundary tests for compatible warm-start knowledge."""

from types import SimpleNamespace

from services import scheduler_service
from history_manager import BandHistoryManager


class MockPredictor:
    def predict_band(self, band, history_manager, current_time):
        return 0.5

    def predict_all_bands(self, bands, history_manager, current_time):
        return {band: 0.5 for band in bands}


def make_prior(num_bands: int):
    return SimpleNamespace(
        num_bands=num_bands,
        bands=[SimpleNamespace(band_id=2, hit_ratio=1.0, confidence=1.0)],
    )


def test_scheduler_service_passes_only_compatible_prior_to_smart_scheduler(monkeypatch) -> None:
    monkeypatch.setattr(scheduler_service, "get_predictor", lambda model_name: MockPredictor())

    adapter = scheduler_service.build_scheduler_adapter(
        "smart_ml",
        prior_knowledge=make_prior(8),
        current_num_bands=8,
    )

    assert adapter.p2_scheduler._warm_prior_by_band == {2: 1.0}


def test_scheduler_service_ignores_incompatible_prior_knowledge(monkeypatch) -> None:
    monkeypatch.setattr(scheduler_service, "get_predictor", lambda model_name: MockPredictor())

    adapter = scheduler_service.build_scheduler_adapter(
        "smart_ml",
        prior_knowledge=make_prior(8),
        current_num_bands=16,
    )

    assert adapter.p2_scheduler._warm_prior_by_band == {}


def test_baseline_schedulers_ignore_prior_knowledge() -> None:
    prior = make_prior(8)

    sequential = scheduler_service.build_scheduler_adapter(
        "sequential", prior_knowledge=prior, current_num_bands=8
    )
    random = scheduler_service.build_scheduler_adapter(
        "random", scheduler_seed=17, prior_knowledge=prior, current_num_bands=8
    )
    random_without_prior = scheduler_service.build_scheduler_adapter(
        "random", scheduler_seed=17
    )

    assert type(sequential.p2_scheduler).__name__ == "SequentialScheduler"
    assert type(random.p2_scheduler).__name__ == "RandomScheduler"
    assert [
        sequential.p2_scheduler.select_band([1, 2, 3], BandHistoryManager(), time)
        for time in range(3)
    ] == [1, 2, 3]
    assert [
        random.p2_scheduler.select_band([1, 2, 3], BandHistoryManager(), time)
        for time in range(5)
    ] == [
        random_without_prior.p2_scheduler.select_band([1, 2, 3], BandHistoryManager(), time)
        for time in range(5)
    ]
