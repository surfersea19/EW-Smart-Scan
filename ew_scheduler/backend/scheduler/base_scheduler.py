# backend/scheduler/base_scheduler.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prediction'))

from abc import ABC, abstractmethod
from history_manager import BandHistoryManager


class BaseScheduler(ABC):
    """
    All schedulers share this interface.
    The experiment runner calls select_band() without knowing
    which scheduler it is talking to.
    """

    @abstractmethod
    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:
        """
        Choose the next band to scan.
        Returns one band ID (integer).
        """
        pass

    def reset(self) -> None:
        """Reset internal state between simulation runs."""
        pass
