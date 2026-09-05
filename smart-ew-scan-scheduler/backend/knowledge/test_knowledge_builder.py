"""Tests for building persistent evidence from P2's run-local history."""

import inspect

from integration.repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

from history_manager import BandHistoryManager  # noqa: E402
from knowledge import build_knowledge  # noqa: E402


def ingest(history_manager: BandHistoryManager, time: int, band: int, detected: bool) -> None:
    history_manager.ingest({"time": time, "band": band, "detected": detected})


def test_empty_history_produces_no_band_records() -> None:
    knowledge = build_knowledge(BandHistoryManager(), 10, "run-empty", 180)

    assert knowledge.bands == []


def test_single_band_evidence_is_built_from_observations() -> None:
    history_manager = BandHistoryManager()
    ingest(history_manager, 3, 12, False)
    ingest(history_manager, 5, 12, True)
    ingest(history_manager, 7, 12, False)
    ingest(history_manager, 9, 12, True)

    knowledge = build_knowledge(history_manager, 15, "run-one", 180)
    band = knowledge.bands[0]

    assert band.observation_count == 4
    assert band.hit_count == 2
    assert band.hit_ratio == 0.5
    assert band.last_hit_time == 9
    assert band.last_scan_time == 9
    assert band.confidence == 0.4
    assert band.last_updated_time == 15


def test_multiple_bands_are_sorted_by_band_id() -> None:
    history_manager = BandHistoryManager()
    ingest(history_manager, 1, 50, True)
    ingest(history_manager, 2, 3, False)
    ingest(history_manager, 3, 21, True)

    knowledge = build_knowledge(history_manager, 4, "run-sorted", 180)

    assert [band.band_id for band in knowledge.bands] == [3, 21, 50]


def test_observed_band_with_no_hits_is_persisted() -> None:
    history_manager = BandHistoryManager()
    ingest(history_manager, 4, 8, False)
    ingest(history_manager, 7, 8, False)

    band = build_knowledge(history_manager, 10, "run-misses", 180).bands[0]

    assert band.hit_count == 0
    assert band.hit_ratio == 0.0
    assert band.last_hit_time is None
    assert band.last_scan_time == 7
    assert band.confidence == 0.2


def test_confidence_caps_after_ten_observations() -> None:
    history_manager = BandHistoryManager()
    for time in range(12):
        ingest(history_manager, time, 7, False)

    band = build_knowledge(history_manager, 12, "run-confidence", 180).bands[0]

    assert band.observation_count == 12
    assert band.confidence == 1.0


def test_unobserved_bands_are_not_persisted() -> None:
    history_manager = BandHistoryManager()
    ingest(history_manager, 1, 4, True)

    knowledge = build_knowledge(history_manager, 2, "run-observed", 180)

    assert [band.band_id for band in knowledge.bands] == [4]
    assert 5 not in [band.band_id for band in knowledge.bands]


def test_source_metadata_is_copied() -> None:
    knowledge = build_knowledge(
        BandHistoryManager(),
        current_time=7,
        run_id="run-metadata",
        num_bands=64,
        scenario_seed=99,
        noise_level="low",
    )

    assert knowledge.schema_version == 1
    assert knowledge.source_run_id == "run-metadata"
    assert knowledge.num_bands == 64
    assert knowledge.source_scenario_seed == 99
    assert knowledge.source_noise_level == "low"
    assert knowledge.created_at.endswith("+00:00")


def test_builder_does_not_mutate_history_manager() -> None:
    history_manager = BandHistoryManager()
    ingest(history_manager, 1, 9, True)
    ingest(history_manager, 2, 9, False)
    before_bands = history_manager.observed_bands()
    before_history = history_manager.get_band_history(9)
    before_time = history_manager.current_time

    build_knowledge(history_manager, 10, "run-immutable", 180)

    assert history_manager.observed_bands() == before_bands
    assert history_manager.get_band_history(9) == before_history
    assert history_manager.current_time == before_time


def test_builder_source_does_not_reference_forbidden_information() -> None:
    source = inspect.getsource(build_knowledge)

    for forbidden_name in (
        "ground_truth_log",
        "RFEnvironment",
        "emitter_id",
        "emitter_type",
        "active_bands_at",
        "predictions",
        "scheduler",
    ):
        assert forbidden_name not in source
