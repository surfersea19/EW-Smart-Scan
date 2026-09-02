# backend/prediction/predict.py

import numpy as np
import joblib
import os
from feature_engineering import FeatureExtractor
from history_manager import BandHistoryManager


MODEL_DIR = os.path.join(os.path.dirname(__file__), "models", "saved")


class Predictor:
    """
    Real-time band activity predictor.

    At each time step, produces P(active) for every band.
    Uses a pre-trained model. Does NOT retrain online.
    This is what the scheduler calls at every decision point.
    """

    def __init__(
        self,
        model_name: str,
        feature_extractor: FeatureExtractor,
        model_dir: str = MODEL_DIR,
    ):
        self.fe            = feature_extractor
        self.model_name    = model_name
        self._feature_names = feature_extractor.feature_names()

        model_path = os.path.join(model_dir, f"{model_name}.joblib")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"No saved model at {model_path}. Run train.py first."
            )

        self.model = joblib.load(model_path)
        print(f"Predictor loaded: {model_name}")
        print(f"Features expected: {self._feature_names}")

    def predict_band(
        self,
        band: int,
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> float:
        """Predict P(active) for a single band. Returns float in [0, 1]."""
        features = self.fe.extract(band, history_manager, current_time)
        x = np.array(
            [features[n] for n in self._feature_names],
            dtype=np.float32,
        ).reshape(1, -1)
        return float(self.model.predict_proba(x)[0, 1])

    def predict_all_bands(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> dict[int, float]:
        """
        Predict P(active) for all bands in one batched model call.
        This is the primary method the scheduler calls.
        Returns {band_id: probability}.
        """
        if not bands:
            return {}

        feature_matrix = []
        for band in bands:
            features = self.fe.extract(band, history_manager, current_time)
            feature_matrix.append([features[n] for n in self._feature_names])

        X     = np.array(feature_matrix, dtype=np.float32)
        probs = self.model.predict_proba(X)[:, 1]

        return {band: float(prob) for band, prob in zip(bands, probs)}

    def uncertainty(
        self,
        band: int,
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> float:
        """
        Uncertainty = distance from 0.5.
        0.5 = maximally uncertain, 0.0 = fully confident.
        """
        prob = self.predict_band(band, history_manager, current_time)
        return float(0.5 - abs(prob - 0.5))

    def ranked_predictions(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> list[tuple[int, float]]:
        """
        Bands sorted by predicted probability, highest first.
        Returns [(band_id, probability), ...].
        """
        predictions = self.predict_all_bands(bands, history_manager, current_time)
        return sorted(predictions.items(), key=lambda x: x[1], reverse=True)

    def summarise(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
        top_n: int = 10,
    ) -> None:
        """Print readable prediction summary. Useful for debugging."""
        ranked = self.ranked_predictions(bands, history_manager, current_time)
        print(f"\nPredictions at t={current_time} (top {top_n}):")
        print(f"  {'Band':<8} {'P(active)':<12} Confidence")
        print(f"  {'-'*35}")
        for band, prob in ranked[:top_n]:
            bar        = "█" * int(prob * 20)
            confidence = ("HIGH" if abs(prob - 0.5) > 0.3 else
                          "MED"  if abs(prob - 0.5) > 0.15 else "LOW")
            print(f"  {band:<8} {prob:<12.3f} {confidence}  {bar}")
