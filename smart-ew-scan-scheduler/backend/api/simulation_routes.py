from fastapi import APIRouter, HTTPException

from schemas.simulation import ScenarioConfig, SimulationState
from services.orchestrator import get_orchestrator

router = APIRouter(prefix="/simulation", tags=["simulation"])


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
    orch.reset(scenario or ScenarioConfig())
    return {"reset": True}


@router.post("/scenario")
def set_scenario(scenario: ScenarioConfig):
    orch = get_orchestrator()
    was_running = orch.state.running
    orch.reset(scenario)
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
