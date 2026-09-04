import os
import sys

SCHED_DIR = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.abspath(os.path.join(SCHED_DIR, "..", "prediction"))
if SCHED_DIR not in sys.path:
    sys.path.insert(0, SCHED_DIR)
if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)

from history_manager import BandHistoryManager
from random_scheduler import RandomScheduler


def test_random_scheduler_reset_restores_seeded_sequence():
    scheduler = RandomScheduler(seed=123)
    bands = [10, 20, 30, 40]
    hm = BandHistoryManager()

    first_run = [scheduler.select_band(bands, hm, current_time=t) for t in range(12)]
    scheduler.reset()
    second_run = [scheduler.select_band(bands, hm, current_time=t) for t in range(12)]

    assert second_run == first_run


def test_random_scheduler_different_seeds_normally_differ():
    bands = list(range(20))
    hm = BandHistoryManager()
    first_scheduler = RandomScheduler(seed=1)
    second_scheduler = RandomScheduler(seed=2)
    first = [first_scheduler.select_band(bands, hm, current_time=t) for t in range(10)]
    second = [second_scheduler.select_band(bands, hm, current_time=t) for t in range(10)]

    assert first != second
