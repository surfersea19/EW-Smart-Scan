"""
Observation schema.

This is the CONTRACT for what Person 1's simulation/receiver must produce
every time the receiver is tuned to a band and takes a look.

IMPORTANT: This is receiver-facing data only. It must NEVER contain
information the receiver couldn't actually have sensed (i.e. no ground
truth about emitters that were not scanned this tick).
"""
from pydantic import BaseModel, Field
from typing import Optional


class Observation(BaseModel):
    time: int = Field(..., description="Simulation tick / timestamp")
    band: int = Field(..., description="Band index the receiver was tuned to")
    detected: bool = Field(..., description="Whether the receiver detected activity")
    power: Optional[float] = Field(None, description="Signal power in dBm, if detected")
    pulse_width: Optional[float] = Field(None, description="Pulse width (us), if detected")
    pri: Optional[float] = Field(None, description="Pulse repetition interval (us), if detected")


class GroundTruth(BaseModel):
    """
    NOT receiver-facing. Used only for evaluation / an explicit debug view.
    Must be kept structurally separate from Observation at all times.
    """
    time: int
    active_bands: list[int]
    active_emitters: list[str]
