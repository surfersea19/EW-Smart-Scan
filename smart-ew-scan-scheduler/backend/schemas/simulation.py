from pydantic import AliasChoices, BaseModel, Field
from typing import Optional, Literal
from .prediction import BandPrediction
from .scheduler import PredictedActivity

# "priority" was dropped: Person 2 does not implement a distinct
# priority-based scheduler, only sequential/random/smart_ml (see
# ew_scheduler/backend/scheduler/). Keeping it in the type would let the
# frontend request a strategy the backend cannot actually provide.
StrategyType = Literal["sequential", "random", "smart_ml"]


class ActiveEmitterInfo(BaseModel):
    band: int
    emitter_id: Optional[str] = None
    emitter_type: Optional[str] = None
    power_db: Optional[float] = None


class ScenarioConfig(BaseModel):
    """Single reproducible run configuration for live and comparison runs."""
    num_bands: int = 180          # overwritten from the real Spectrum after reset; see simulation_service.py
    num_emitters: int = 5
    duration: int = 300           # ticks, used by the comparison endpoint
    noise_level: Literal["low", "medium", "high"] = "medium"
    strategy: StrategyType = "smart_ml"
    scenario_seed: int = Field(
        default=0,
        validation_alias=AliasChoices("scenario_seed", "seed"),
    )  # P1 environment generation and receiver noise; accepts legacy ``seed`` input
    scheduler_seed: int = 0       # P2 Random/Smart scheduler decision streams
    model_name: Literal["logistic", "random_forest", "xgboost"] = "random_forest"
    playback_speed: int = 5       # 1x, 5x, 10x wall-clock execution pacing


class ObservationView(BaseModel):
    """
    Pydantic view of Person 1's real (dataclass) Observation, for the
    /simulation/state REST response only. Field names deliberately match
    P1's real Observation (scanned_band, measured_power_db, ...), NOT
    the earlier placeholder mock's names -- see schemas/observation.py.
    """
    time: int
    scanned_band: int
    detected: bool
    measured_power_db: Optional[float] = None
    pulse_width_us: Optional[float] = None
    pri_us: Optional[float] = None


class Metrics(BaseModel):
    ticks_run: int = 0
    hits: int = 0
    misses: int = 0
    detection_probability: float = 0.0    # Pd, from ew_scheduler SimulationResult.pd
    false_alarm_probability: float = 0.0  # Pfa, from SimulationResult.pfa
    avg_intercept_time: float = 0.0       # burst-start-relative, from SimulationResult.avg_intercept_time
    intercept_rate: float = 0.0           # from SimulationResult.intercept_rate
    prediction_accuracy: float = 0.0      # from SimulationResult.scan_efficiency (closest real analogue)


class SimulationState(BaseModel):
    """
    Full authoritative backend state, for the /simulation/state REST
    endpoint. Ground truth is strictly isolated and never fed into ML
    decision paths; active_emitters is provided exclusively for the
    environment waterfall visualization.
    """
    running: bool = False
    completed: bool = False
    scenario: ScenarioConfig = ScenarioConfig()
    simulation_time: int = 0
    current_band: Optional[int] = None
    last_observation: Optional[ObservationView] = None
    predictions: list[BandPrediction] = []
    next_band: Optional[int] = None
    scheduler_reason: Optional[str] = None
    predicted_activity: list[PredictedActivity] = []
    metrics: Metrics = Metrics()
    playback_speed: int = 5
    active_emitters: list[ActiveEmitterInfo] = []


class WSDelta(BaseModel):
    """
    Compact per-tick payload pushed to the frontend over WebSocket.
    active_emitters captures simulated RF environment activity for the
    waterfall display only (never passed to ML/scheduler).
    """
    time: int
    current_band: Optional[int]
    detected: Optional[bool]
    power: Optional[float] = None
    top_predictions: list[BandPrediction] = []
    next_band: Optional[int]
    scheduler_reason: Optional[str] = None
    predicted_activity: list[PredictedActivity] = []
    metrics: Metrics
    running: bool = True
    completed: bool = False
    playback_speed: int = 5
    active_emitters: list[ActiveEmitterInfo] = []
