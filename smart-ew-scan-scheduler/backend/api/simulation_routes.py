from fastapi import APIRouter, HTTPException

from schemas.simulation import ScenarioConfig, SimulationState
from services.orchestrator import get_orchestrator
from services.prediction_service import PredictorNotAvailableError

router = APIRouter(prefix="/simulation", tags=["simulation"])


def _reset_or_409(orch, scenario: ScenarioConfig) -> None:
    """
    Shared error handling for any endpoint that calls orch.reset().
    PredictorNotAvailableError means scenario.strategy == "smart_ml" and
    no trained model exists yet -- this is surfaced as a clear, actionable
    error, NOT silently worked around by training on the spot (see
    services/prediction_service.py docstring).
    """
    try:
        orch.reset(scenario)
    except PredictorNotAvailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/start")
def start_simulation():
    orch = get_orchestrator()
    orch.start()
    return {"running": True}


@router.post("/stop")
def stop_simulation():
    orch = get_orchestrator()
    orch.pause()
    return {"running": False}


@router.post("/reset")
def reset_simulation(scenario: ScenarioConfig | None = None):
    orch = get_orchestrator()
    _reset_or_409(orch, scenario or ScenarioConfig())
    return {"reset": True}


@router.post("/scenario")
def set_scenario(scenario: ScenarioConfig):
    orch = get_orchestrator()
    was_running = orch.state.running
    _reset_or_409(orch, scenario)
    if was_running:
        orch.start()
    return {"scenario": scenario}


@router.get("/state", response_model=SimulationState)
def get_state():
    orch = get_orchestrator()
    return orch.state


@router.get("/metrics")
def get_metrics():
    orch = get_orchestrator()
    return orch.state.metrics
