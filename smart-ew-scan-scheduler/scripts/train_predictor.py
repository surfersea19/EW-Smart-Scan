#!/usr/bin/env python3
"""
scripts/train_predictor.py

Run this ONCE, manually, before starting the integrated application with
the "smart_ml" strategy:

    cd smart-ew-scan-scheduler
    python3 scripts/train_predictor.py

This is a DELIBERATELY SEPARATE, EXPLICIT step -- it is never called
automatically by main.py / the FastAPI app / any startup path. Ground
truth is used here ONLY to generate offline training LABELS (the
permitted offline use); the live application (services/prediction_service.py)
never trains and never sees ground truth.

What this does:
  1. Builds a real Person 1 scenario (ScenarioGenerator -> RFEnvironment).
  2. Runs Person 1's own NaiveSequentialScheduler for a while to produce
     a broad-coverage observation log (P1's own documented purpose for
     this scheduler -- see simulation_engine.py's docstring: "ship a
     NaiveSequentialScheduler as a placeholder... Person 1 can test with
     a simple sequential scanner before the smart scheduler exists").
  3. Converts the observation log to Person 2's dict format (observation
     data only) and the ground truth log to Person 2's
     dict[band, list[time]] format (used ONLY as training labels here).
  4. Calls Person 2's REAL, UNMODIFIED DatasetBuilder + ModelTrainer
     (ew_scheduler/backend/prediction/{dataset_builder,train}.py) to
     build the dataset and train/save models.

Requires ew_scheduler/requirements.txt to be installed (including
xgboost) -- this script does not work around missing dependencies.
"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_THIS_DIR, "..", "backend")
sys.path.insert(0, _BACKEND_DIR)

from integration.repo_paths import register_p1_p2_on_path  # noqa: E402
from integration.feature_config import WINDOW_SIZE, N_LAGS  # noqa: E402
from integration.observation_adapter import p1_observation_to_p2_dict  # noqa: E402

register_p1_p2_on_path()

from backend.environment.scenario_generator import (  # noqa: E402
    ScenarioGenerator, ScenarioConfig as P1ScenarioConfig,
)
from backend.environment.spectrum import SpectrumConfig  # noqa: E402
from backend.receiver.virtual_receiver import VirtualReceiver  # noqa: E402
from backend.receiver.noise_model import NoiseModel, NoiseConfig  # noqa: E402
from backend.receiver.detection_model import DetectionModel, DetectionConfig  # noqa: E402
from backend.simulation.simulation_engine import SimulationEngine, NaiveSequentialScheduler  # noqa: E402

from feature_engineering import FeatureExtractor  # noqa: E402  (P2, path registered above)
from dataset_builder import DatasetBuilder  # noqa: E402
from train import ModelTrainer  # noqa: E402  (P2's REAL trainer -- unmodified)

# --- Configuration -----------------------------------------------------
SCENARIO_SEED = 42
TRAINING_SEED = 42
NUM_BANDS = 180        # matches P1's default SpectrumConfig
NUM_EMITTERS = 8
NUM_DECISIONS = 8000    # scheduler decisions to run for training data coverage
NOISE_STD_DB = 3.0
LABEL_HORIZON = 5
MIN_HISTORY = 3
# ------------------------------------------------------------------------


def main():
    print("=" * 70)
    print("TRAINING BOOTSTRAP -- generating data via Person 1's real "
          "simulation, then training Person 2's real models.")
    print("Ground truth is used below ONLY to build training labels.")
    print("=" * 70)

    generator = ScenarioGenerator(P1ScenarioConfig(
        seed=SCENARIO_SEED,
        spectrum_config=SpectrumConfig(num_bands=NUM_BANDS),
        num_emitters=NUM_EMITTERS,
    ))
    environment = generator.generate()

    noise = NoiseModel(NoiseConfig(noise_std_db=NOISE_STD_DB, seed=SCENARIO_SEED))
    detector = DetectionModel(noise, DetectionConfig())
    receiver = VirtualReceiver(environment, detection_model=detector)
    # NaiveSequentialScheduler: broad, unbiased band coverage for training
    # data. Using SmartScheduler here would be circular (it needs a
    # trained model to run) and using Sequential/Random from P2 would
    # work too, but P1 already ships exactly this scheduler for this
    # purpose (see simulation_engine.py docstring).
    engine = SimulationEngine(environment, receiver, scheduler=NaiveSequentialScheduler())

    print(f"\nRunning {NUM_DECISIONS} scheduler decisions across "
          f"{environment.spectrum.num_bands} bands, {NUM_EMITTERS} emitters...")
    engine.run(NUM_DECISIONS)
    print(f"Generated {len(receiver.observation_log)} observations, "
          f"{len(environment.ground_truth_log)} ground truth records.")

    # --- Offline translation (permitted ground-truth use) --------------
    observation_dicts = [
        p1_observation_to_p2_dict(obs) for obs in receiver.observation_log
    ]

    # NOTE: dedupe per (band, time) -- P1's ground_truth_log has one
    # record per emitter per tick, so if two+ emitters are simultaneously
    # active on the same band, that (band, time) pair would otherwise be
    # appended more than once. P2's ground_truth dict format is defined
    # as "the set of times a band was active" (see
    # ew_scheduler/backend/evaluation/experiment_runner.py's
    # extract_bursts, which assumes a de-duplicated, sorted time list per
    # band); duplicate timestamps make its contiguous-run burst detection
    # fragment one real burst into several spurious ones. This dedup
    # keeps training-label generation consistent with how the same
    # ground truth is interpreted everywhere else in this integration
    # (see integration/evaluation_adapter.py).
    ground_truth_sets: dict[int, set] = {}
    for record in environment.ground_truth_log:
        if record.active and record.band is not None:
            ground_truth_sets.setdefault(record.band, set()).add(record.time)
    ground_truth: dict[int, list[int]] = {
        band: sorted(times) for band, times in ground_truth_sets.items()
    }

    all_bands = environment.spectrum.list_bands()

    # --- Real Person 2 dataset construction + training ------------------
    feature_extractor = FeatureExtractor(window_size=WINDOW_SIZE, n_lags=N_LAGS)
    builder = DatasetBuilder(feature_extractor, horizon=LABEL_HORIZON, min_history=MIN_HISTORY)

    print("\nBuilding training dataset (Person 2's real DatasetBuilder)...")
    dataset = builder.build(observation_dicts, ground_truth, all_bands)
    print(f"Dataset: {len(dataset)} rows, positive rate {dataset['label'].mean():.3f}")

    train_df, val_df, _test_df = builder.time_split(dataset)

    trainer = ModelTrainer(
        feature_names=feature_extractor.feature_names(),
        random_state=TRAINING_SEED,
    )
    print("\nTraining all models (Person 2's real ModelTrainer -- logistic, "
          "random_forest, xgboost)...")
    comparison = trainer.train_all(train_df, val_df)

    print("\n" + "=" * 70)
    print(f"Done. Models saved to {trainer.model_dir}")
    print("The application's default model is 'random_forest' "
          "(see backend/integration/feature_config.py -- change "
          "DEFAULT_MODEL_NAME there to use a different one).")
    print("=" * 70)
    return comparison


if __name__ == "__main__":
    main()
