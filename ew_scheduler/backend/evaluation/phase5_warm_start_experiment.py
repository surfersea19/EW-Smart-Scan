import random
import sys
import os

# --- Path setup ---
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PRED_DIR = os.path.join(ROOT, "backend", "prediction")
SCHED_DIR = os.path.join(ROOT, "backend", "scheduler")
P3_DIR = os.path.join(
    os.path.dirname(ROOT),
    "smart-ew-scan-scheduler",
    "backend",
)

sys.path.insert(0, PRED_DIR)
sys.path.insert(0, SCHED_DIR)
sys.path.insert(0, P3_DIR)

from history_manager import BandHistoryManager
from feature_engineering import FeatureExtractor
from predict import Predictor
from smart_scheduler import SmartScheduler
from experiment_runner import run_simulation
from knowledge import build_knowledge


BANDS = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
SEEDS = [1, 2, 3, 4, 5]
SOURCE_STEPS = 600
TOTAL_STEPS = 1000
EVAL_STEPS = TOTAL_STEPS - SOURCE_STEPS


def build_scenario(seed: int, total_steps: int) -> dict[int, list[int]]:
    rng = random.Random(seed)
    ground_truth = {band: [] for band in BANDS}

    for t in range(1, total_steps + 1):
        if t % 8 == 0:
            ground_truth[10].append(t)
        if t % 15 == 0:
            ground_truth[20].append(t)
        if t % 22 == 0:
            ground_truth[30].append(t)
        if rng.random() < 0.25:
            ground_truth[40].append(t)
        if rng.random() < 0.15:
            ground_truth[50].append(t)
        if rng.random() < 0.08:
            ground_truth[60].append(t)

    return ground_truth


def build_prior_knowledge(seed: int):
    """Build real prior evidence from a previous observation phase."""
    history = BandHistoryManager()
    ground_truth = build_scenario(seed, SOURCE_STEPS)
    gt_sets = {band: set(times) for band, times in ground_truth.items()}

    for t in range(1, SOURCE_STEPS + 1):
        band = BANDS[(t - 1) % len(BANDS)]
        history.ingest(
            {
                "time": t,
                "band": band,
                "detected": t in gt_sets[band],
            }
        )

    return build_knowledge(
        history_manager=history,
        current_time=SOURCE_STEPS,
        run_id=f"phase5-warm-source-seed-{seed}",
        num_bands=len(BANDS),
        scenario_seed=seed,
        noise_level="none",
    )


def run_one_seed(seed: int, predictor: Predictor):
    prior_knowledge = build_prior_knowledge(seed)

    full_ground_truth = build_scenario(seed, TOTAL_STEPS)
    eval_ground_truth = {
        band: [t - SOURCE_STEPS for t in times if t > SOURCE_STEPS]
        for band, times in full_ground_truth.items()
    }

    cold_scheduler = SmartScheduler(
        predictor,
        seed=seed,
        prior_knowledge=None,
    )

    warm_scheduler = SmartScheduler(
        predictor,
        seed=seed,
        prior_knowledge=prior_knowledge,
    )

    cold_result = run_simulation(
        scheduler=cold_scheduler,
        bands=BANDS,
        ground_truth=eval_ground_truth,
        total_steps=EVAL_STEPS,
        scheduler_name=f"Cold-{seed}",
        noise_prob=0.0,
        seed=seed,
    )

    warm_result = run_simulation(
        scheduler=warm_scheduler,
        bands=BANDS,
        ground_truth=eval_ground_truth,
        total_steps=EVAL_STEPS,
        scheduler_name=f"Warm-{seed}",
        noise_prob=0.0,
        seed=seed,
    )

    return cold_result, warm_result


def main():
    fe = FeatureExtractor(window_size=10, n_lags=5)
    predictor = Predictor("random_forest", fe)

    rows = []

    for seed in SEEDS:
        cold, warm = run_one_seed(seed, predictor)

        rows.append(
            {
                "seed": seed,
                "cold_pd": cold.pd,
                "warm_pd": warm.pd,
                "cold_intercept": cold.intercept_rate,
                "warm_intercept": warm.intercept_rate,
                "cold_time": cold.avg_intercept_time,
                "warm_time": warm.avg_intercept_time,
                "cold_bursts": cold.bursts_intercepted,
                "warm_bursts": warm.bursts_intercepted,
                "cold_missed": cold.missed_bursts,
                "warm_missed": warm.missed_bursts,
            }
        )

    print("\n" + "=" * 82)
    print("PHASE 5I — CONTROLLED COLD vs WARM EVALUATION")
    print("=" * 82)

    print(
        f"{'Seed':>4} "
        f"{'Cold Pd':>9} {'Warm Pd':>9} "
        f"{'Cold Int':>10} {'Warm Int':>10} "
        f"{'Cold Time':>10} {'Warm Time':>10} "
        f"{'Cold Bursts':>12} {'Warm Bursts':>12}"
    )

    for row in rows:
        print(
            f"{row['seed']:>4} "
            f"{row['cold_pd']:>9.3f} {row['warm_pd']:>9.3f} "
            f"{row['cold_intercept']:>10.3f} {row['warm_intercept']:>10.3f} "
            f"{row['cold_time']:>10.2f} {row['warm_time']:>10.2f} "
            f"{row['cold_bursts']:>12} {row['warm_bursts']:>12}"
        )

    def avg(key):
        return sum(row[key] for row in rows) / len(rows)

    print("\n" + "-" * 82)
    print("5-SEED AVERAGES")
    print("-" * 82)

    print(f"Cold Pd              : {avg('cold_pd'):.3f}")
    print(f"Warm Pd              : {avg('warm_pd'):.3f}")
    print(f"Warm - Cold Pd       : {avg('warm_pd') - avg('cold_pd'):+.3f}")

    print(f"\nCold Intercept Rate  : {avg('cold_intercept'):.3f}")
    print(f"Warm Intercept Rate  : {avg('warm_intercept'):.3f}")
    print(
        f"Warm - Cold Rate     : "
        f"{avg('warm_intercept') - avg('cold_intercept'):+.3f}"
    )

    print(f"\nCold Avg Intercept   : {avg('cold_time'):.2f}")
    print(f"Warm Avg Intercept   : {avg('warm_time'):.2f}")
    print(
        f"Warm - Cold Time     : "
        f"{avg('warm_time') - avg('cold_time'):+.2f}"
    )

    print(f"\nCold Bursts          : {avg('cold_bursts'):.1f}")
    print(f"Warm Bursts          : {avg('warm_bursts'):.1f}")
    print(
        f"Warm - Cold Bursts   : "
        f"{avg('warm_bursts') - avg('cold_bursts'):+.1f}"
    )

    print(f"\nCold Missed Bursts   : {avg('cold_missed'):.1f}")
    print(f"Warm Missed Bursts   : {avg('warm_missed'):.1f}")
    print(
        f"Warm - Cold Missed   : "
        f"{avg('warm_missed') - avg('cold_missed'):+.1f}"
    )

    print("=" * 82)


if __name__ == "__main__":
    main()