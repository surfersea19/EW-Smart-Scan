from fastapi import APIRouter

from schemas.simulation import ScenarioConfig, Metrics
from services.orchestrator import SimulationOrchestrator

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.post("")
def run_comparison(base_scenario: ScenarioConfig):
    """
    Runs base_scenario.duration ticks under each strategy, headlessly,
    and returns each strategy's resulting metrics. Numbers are always
    produced by actually running the simulation -- never hardcoded.
    """
    strategies = ["sequential", "random", "smart_ml"]
    results: dict[str, Metrics] = {}

    for strategy in strategies:
        scenario = base_scenario.model_copy(update={"strategy": strategy})
        orch = SimulationOrchestrator()  # isolated instance, doesn't touch live sim
        orch.reset(scenario)
        for _ in range(scenario.duration):
            orch.tick()
        results[strategy] = orch.state.metrics

    return results
