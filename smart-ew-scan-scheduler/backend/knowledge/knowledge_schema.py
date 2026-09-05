"""Small schema for persisted, evidence-based band knowledge."""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BandKnowledge(BaseModel):
    """Evidence observed for one band across a completed source run."""

    model_config = ConfigDict(extra="forbid")

    band_id: int
    observation_count: int = Field(ge=0)
    hit_count: int = Field(ge=0)
    hit_ratio: float = Field(ge=0.0, le=1.0)
    last_hit_time: Optional[int] = None
    last_scan_time: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)
    last_updated_time: Optional[int] = None

    @model_validator(mode="after")
    def validate_observation_evidence(self) -> "BandKnowledge":
        if self.hit_count > self.observation_count:
            raise ValueError("hit_count must not exceed observation_count")
        if self.observation_count > 0 and self.last_scan_time is None:
            raise ValueError("last_scan_time is required when observation_count is positive")
        return self


class PersistentKnowledge(BaseModel):
    """Versioned prior evidence that is independent of run-local scheduler state."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    source_run_id: str
    created_at: str
    num_bands: int
    source_scenario_seed: Optional[int] = None
    source_noise_level: Optional[str] = None
    bands: list[BandKnowledge]
