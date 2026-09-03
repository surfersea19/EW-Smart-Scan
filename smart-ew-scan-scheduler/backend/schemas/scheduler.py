from pydantic import BaseModel
from typing import Optional


class SchedulerDecision(BaseModel):
    next_band: int
    dwell_time: int = 1
    reason: Optional[str] = None


class PredictedActivity(BaseModel):
    """
    A single band from the predictor's current top-K ranking.

    IMPORTANT (see integration analysis, "TRACKING"): Person 2's
    predictor produces a fresh per-band probability every tick -- it
    does not perform persistent multi-target tracking (no track
    continuity, no track ID association across ticks). `rank` is just
    this tick's ordinal position (1 = highest predicted probability
    right now); it is NOT a stable identifier for a followed entity,
    and the band it points to can jump between ticks. This model was
    previously named TrackInfo, which implied a tracking capability
    the backend does not implement -- renamed to avoid that.
    """
    rank: int
    band: int
    probability: float
