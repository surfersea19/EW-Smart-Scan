import math
import sys
from pathlib import Path

import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from evaluate_phase4 import (
    EVALUATION_CASES,
    Phase4Config,
    aggregate_results,
    build_scenario,
    result_row,
    run_integrated,
    scan_behavior_metrics,
)


def test_default_configuration_contains_exactly_the_five_phase4_cases():
    assert [(case.strategy, case.model_name) for case in EVALUATION_CASES] == [
        ("sequential", "random_forest"),
        ("random", "random_forest"),
        ("smart_ml", "logistic"),
        ("smart_ml", "random_forest"),
        ("smart_ml", "xgboost"),
    ]


def test_paired_run_configurations_share_scenario_seed_and_scheduler_seed():
    config = Phase4Config(scenario_seeds=(7,), duration=20)
    scenarios = [build_scenario(config, case, 7) for case in config.cases]

    assert {scenario.scenario_seed for scenario in scenarios} == {7}
    assert {scenario.scheduler_seed for scenario in scenarios} == {7}
    assert {scenario.duration for scenario in scenarios} == {20}
    assert {scenario.num_bands for scenario in scenarios} == {180}


def test_coverage_and_repeat_rate_are_calculated_from_decision_log():
    decision_log = [{"band": 4}, {"band": 8}, {"band": 4}, {"band": 10}, {"band": 8}]

    metrics = scan_behavior_metrics(decision_log, total_available_bands=20)

    assert metrics == {
        "unique_bands_scanned": 3,
        "scan_coverage": 0.15,
        "repeat_scans": 2,
        "repeat_rate": 0.4,
    }


def test_aggregate_results_calculates_mean_and_sample_standard_deviation():
    raw = pd.DataFrame([
        {"configuration": "Sequential", "strategy": "sequential", "model_name": "none", "pd": 0.1,
         "pfa": 0.0, "intercept_rate": 0.2, "avg_intercept_time": 2.0,
         "bursts_intercepted": 2, "missed_bursts": 4, "scan_efficiency": 0.2,
         "unique_bands_scanned": 10, "scan_coverage": 0.5, "repeat_rate": 0.5},
        {"configuration": "Sequential", "strategy": "sequential", "model_name": "none", "pd": 0.3,
         "pfa": 0.2, "intercept_rate": 0.4, "avg_intercept_time": 4.0,
         "bursts_intercepted": 4, "missed_bursts": 2, "scan_efficiency": 0.4,
         "unique_bands_scanned": 14, "scan_coverage": 0.7, "repeat_rate": 0.3},
    ])

    aggregate = aggregate_results(raw).iloc[0]

    assert aggregate["pd_mean"] == 0.2
    assert math.isclose(aggregate["pd_std"], math.sqrt(0.02))
    assert aggregate["unique_bands_scanned_mean"] == 12
    assert math.isclose(aggregate["repeat_rate_std"], math.sqrt(0.02))


def test_same_integrated_configuration_and_seed_produce_identical_raw_metrics():
    config = Phase4Config(scenario_seeds=(3,), duration=30)
    case = EVALUATION_CASES[0]
    scenario = build_scenario(config, case, 3)

    first = run_integrated(case, scenario)
    second = run_integrated(case, scenario)

    first_row = result_row(case, scenario, first)
    second_row = result_row(case, scenario, second)
    assert first_row.keys() == second_row.keys()
    for key, first_value in first_row.items():
        second_value = second_row[key]
        assert (
            first_value == second_value
            or (isinstance(first_value, float) and isinstance(second_value, float)
                and math.isnan(first_value) and math.isnan(second_value))
        ), key


def test_different_scenario_seeds_normally_produce_different_integrated_trajectories():
    # A compact spectrum ensures each sequential sweep observes all generated
    # emitters, while still using the real P1 environment and receiver.
    config = Phase4Config(scenario_seeds=(0, 1), num_bands=5, num_emitters=5, duration=30)
    case = EVALUATION_CASES[0]
    first = run_integrated(case, build_scenario(config, case, 0))
    second = run_integrated(case, build_scenario(config, case, 1))

    assert first.decision_log != second.decision_log
