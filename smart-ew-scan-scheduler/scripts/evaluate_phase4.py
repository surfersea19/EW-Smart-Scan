#!/usr/bin/env python3
"""Reproducible Phase 4 baseline evaluation of the integrated P1 -> P2 stack.

This script deliberately does not use P2's toy ``experiment_runner``.  Every
run creates a new real P1 simulation engine, receiver, and P2 scheduler.  The
only ground-truth access is the existing evaluation tracker, after P1 has
already produced each receiver observation.

Run from the repository root or P3 directory, for example:

    python smart-ew-scan-scheduler/scripts/evaluate_phase4.py
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
P3_ROOT = SCRIPT_DIR.parent
BACKEND_DIR = P3_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from integration.evaluation_adapter import LiveMetricsTracker, ground_truth_records_at
from schemas.simulation import ScenarioConfig
from services import scheduler_service, simulation_service


@dataclass(frozen=True)
class EvaluationCase:
    """One scheduler/model configuration in the fixed Phase 4 baseline."""

    name: str
    strategy: str
    model_name: str


EVALUATION_CASES = (
    EvaluationCase("Sequential", "sequential", "random_forest"),
    EvaluationCase("Random", "random", "random_forest"),
    EvaluationCase("Smart + Logistic", "smart_ml", "logistic"),
    EvaluationCase("Smart + Random Forest", "smart_ml", "random_forest"),
    EvaluationCase("Smart + XGBoost", "smart_ml", "xgboost"),
)


@dataclass(frozen=True)
class Phase4Config:
    """Single source of truth for a reproducible Phase 4 experiment."""

    scenario_seeds: tuple[int, ...] = (0, 1, 2, 3, 4)
    num_bands: int = 180
    num_emitters: int = 5
    duration: int = 300
    noise_level: str = "medium"
    cases: tuple[EvaluationCase, ...] = EVALUATION_CASES

    def scheduler_seed_for(self, scenario_seed: int) -> int:
        """Paired policy: all competitors in scenario S use scheduler seed S."""
        return scenario_seed


def build_scenario(config: Phase4Config, case: EvaluationCase, scenario_seed: int) -> ScenarioConfig:
    """Build one immutable run configuration without sharing engine state."""
    return ScenarioConfig(
        num_bands=config.num_bands,
        num_emitters=config.num_emitters,
        duration=config.duration,
        noise_level=config.noise_level,
        strategy=case.strategy,
        scenario_seed=scenario_seed,
        scheduler_seed=config.scheduler_seed_for(scenario_seed),
        model_name=case.model_name,
    )


def run_integrated(case: EvaluationCase, scenario: ScenarioConfig):
    """Run one isolated real P1/P2 competitor and return its raw P2 result."""
    scheduler_adapter = scheduler_service.build_scheduler_adapter(
        scenario.strategy,
        scheduler_seed=scenario.scheduler_seed,
        model_name=scenario.model_name,
    )
    engine = simulation_service.RealSimulationEngine()
    engine.reset(scenario.model_copy(deep=True), scheduler_adapter)
    tracker = LiveMetricsTracker(scheduler_name=case.name)

    # P1 owns the clock. Ground truth is read only after receiver output to
    # update the evaluation-only tracker; it is never exposed to the scheduler.
    while engine.current_time < scenario.duration:
        observations = engine.step_once()
        for observation in observations:
            tracker.update(
                observation,
                ground_truth_records_at(engine.environment.ground_truth_log, observation.time),
            )

    tracker.finalize()
    return tracker.result


def scan_behavior_metrics(decision_log: list[dict], total_available_bands: int) -> dict[str, float | int]:
    """Compute coverage/repetition strictly from an existing decision log."""
    decisions = len(decision_log)
    unique_bands = len({decision["band"] for decision in decision_log})
    repeat_scans = decisions - unique_bands
    return {
        "unique_bands_scanned": unique_bands,
        "scan_coverage": unique_bands / total_available_bands if total_available_bands else 0.0,
        "repeat_scans": repeat_scans,
        "repeat_rate": repeat_scans / decisions if decisions else 0.0,
    }


def result_row(case: EvaluationCase, scenario: ScenarioConfig, result) -> dict:
    """Flatten unchanged P2 metrics plus decision-log scan behavior for CSV."""
    behavior = scan_behavior_metrics(result.decision_log, scenario.num_bands)
    avg_intercept_time = result.avg_intercept_time
    if math.isinf(avg_intercept_time):
        avg_intercept_time = float("nan")

    return {
        "configuration": case.name,
        "strategy": case.strategy,
        "model_name": case.model_name if case.strategy == "smart_ml" else "none",
        "scenario_seed": scenario.scenario_seed,
        "scheduler_seed": scenario.scheduler_seed,
        "num_bands": scenario.num_bands,
        "num_emitters": scenario.num_emitters,
        "duration": scenario.duration,
        "noise_level": scenario.noise_level,
        "pd": result.pd,
        "pfa": result.pfa,
        "intercept_rate": result.intercept_rate,
        "avg_intercept_time": avg_intercept_time,
        "bursts_intercepted": result.bursts_intercepted,
        "missed_bursts": result.missed_bursts,
        "scan_efficiency": result.scan_efficiency,
        **behavior,
    }


METRIC_COLUMNS = (
    "pd",
    "pfa",
    "intercept_rate",
    "avg_intercept_time",
    "bursts_intercepted",
    "missed_bursts",
    "scan_efficiency",
    "unique_bands_scanned",
    "scan_coverage",
    "repeat_rate",
)


def aggregate_results(raw_results: pd.DataFrame) -> pd.DataFrame:
    """Mean and sample standard deviation across scenario seeds per case."""
    grouped = raw_results.groupby(["configuration", "strategy", "model_name"], sort=False)
    aggregated = grouped[list(METRIC_COLUMNS)].agg(["mean", "std"])
    aggregated.columns = [f"{metric}_{stat}" for metric, stat in aggregated.columns]
    return aggregated.reset_index()


def evaluate(config: Phase4Config) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Execute all paired runs, then return per-run and aggregate tables."""
    rows = []
    for scenario_seed in config.scenario_seeds:
        for case in config.cases:
            scenario = build_scenario(config, case, scenario_seed)
            result = run_integrated(case, scenario)
            rows.append(result_row(case, scenario, result))

    raw = pd.DataFrame(rows)
    return raw, aggregate_results(raw)


def parse_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not seeds:
        raise argparse.ArgumentTypeError("at least one scenario seed is required")
    return seeds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=parse_seeds, default=(0, 1, 2, 3, 4))
    parser.add_argument("--num-bands", type=int, default=180)
    parser.add_argument("--num-emitters", type=int, default=5)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--noise-level", choices=("low", "medium", "high"), default="medium")
    parser.add_argument("--output-dir", type=Path, default=P3_ROOT / "results" / "phase4")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Phase4Config(
        scenario_seeds=args.seeds,
        num_bands=args.num_bands,
        num_emitters=args.num_emitters,
        duration=args.duration,
        noise_level=args.noise_level,
    )
    raw, aggregate = evaluate(config)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(args.output_dir / "phase4_raw_results.csv", index=False)
    aggregate.to_csv(args.output_dir / "phase4_aggregate_results.csv", index=False)

    print("\nPHASE 4 RAW RESULTS")
    print(raw.to_string(index=False))
    print("\nPHASE 4 AGGREGATE RESULTS (mean ± sample std)")
    print(aggregate.to_string(index=False))
    print(f"\nWrote CSV results to {args.output_dir}")


if __name__ == "__main__":
    main()
