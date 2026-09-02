from pydantic import BaseModel
from typing import Optional


class SchedulerDecision(BaseModel):
    next_band: int
    dwell_time: int = 1
    reason: Optional[str] = None  # e.g. "high predicted activity, not recently scanned"


class TrackInfo(BaseModel):
    track_id: str          # anonymized: "Track 1", never a real emitter identity
    emitter_type: str      # "periodic" | "agile" | "continuous" | "unknown"
    current_band: Optional[int] = None
    confidence: float = 0.0
