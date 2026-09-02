# run_pipeline.py
# Run this file to execute the full pipeline end to end.
# It will: generate a scenario, train all models, run all three
# schedulers, and print a comparison table.

import sys
import os
import random

# --- Path setup ---
PRED_DIR  = os.path.join(os.path.dirname(__file__), "backend", "prediction")
SCHED_DIR = os.path.join(os.path.dirname(__file__), "backend", "scheduler")
EVAL_DIR  = os.path.join(os.path.dirname(__file__), "backend", "evaluation")

sys.path.insert(0, PRED_DIR)
sys.path.insert(0, SCHED_DIR)
sys.path.insert(0, EVAL_DIR)

from history_manager        import BandHistoryManager
from feature_engineering    import FeatureExtractor
from dataset_builder        import DatasetBuilder
from train                  import ModelTrainer
from predict                import Predictor
from sequential_scheduler   import SequentialScheduler
from random_scheduler       import RandomScheduler
from smart_scheduler        import SmartScheduler
from experiment_runner      import run_simulation
from comparison             import compare_results, print_comparison


# ====================================================================
# STEP 1: DEFINE SCENARIO
# ====================================================================

SEED        = 42
BANDS       = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
TOTAL_TIME  = 1000   # total simulation time steps
TRAIN_END   = 600    # use first 600 steps for training, rest for eval

random.seed(SEED)

# Build ground truth for the entire simulation
ground_truth = {b: [] for b in BANDS}

for t in range(1, TOTAL_TIME + 1):
    if t % 8  == 0: ground_truth[10].append(t)   # periodic every 8
    if t % 15 == 0: ground_truth[20].append(t)   # periodic every 15
    if t % 22 == 0: ground_truth[30].append(t)   # periodic every 22
    if random.random() < 0.25: ground_truth[40].append(t)  # random 25%
    if random.random() < 0.15: ground_truth[50].append(t)  # random 15%
    if random.random() < 0.08: ground_truth[60].append(t)  # random 8%
    # bands 70, 80, 90, 100: silent (test exploration)

print(f"Scenario: {len(BANDS)} bands, {TOTAL_TIME} time steps")
for b, times in ground_truth.items():
    print(f"  Band {b:>3}: {len(times)} active steps")


# ====================================================================
# STEP 2: BUILD TRAINING OBSERVATION LOG
# ====================================================================
# Simulate a round-robin receiver to generate training data.
# In the real system, Person 1 provides this.

gt_sets = {b: set(ground_truth[b]) for b in BANDS}
obs_log = []

for t in range(1, TRAIN_END + 1):
    band     = BANDS[t % len(BANDS)]
    detected = t in gt_sets[band]
    obs      = {"time": t, "band": band, "detected": detected}
    if detected:
        obs["power"] = random.uniform(-50, -30)
    obs_log.append(obs)

print(f"\nTraining observation log: {len(obs_log)} observations")


# ====================================================================
# STEP 3: BUILD DATASET AND TRAIN MODELS
# ====================================================================

fe = FeatureExtractor(window_size=10, n_lags=5)
db = DatasetBuilder(fe, horizon=8, min_history=5)

print("\nBuilding training dataset...")
df = db.build(obs_log, ground_truth, BANDS)
train_df, val_df, _ = db.time_split(df)

print("\nTraining models...")
trainer   = ModelTrainer(feature_names=fe.feature_names())
comparison_ml = trainer.train_all(train_df, val_df)

print("\nFeature importance (Random Forest):")
trainer.print_feature_importance("random_forest")


# ====================================================================
# STEP 4: BUILD PREDICTOR
# ====================================================================

predictor = Predictor("random_forest", fe)


# ====================================================================
# STEP 5: DEFINE EVALUATION GROUND TRUTH
# ====================================================================
# Evaluate on time steps AFTER training ends.
# Re-index so evaluation starts at t=1 (the simulator always starts at 1).

eval_steps  = TOTAL_TIME - TRAIN_END
time_offset = TRAIN_END  # shift all times back by this amount

eval_ground_truth = {
    band: [t - time_offset for t in times if t > TRAIN_END]
    for band, times in ground_truth.items()
}

print(f"\nEvaluation: {eval_steps} steps (original t={TRAIN_END+1} to t={TOTAL_TIME})")
for b, times in eval_ground_truth.items():
    if times:
        print(f"  Band {b:>3}: {len(times)} active steps in eval window")


# ====================================================================
# STEP 6: RUN ALL THREE SCHEDULERS
# ====================================================================

schedulers = [
    (SequentialScheduler(),                "Sequential"),
    (RandomScheduler(seed=SEED),           "Random"),
    (SmartScheduler(predictor, seed=SEED), "Smart ML"),
]

results = []
for scheduler, name in schedulers:
    print(f"\n{'='*40}")
    print(f"Running: {name}")
    print(f"{'='*40}")
    result = run_simulation(
        scheduler      = scheduler,
        bands          = BANDS,
        ground_truth   = eval_ground_truth,
        total_steps    = eval_steps,
        scheduler_name = name,
        noise_prob     = 0.0,
        seed           = SEED,
    )
    print(result.summary())
    results.append(result)


# ====================================================================
# STEP 7: COMPARE RESULTS
# ====================================================================

df_comparison = compare_results(results)
print_comparison(df_comparison)


# ====================================================================
# STEP 8: SHOW SMART SCHEDULER DECISION BREAKDOWN
# ====================================================================

print("\n--- Smart Scheduler: Example Decision Breakdown ---")
smart_sched = SmartScheduler(predictor, epsilon=0.0, seed=SEED)
hm_demo     = BandHistoryManager()

# Feed some observations so the scheduler has history to work with
for obs in obs_log[-50:]:
    hm_demo.ingest(obs)

smart_sched.explain_decision(BANDS, hm_demo, current_time=TRAIN_END)
