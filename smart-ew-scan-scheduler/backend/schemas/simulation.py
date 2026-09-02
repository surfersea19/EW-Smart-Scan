from pydantic import BaseModel
from typing import Optional, Literal
from .observation import Observation
from .prediction import BandPrediction
from .scheduler import TrackInfo

StrategyType = Literal["sequential", "random", "priority", "smart_ml"]


class ScenarioConfig(BaseModel):
    num_bands: int = 100
    num_emitters: int = 5
    duration: int = 300           # ticks
    noise_level: Literal["low", "medium", "high"] = "medium"
    strategy: StrategyType = "smart_ml"


class Metrics(BaseModel):
    ticks_run: int = 0
    hits: int = 0
    misses: int = 0
    detection_probability: float = 0.0   # Pd
    false_alarm_probability: float = 0.0  # Pfa
    avg_intercept_time: float = 0.0
    intercept_rate: float = 0.0
    prediction_accuracy: float = 0.0


class SimulationState(BaseModel):
    """
    Full authoritative backend state.
    Ground truth deliberately lives OUTSIDE this model (see simulation_service)
    so it can never be accidentally serialized into a receiver-facing payload.
    """
    running: bool = False
    scenario: ScenarioConfig = ScenarioConfig()
    simulation_time: int = 0
    current_band: Optional[int] = None
    last_observation: Optional[Observation] = None
    predictions: list[BandPrediction] = []
    next_band: Optional[int] = None
    scheduler_reason: Optional[str] = None
    tracks: list[TrackInfo] = []
    metrics: Metrics = Metrics()


class WSDelta(BaseModel):
    """
    Compact per-tick payload pushed to the frontend over WebSocket.
    Receiver-facing only -- no ground truth here.
    """
    time: int
    current_band: Optional[int]
    detected: Optional[bool]
    power: Optional[float] = None
    top_predictions: list[BandPrediction] = []
    next_band: Optional[int]
    scheduler_reason: Optional[str] = None
    tracks: list[TrackInfo] = []
    metrics: Metrics
