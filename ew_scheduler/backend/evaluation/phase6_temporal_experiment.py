# backend/evaluation/phase6_temporal_experiment.py
"""
Phase 6 Controlled Multi-Seed Experiment: Temporal & Periodic Behavior Intelligence.

Evaluates and compares:
  1. Sequential Baseline
  2. Random Baseline
  3. Phase 5 Smart ML Scheduler (without temporal scoring, w_temporal=0.0)
  4. Phase 6 Temporal Smart ML Scheduler (with temporal intelligence, w_temporal=0.15)

Tested across 5 deterministic seeds on periodic and mixed EW scenarios.
Operates with strict ground-truth isolation (observations only during scheduling).
"""

from __future__ import annotations

import os
import random
import sys
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PRED_DIR = os.path.join(ROOT, "backend", "prediction")
SCHED_DIR = os.path.join(ROOT, "backend", "scheduler")
EVAL_DIR = os.path.join(ROOT, "backend", "evaluation")

for p in [PRED_DIR, SCHED_DIR, EVAL_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from feature_engineering import FeatureExtractor
from dataset_builder import DatasetBuilder
from train import ModelTrainer
from predict import Predictor
from sequential_scheduler import SequentialScheduler
from random_scheduler import RandomScheduler
from smart_scheduler import SmartScheduler
from experiment_runner import run_simulation


SEEDS = [1, 2, 3, 4, 5]
BANDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
TOTAL_STEPS = 1200
TRAIN_STEPS = 600
EVAL_STEPS = TOTAL_STEPS - TRAIN_STEPS


def generate_periodic_scenario(seed: int, total_steps: int) -> Dict[int, List[int]]:
    """
    Generate ground truth with distinct periodic emitters and background traffic.
    - Band 10: Periodic cycle T=8 (burst length 1)
    - Band 20: Periodic cycle T=15 (burst length 2)
    - Band 30: Periodic cycle T=24 (burst length 3)
    - Band 40: Periodic cycle T=35 (burst length 2)
    - Band 50: Intermittent bursty traffic (~20% duty)
    - Band 60: Low-rate bursty traffic (~8% duty)
    - Bands 70..100: Silent / background
    """
    rng = random.Random(seed)
    ground_truth = {b: [] for b in BANDS}

    # Deterministic phase offsets per seed
    phase_10 = rng.randint(0, 7)
    phase_20 = rng.randint(0, 14)
    phase_30 = rng.randint(0, 23)
    phase_40 = rng.randint(0, 34)

    for t in range(1, total_steps + 1):
        # Periodic Band 10 (T=8)
        if (t + phase_10) % 8 == 0:
            ground_truth[10].append(t)

        # Periodic Band 20 (T=15, duration 2)
        p20 = (t + phase_20) % 15
        if p20 in (0, 1):
            ground_truth[20].append(t)

        # Periodic Band 30 (T=24, duration 3)
        p30 = (t + phase_30) % 24
        if p30 in (0, 1, 2):
            ground_truth[30].append(t)

        # Periodic Band 40 (T=35, duration 2)
        p40 = (t + phase_40) % 35
        if p40 in (0, 1):
            ground_truth[40].append(t)

        # Bursty Band 50 (20%)
        if rng.random() < 0.20:
            ground_truth[50].append(t)

        # Bursty Band 60 (8%)
        if rng.random() < 0.08:
            ground_truth[60].append(t)

    return ground_truth


def train_offline_predictor(
    scenario_seed: int,
    feature_extractor: FeatureExtractor,
    model_name: str = "random_forest",
) -> Predictor:
    """Generate training observations via sequential scanning and train model."""
    gt_full = generate_periodic_scenario(scenario_seed, TRAIN_STEPS)
    gt_sets = {b: set(gt_full[b]) for b in BANDS}

    rng = random.Random(scenario_seed)
    obs_log = []
    for t in range(1, TRAIN_STEPS + 1):
        band = BANDS[(t - 1) % len(BANDS)]
        detected = t in gt_sets[band]
        obs = {"time": t, "band": band, "detected": detected}
        if detected:
            obs["power"] = rng.uniform(-60, -35)
        obs_log.append(obs)

    builder = DatasetBuilder(feature_extractor, horizon=6, min_history=3)
    dataset = builder.build(obs_log, gt_full, BANDS)
    train_df, val_df, _ = builder.time_split(dataset, train_frac=0.70, val_frac=0.15)

    trainer = ModelTrainer(
        feature_names=feature_extractor.feature_names(),
        random_state=scenario_seed,
    )
    trainer.train_all(train_df, val_df)
    return Predictor(model_name, feature_extractor)


def run_experiment_for_seed(seed: int, predictor: Predictor) -> Dict[str, dict]:
    """Run all 4 competing schedulers on one seeded evaluation environment."""
    full_gt = generate_periodic_scenario(seed, TOTAL_STEPS)

    # Shift ground truth for the evaluation window
    eval_gt = {
        b: [t - TRAIN_STEPS for t in times if t > TRAIN_STEPS]
        for b, times in full_gt.items()
    }

    schedulers = [
        ("Sequential", SequentialScheduler()),
        ("Random", RandomScheduler(seed=seed)),
        ("Phase 5 Smart ML (No Temporal)", SmartScheduler(predictor, w_temporal=0.0, seed=seed)),
        ("Phase 6 Smart ML (Temporal)", SmartScheduler(predictor, w_temporal=0.15, seed=seed)),
    ]

    results = {}
    for name, sched in schedulers:
        sim_res = run_simulation(
            scheduler=sched,
            bands=BANDS,
            ground_truth=eval_gt,
            total_steps=EVAL_STEPS,
            scheduler_name=name,
            noise_prob=0.0,
            seed=seed,
        )
        results[name] = {
            "pd": sim_res.pd,
            "intercept_rate": sim_res.intercept_rate,
            "avg_intercept_time": sim_res.avg_intercept_time,
            "bursts_intercepted": sim_res.bursts_intercepted,
            "missed_bursts": sim_res.missed_bursts,
            "scan_efficiency": sim_res.scan_efficiency,
            "pfa": sim_res.pfa,
        }

    return results


def main():
    print("=" * 80)
    print("PHASE 6 CONTROLLED MULTI-SEED EXPERIMENT: TEMPORAL BEHAVIOR INTELLIGENCE")
    print(f"Seeds: {SEEDS}, Spectrum: {len(BANDS)} bands, Eval Steps: {EVAL_STEPS}")
    print("=" * 80)

    fe = FeatureExtractor(window_size=10, n_lags=5)
    print("\n[1/2] Training offline predictor on seed 42 reference scenario...")
    predictor = train_offline_predictor(42, fe, model_name="random_forest")

    all_seed_results = []

    print("\n[2/2] Running controlled multi-seed evaluations across 5 independent seeds...")
    for seed in SEEDS:
        print(f"\n--- Running Seed {seed} ---")
        seed_res = run_experiment_for_seed(seed, predictor)
        for sched_name, metrics in seed_res.items():
            row = {"seed": seed, "scheduler": sched_name, **metrics}
            all_seed_results.append(row)
            print(
                f"  {sched_name:<32} | Pd: {metrics['pd']:.3f} | "
                f"Intercept Rate: {metrics['intercept_rate']:.3f} | "
                f"Bursts: {metrics['bursts_intercepted']:<3} | "
                f"Missed: {metrics['missed_bursts']:<3} | "
                f"Scan Eff: {metrics['scan_efficiency']:.3f}"
            )

    df = pd.DataFrame(all_seed_results)

    print("\n" + "=" * 80)
    print("MULTI-SEED SUMMARY (AVERAGE +/- STD OVER 5 SEEDS)")
    print("=" * 80)

    schedulers_order = [
        "Sequential",
        "Random",
        "Phase 5 Smart ML (No Temporal)",
        "Phase 6 Smart ML (Temporal)",
    ]

    summary_rows = []
    for sched in schedulers_order:
        sub = df[df["scheduler"] == sched]
        summary_rows.append({
            "Scheduler": sched,
            "Pd (Mean)": f"{sub['pd'].mean():.3f} +/- {sub['pd'].std():.3f}",
            "Intercept Rate": f"{sub['intercept_rate'].mean():.3f} +/- {sub['intercept_rate'].std():.3f}",
            "Bursts Caught": f"{sub['bursts_intercepted'].mean():.1f} +/- {sub['bursts_intercepted'].std():.1f}",
            "Missed Bursts": f"{sub['missed_bursts'].mean():.1f} +/- {sub['missed_bursts'].std():.1f}",
            "Scan Efficiency": f"{sub['scan_efficiency'].mean():.3f} +/- {sub['scan_efficiency'].std():.3f}",
            "Avg Intercept Time": f"{sub['avg_intercept_time'].mean():.2f} +/- {sub['avg_intercept_time'].std():.2f}",
        })

    summary_df = pd.DataFrame(summary_rows)
    print(summary_df.to_string(index=False))

    # Calculate Relative Improvements
    p5_sub = df[df["scheduler"] == "Phase 5 Smart ML (No Temporal)"]
    p6_sub = df[df["scheduler"] == "Phase 6 Smart ML (Temporal)"]
    seq_sub = df[df["scheduler"] == "Sequential"]
    rnd_sub = df[df["scheduler"] == "Random"]

    pd_gain_p5 = ((p6_sub["pd"].mean() - p5_sub["pd"].mean()) / p5_sub["pd"].mean()) * 100.0
    pd_gain_seq = ((p6_sub["pd"].mean() - seq_sub["pd"].mean()) / seq_sub["pd"].mean()) * 100.0
    pd_gain_rnd = ((p6_sub["pd"].mean() - rnd_sub["pd"].mean()) / rnd_sub["pd"].mean()) * 100.0

    burst_gain_p5 = ((p6_sub["bursts_intercepted"].mean() - p5_sub["bursts_intercepted"].mean()) / p5_sub["bursts_intercepted"].mean()) * 100.0
    missed_reduction_p5 = ((p5_sub["missed_bursts"].mean() - p6_sub["missed_bursts"].mean()) / p5_sub["missed_bursts"].mean()) * 100.0

    print("\n" + "=" * 80)
    print("PHASE 6 TEMPORAL INTELLIGENCE PERFORMANCE GAINS")
    print("=" * 80)
    print(f"  Pd Gain vs Phase 5 Baseline   : {pd_gain_p5:+.1f}%")
    print(f"  Pd Gain vs Sequential Baseline : {pd_gain_seq:+.1f}%")
    print(f"  Pd Gain vs Random Baseline     : {pd_gain_rnd:+.1f}%")
    print(f"  Bursts Caught Gain vs Phase 5  : {burst_gain_p5:+.1f}%")
    print(f"  Missed Bursts Reduction vs P5  : {missed_reduction_p5:+.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    main()
