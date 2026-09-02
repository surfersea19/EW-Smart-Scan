"""
Scheduler service.

Person 2's territory: turns predictions into a next-scan decision, with
some exploration/exploitation tradeoff. Also hosts the baseline strategies
(sequential / random / priority) purely so the comparison feature works
without needing Person 2's ML scheduler.

TO INTEGRATE PERSON 2's REAL CODE:
  Implement SchedulerProtocol for the "smart_ml" strategy, swap it in
  get_scheduler(). Baseline strategies can stay as-is (they're Person 3's
  responsibility for the comparison feature).
"""
from __future__ import annotations
import random
from typing import Protocol

from schemas.prediction import BandPrediction
from schemas.scheduler import SchedulerDecision


class SchedulerProtocol(Protocol):
    def decide(
        self,
        predictions: list[BandPrediction],
        current_band: int,
        num_bands: int,
        recently_scanned: set[int],
    ) -> SchedulerDecision: ...


class MockSmartScheduler:
    """Epsilon-greedy: mostly exploit top prediction, sometimes explore."""

    def __init__(self, epsilon: float = 0.15):
        self.epsilon = epsilon

    def decide(
        self,
        predictions: list[BandPrediction],
        current_band: int,
        num_bands: int,
        recently_scanned: set[int],
    ) -> SchedulerDecision:
        if predictions and random.random() > self.epsilon:
            # prefer high-probability bands not scanned very recently
            candidates = sorted(
                predictions,
                key=lambda p: p.probability - (0.3 if p.band in recently_scanned else 0),
                reverse=True,
            )
            choice = candidates[0]
            reason = "high predicted activity, not recently scanned"
            return SchedulerDecision(next_band=choice.band, dwell_time=1, reason=reason)
        band = random.randint(0, num_bands - 1)
        return SchedulerDecision(next_band=band, dwell_time=1, reason="exploration")


class SequentialScheduler:
    def decide(self, predictions, current_band, num_bands, recently_scanned):
        return SchedulerDecision(
            next_band=(current_band + 1) % num_bands,
            dwell_time=1,
            reason="sequential sweep",
        )


class RandomScheduler:
    def decide(self, predictions, current_band, num_bands, recently_scanned):
        return SchedulerDecision(
            next_band=random.randint(0, num_bands - 1),
            dwell_time=1,
            reason="random",
        )


_schedulers: dict[str, SchedulerProtocol] = {}


def get_scheduler(strategy: str) -> SchedulerProtocol:
    if strategy not in _schedulers:
        if strategy == "sequential":
            _schedulers[strategy] = SequentialScheduler()
        elif strategy == "random":
            _schedulers[strategy] = RandomScheduler()
        else:  # "smart_ml" and fallback "priority" both use the smart mock for now
            _schedulers[strategy] = MockSmartScheduler()
    return _schedulers[strategy]
