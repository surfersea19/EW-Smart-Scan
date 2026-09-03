"""
comparison_routes.py

Runs the SAME scenario (same seed -> identical P1 environment, per
ScenarioGenerator's determinism guarantee) under each of Person 2's
three real schedulers, driven by Person 1's real SimulationEngine each
time. Numbers are always produced by actually running the integrated
simulation -- never hardcoded (see integration analysis, evaluation
section).

This does NOT reuse ew_scheduler's experiment_runner.run_simulation()
directly, because that function drives its own simplified toy detector
instead of Person 1's real RFEnvironment/DetectionModel (see
integration/evaluation_adapter.py module docstring for the full
rationale). It DOES reuse P2's real SimulationResult and
compare_results() unmodified.
"""
from fastapi import APIRouter, HTTPException

from schemas.simulation import ScenarioConfig
from services import simulation_service, scheduler_service
from services.prediction_service import PredictorNotAvailableError
from integration.evaluation_adapter import (
    LiveMetricsTracker,
    ground_truth_records_at,
    simulation_result_to_metrics,
    build_comparison_table,
)

router = APIRouter(prefix="/comparison", tags=["comparison"])

STRATEGIES = ["sequential", "random", "smart_ml"]


@router.post("")
def run_comparison(base_scenario: ScenarioConfig):
    """
    Runs each strategy against an isolated RealSimulationEngine instance
    (does not disturb the live /simulation state) until Person 1's real
    clock (engine.current_time) reaches base_scenario.duration, and
    returns each strategy's resulting metrics.

    duration is interpreted identically here and in the live orchestrator
    (services/orchestrator.py tick()): it means P1's real raw-tick clock,
    not a count of scheduler decisions -- see that file's docstring for
    the full rationale. Previously this looped `range(scenario.duration)`
    calls to step_once(), which is only equivalent to "duration raw
    ticks" when every decision costs exactly 1 tick (P1's current default
    receiver config) -- this fix makes it correct in general.
    """
    results = {}
    raw_results = []  # real P2 SimulationResult objects, for compare_results()
    engine = simulation_service.RealSimulationEngine()  # isolated instance

    for strategy in STRATEGIES:
        scenario = base_scenario.model_copy(update={"strategy": strategy})

        try:
            scheduler_adapter = scheduler_service.build_scheduler_adapter(strategy)
        except PredictorNotAvailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        engine.reset(scenario, scheduler_adapter)
        tracker = LiveMetricsTracker(scheduler_name=strategy)

        # Driven purely by P1's real clock (engine.current_time), read
        # after each decision -- no second clock introduced. P1's engine
        # always advances current_time by at least 1 per step_once()
        # call (dwell_time >= 1 by construction), so this terminates.
        while engine.current_time < scenario.duration:
            observations = engine.step_once()
            for obs in observations:
                gt_records = ground_truth_records_at(engine.environment.ground_truth_log, obs.time)
                tracker.update(obs, gt_records)

        # BUG FIX: without this, a burst still active on the very last
        # tick of the fixed-duration run was silently dropped instead of
        # being resolved as intercepted/missed (see
        # LiveMetricsTracker.finalize() docstring for the exact P2
        # semantics this reproduces). This is especially likely to
        # matter here since /comparison always runs a fixed, bounded
        # number of ticks.
        tracker.finalize()

        raw_results.append(tracker.result)
        results[strategy] = simulation_result_to_metrics(tracker.result)

    # Reuse Person 2's real compare_results() (unmodified) for a
    # server-side log of the full comparison table, exactly as P2's own
    # evaluation module presents it -- useful for the demo narration /
    # terminal output, in addition to the JSON returned to the frontend.
    print(build_comparison_table(raw_results).to_string())

    return results
