"""Tests for the isolated persistent knowledge schema and JSON store."""

import json

import pytest
from pydantic import ValidationError

from knowledge import BandKnowledge, PersistentKnowledge, PersistentKnowledgeStore


def make_knowledge() -> PersistentKnowledge:
    return PersistentKnowledge(
        schema_version=1,
        source_run_id="run-123",
        created_at="2026-09-05T12:00:00Z",
        num_bands=180,
        source_scenario_seed=42,
        source_noise_level="medium",
        bands=[
            BandKnowledge(
                band_id=12,
                observation_count=8,
                hit_count=3,
                hit_ratio=0.375,
                last_hit_time=20,
                last_scan_time=24,
                confidence=0.7,
                last_updated_time=24,
            ),
            BandKnowledge(
                band_id=48,
                observation_count=2,
                hit_count=0,
                hit_ratio=0.0,
                last_scan_time=18,
                confidence=0.2,
            ),
        ],
    )


def test_band_knowledge_can_be_created() -> None:
    band = BandKnowledge(
        band_id=1,
        observation_count=4,
        hit_count=2,
        hit_ratio=0.5,
        last_scan_time=4,
        confidence=0.6,
    )

    assert band.band_id == 1
    assert band.last_hit_time is None


def test_negative_observation_count_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BandKnowledge(
            band_id=1,
            observation_count=-1,
            hit_count=0,
            hit_ratio=0.0,
            confidence=0.5,
        )


def test_hit_count_cannot_exceed_observation_count() -> None:
    with pytest.raises(ValidationError, match="hit_count must not exceed"):
        BandKnowledge(
            band_id=1,
            observation_count=1,
            hit_count=2,
            hit_ratio=1.0,
            last_scan_time=1,
            confidence=0.5,
        )


@pytest.mark.parametrize("hit_ratio", [-0.1, 1.1])
def test_invalid_hit_ratio_is_rejected(hit_ratio: float) -> None:
    with pytest.raises(ValidationError):
        BandKnowledge(
            band_id=1,
            observation_count=1,
            hit_count=0,
            hit_ratio=hit_ratio,
            last_scan_time=1,
            confidence=0.5,
        )


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_invalid_confidence_is_rejected(confidence: float) -> None:
    with pytest.raises(ValidationError):
        BandKnowledge(
            band_id=1,
            observation_count=1,
            hit_count=0,
            hit_ratio=0.0,
            last_scan_time=1,
            confidence=confidence,
        )


def test_positive_observation_count_requires_last_scan_time() -> None:
    with pytest.raises(ValidationError, match="last_scan_time is required"):
        BandKnowledge(
            band_id=1,
            observation_count=1,
            hit_count=0,
            hit_ratio=0.0,
            confidence=0.5,
        )


def test_zero_observations_may_omit_last_scan_time() -> None:
    band = BandKnowledge(
        band_id=1,
        observation_count=0,
        hit_count=0,
        hit_ratio=0.0,
        confidence=0.5,
    )

    assert band.last_scan_time is None


def test_zero_hits_may_omit_last_hit_time() -> None:
    band = BandKnowledge(
        band_id=1,
        observation_count=1,
        hit_count=0,
        hit_ratio=0.0,
        last_scan_time=1,
        confidence=0.5,
    )

    assert band.last_hit_time is None


def test_persistent_knowledge_can_contain_multiple_bands() -> None:
    knowledge = make_knowledge()

    assert len(knowledge.bands) == 2
    assert knowledge.bands[1].band_id == 48


def test_save_load_exists_and_clear_use_temporary_directory(tmp_path) -> None:
    store = PersistentKnowledgeStore(tmp_path)
    knowledge = make_knowledge()

    assert store.exists() is False
    assert store.load() is None

    store.save(knowledge)

    assert store.exists() is True
    assert (tmp_path / "persistent_knowledge.json").is_file()
    assert store.load() == knowledge

    store.clear()

    assert store.exists() is False
    assert store.load() is None


def test_malformed_persisted_data_raises_clear_validation_error(tmp_path) -> None:
    store = PersistentKnowledgeStore(tmp_path)
    (tmp_path / "persistent_knowledge.json").write_text(
        json.dumps({"schema_version": 1}), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="required schema"):
        store.load()


def test_invalid_json_raises_clear_error(tmp_path) -> None:
    store = PersistentKnowledgeStore(tmp_path)
    (tmp_path / "persistent_knowledge.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid JSON"):
        store.load()


def test_saved_json_excludes_forbidden_fields(tmp_path) -> None:
    store = PersistentKnowledgeStore(tmp_path)
    store.save(make_knowledge())

    saved_json = (tmp_path / "persistent_knowledge.json").read_text(encoding="utf-8")

    for forbidden_field in (
        "emitter_id",
        "emitter_type",
        "ground_truth",
        "predictions",
        "scheduler_state",
    ):
        assert forbidden_field not in saved_json
