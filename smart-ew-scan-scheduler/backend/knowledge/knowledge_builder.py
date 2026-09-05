"""Build persistent prior evidence from one run's receiver observations."""

from datetime import datetime, timezone

from .knowledge_schema import BandKnowledge, PersistentKnowledge


def build_knowledge(
    history_manager,
    current_time: int,
    run_id: str,
    num_bands: int,
    scenario_seed: int | None = None,
    noise_level: str | None = None,
) -> PersistentKnowledge:
    """Create a persistent evidence snapshot without mutating run-local history.

    Confidence is a deterministic evidence-strength heuristic based solely on
    scan quantity. It is not an ML probability or a signal-activity estimate.
    """
    bands = []
    for band_id in sorted(history_manager.observed_bands()):
        observation_count = history_manager.scan_count(band_id)
        observations = history_manager.get_band_history(band_id)
        hit_count = sum(1 for observation in observations if observation["detected"])
        hit_ratio = hit_count / observation_count if observation_count > 0 else 0.0

        bands.append(
            BandKnowledge(
                band_id=band_id,
                observation_count=observation_count,
                hit_count=hit_count,
                hit_ratio=hit_ratio,
                last_hit_time=history_manager.last_hit_time(band_id),
                last_scan_time=history_manager.last_scan_time(band_id),
                confidence=min(observation_count / 10.0, 1.0),
                last_updated_time=current_time,
            )
        )

    return PersistentKnowledge(
        schema_version=1,
        source_run_id=run_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        num_bands=num_bands,
        source_scenario_seed=scenario_seed,
        source_noise_level=noise_level,
        bands=bands,
    )
