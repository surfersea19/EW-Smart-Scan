# backend/scheduler/random_scheduler.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prediction'))

import random
from base_scheduler import BaseScheduler
from history_manager import BandHistoryManager


class RandomScheduler(BaseScheduler):
    """
    Baseline: pick a uniformly random band each step.
    Makes no use of observations or predictions.
    If smart cannot beat this, ML predictions are not helping.
    """

    def __init__(self, seed: int = None):
        self._rng = random.Random(seed)

    def reset(self) -> None:
        pass

    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:
        return self._rng.choice(bands)
