"""
prediction_service.py -- REAL Person 2 integration.

Loads Person 2's real Predictor against a model trained offline.

DELIBERATE DESIGN CHOICE (per integration sign-off): this module never
trains a model itself, and never runs at application startup as a
training step. If no trained model artifact exists on disk, it raises
PredictorNotAvailableError with instructions -- it does NOT silently
fall back to training using live ground truth. Training is a separate,
explicit, offline step: run `python3 scripts/train_predictor.py` once
before starting the application. That script uses ground truth only to
generate training LABELS (the offline-permitted use) -- this module's
job is strictly live inference on trained weights.
"""
from integration.repo_paths import register_p1_p2_on_path
from integration.feature_config import WINDOW_SIZE, N_LAGS, DEFAULT_MODEL_NAME

register_p1_p2_on_path()

from predict import Predictor  # noqa: E402  (P2, path registered above)
from feature_engineering import FeatureExtractor  # noqa: E402


class PredictorNotAvailableError(RuntimeError):
    """Raised when the smart_ml strategy is requested but no trained
    model exists yet. The caller (scheduler_service / API routes) is
    responsible for turning this into a clear user-facing message --
    this is not a bug to silently work around by training on the spot."""
    pass


_predictor_instances: dict[str, Predictor] = {}


def get_predictor(model_name: str = DEFAULT_MODEL_NAME) -> Predictor:
    if model_name not in _predictor_instances:
        fe = FeatureExtractor(window_size=WINDOW_SIZE, n_lags=N_LAGS)
        try:
            _predictor_instances[model_name] = Predictor(model_name, fe)
        except FileNotFoundError as exc:
            raise PredictorNotAvailableError(
                f"No trained model found for '{model_name}'. "
                "Run `python3 scripts/train_predictor.py` from inside "
                "smart-ew-scan-scheduler/ before starting the Smart ML "
                "scheduler. Sequential and Random strategies do not "
                "require a trained model and can be used immediately."
            ) from exc
    return _predictor_instances[model_name]
