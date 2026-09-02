# backend/scheduler/sequential_scheduler.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prediction'))

from base_scheduler import BaseScheduler
from history_manager import BandHistoryManager


class SequentialScheduler(BaseScheduler):
    """
    Baseline: scan bands in fixed cyclic order.
    B0 -> B1 -> B2 -> ... -> BN -> B0 -> B1 -> ...
    Makes no use of observations or predictions.
    Sets the performance floor.
    """

    def __init__(self):
        self._index = 0

    def reset(self) -> None:
        self._index = 0

    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:
        sorted_bands = sorted(bands)
        band         = sorted_bands[self._index % len(sorted_bands)]
        self._index += 1
        return band
