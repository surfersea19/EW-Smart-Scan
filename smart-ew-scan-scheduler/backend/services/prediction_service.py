"""
Prediction service.

Person 2's territory: feature engineering + ML prediction.

CRITICAL: predict() must only ever be given observation history, never
ground truth. The mock below deliberately only sees what get_simulation_engine()
.observe() has returned over time -- same constraint the real model must obey.

TO INTEGRATE PERSON 2's REAL CODE:
  Implement PredictorProtocol, swap the instantiation in get_predictor().
"""
from __future__ import annotations
import random
from collections import defaultdict
from typing import Protocol

from schemas.observation import Observation
from schemas.prediction import BandPrediction


class PredictorProtocol(Protocol):
    def predict(
        self, obs_history: list[Observation], num_bands: int, top_k: int = 5
    ) -> list[BandPrediction]: ...


class MockPredictor:
    """
    Heuristic stand-in: scores a band by recency-weighted hit frequency
    plus a little exploration noise. Not real ML -- just enough to drive
    the pipeline end to end.
    """

    def predict(
        self, obs_history: list[Observation], num_bands: int, top_k: int = 5
    ) -> list[BandPrediction]:
        scores: dict[int, float] = defaultdict(float)
        for i, obs in enumerate(obs_history[-50:]):
            if obs.detected:
                recency_weight = 1.0 + i * 0.02
                scores[obs.band] += recency_weight

        # normalize + add a little exploration noise so untried bands
        # occasionally surface
        max_score = max(scores.values(), default=1.0)
        results = []
        for band in range(num_bands):
            base = scores.get(band, 0.0) / max_score if max_score else 0.0
            noise = random.uniform(0, 0.1)
            prob = min(1.0, base * 0.85 + noise)
            results.append(BandPrediction(band=band, probability=round(prob, 3)))

        results.sort(key=lambda p: p.probability, reverse=True)
        return results[:top_k]


_predictor_instance: MockPredictor | None = None


def get_predictor() -> PredictorProtocol:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MockPredictor()
    return _predictor_instance
