"""
feature_config.py

The FeatureExtractor's shape (window_size, n_lags) determines the exact
feature columns a trained model expects. This MUST be identical between
training time (scripts/train_predictor.py) and live inference time
(services/prediction_service.py), or predict_proba() will silently see
misaligned columns. Both import these two constants instead of each
hardcoding their own copy.
"""

WINDOW_SIZE = 10
N_LAGS = 5

DEFAULT_MODEL_NAME = "random_forest"
