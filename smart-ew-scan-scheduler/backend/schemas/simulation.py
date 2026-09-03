from pydantic import BaseModel
from typing import Optional, Literal
from .prediction import BandPrediction
from .scheduler import PredictedActivity

# "priority" was dropped: Person 2 does not implement a distinct
# priority-based scheduler, only sequential/random/smart_ml (see
# ew_scheduler/backend/scheduler/). Keeping it in the type would let the
# frontend request a strategy the backend cannot actually provide.
StrategyType = Literal["sequential", "random", "smart_ml"]


class ScenarioConfig(BaseModel):
    num_bands: int = 180          # overwritten from the real Spectrum after reset; see simulation_service.py
    num_emitters: int = 5
    duration: int = 300           # ticks, used by the comparison endpoint
    noise_level: Literal["low", "medium", "high"] = "medium"
    strategy: StrategyType = "smart_ml"
    seed: int = 0                 # reproducible scenarios, passed straight to P1's ScenarioConfig


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
    endpoint. Ground truth deliberately lives OUTSIDE this model (it's
    read only inside integration/evaluation_adapter.py) so it can never
    be accidentally serialized into a receiver-facing payload.
    """
    running: bool = False
    scenario: ScenarioConfig = ScenarioConfig()
    simulation_time: int = 0
    current_band: Optional[int] = None
    last_observation: Optional[ObservationView] = None
    predictions: list[BandPrediction] = []
    next_band: Optional[int] = None
    scheduler_reason: Optional[str] = None
    predicted_activity: list[PredictedActivity] = []
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
    predicted_activity: list[PredictedActivity] = []
    metrics: Metrics
    running: bool = True
    # ^ Added so the frontend learns immediately when the backend
    # auto-stops after reaching ScenarioConfig.duration (see
    # orchestrator.tick()) -- without this, the frontend's local
    # "running" flag only ever changed in response to explicit
    # start()/stop() button clicks and had no way to learn the backend
    # stopped itself, leaving a stale "running=true" in the UI.
