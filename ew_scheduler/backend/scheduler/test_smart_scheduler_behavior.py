# backend/scheduler/test_smart_scheduler_behavior.py

import os
import sys

SCHED_DIR = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.abspath(os.path.join(SCHED_DIR, "..", "prediction"))

if SCHED_DIR not in sys.path:
    sys.path.insert(0, SCHED_DIR)

if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)

from history_manager import BandHistoryManager
from smart_scheduler import SmartScheduler
from behavior_detector import BehaviorDetector


class FixedMockPredictor:
    def __init__(self, prob_map=None, default_prob=0.30):
        self.prob_map = prob_map or {}
        self.default_prob = default_prob

    def predict_band(self, band, hm, t):
        return self.prob_map.get(band, self.default_prob)

    def predict_all_bands(self, bands, hm, t):
        return {
            b: self.predict_band(b, hm, t)
            for b in bands
        }


def _scheduler(**kwargs):
    predictor = FixedMockPredictor()
    return SmartScheduler(
        predictor,
        w_prob=0.0,
        w_stale=0.0,
        w_unc=0.0,
        w_recent=0.0,
        epsilon=0.0,
        w_behavior=kwargs.pop("w_behavior", 0.10),
        seed=42,
        **kwargs,
    )


def _disable_cold_start(scheduler, bands):
    scheduler._cold_start_remaining = []
    scheduler._cold_start_visited = set(bands)
    scheduler._cold_start_initialized = True


def test_behavior_bonus_favors_periodic_band():
    bands = [10, 20]

    predictor = FixedMockPredictor({
        10: 0.30,
        20: 0.30,
    })

    scheduler = SmartScheduler(
        predictor,
        w_prob=1.0,
        w_stale=0.0,
        w_unc=0.0,
        w_recent=0.0,
        epsilon=0.0,
        w_behavior=0.20,
        seed=42,
    )

    _disable_cold_start(scheduler, bands)

    hm = BandHistoryManager()

    for t in [10, 20, 30]:
        hm.ingest({
            "time": t,
            "band": 10,
            "detected": True,
        })

    score_10 = scheduler._score_band(
        10,
        0.30,
        hm,
        current_time=40,
    )

    score_20 = scheduler._score_band(
        20,
        0.30,
        hm,
        current_time=40,
    )

    assert score_10 > score_20


def test_behavior_bonus_is_bounded():
    bands = [10]

    scheduler = _scheduler(w_behavior=0.10)
    _disable_cold_start(scheduler, bands)

    hm = BandHistoryManager()

    for t in range(1, 11):
        hm.ingest({
            "time": t,
            "band": 10,
            "detected": True,
        })

    score = scheduler._score_band(
        10,
        0.0,
        hm,
        current_time=10,
    )

    assert 0.0 <= score <= 0.10


def test_unknown_behavior_does_not_create_large_bonus():
    bands = [10]

    scheduler = _scheduler(w_behavior=0.10)
    _disable_cold_start(scheduler, bands)

    hm = BandHistoryManager()

    hm.ingest({
        "time": 1,
        "band": 10,
        "detected": True,
    })

    score = scheduler._score_band(
        10,
        0.0,
        hm,
        current_time=1,
    )

    assert score <= 0.10


def test_behavior_detector_can_be_injected():
    detector = BehaviorDetector()

    scheduler = SmartScheduler(
        FixedMockPredictor(),
        behavior_detector=detector,
        w_behavior=0.10,
        seed=42,
    )

    assert scheduler.behavior_detector is detector


def test_behavior_does_not_change_cold_start():
    bands = list(range(10))

    predictor = FixedMockPredictor()

    standard = SmartScheduler(
        predictor,
        w_behavior=0.0,
        seed=123,
    )

    behavior = SmartScheduler(
        predictor,
        behavior_detector=BehaviorDetector(),
        w_behavior=0.20,
        seed=123,
    )

    hm_standard = BandHistoryManager()
    hm_behavior = BandHistoryManager()

    standard_decisions = [
        standard.select_band(
            bands,
            hm_standard,
            t,
        )
        for t in range(len(bands))
    ]

    behavior_decisions = [
        behavior.select_band(
            bands,
            hm_behavior,
            t,
        )
        for t in range(len(bands))
    ]

    assert standard_decisions == behavior_decisions


def test_behavior_intelligence_is_observation_only():
    bands = [10, 20]

    scheduler = SmartScheduler(
        FixedMockPredictor(),
        behavior_detector=BehaviorDetector(),
        w_behavior=0.10,
        epsilon=0.0,
        seed=42,
    )

    _disable_cold_start(scheduler, bands)

    hm = BandHistoryManager()

    # Only receiver observations are supplied.
    hm.ingest({
        "time": 1,
        "band": 10,
        "detected": True,
    })
    hm.ingest({
        "time": 2,
        "band": 10,
        "detected": True,
    })
    hm.ingest({
        "time": 3,
        "band": 10,
        "detected": True,
    })
    hm.ingest({
        "time": 4,
        "band": 10,
        "detected": True,
    })

    result = scheduler.behavior_detector.analyze(
        hm.get_band_history(10),
        current_time=4,
    )

    assert result.behavior in BehaviorDetector.BEHAVIORS
    assert "fixed" in result.scores
    assert "unknown" in result.scores

def test_scanning_behavior_favors_next_directional_band():
    """Scanning behavior should favor the next band in the observed direction."""
    scheduler = _scheduler()

    history = BandHistoryManager()

    observations = [
        {"time": 1, "band": 10, "detected": True},
        {"time": 2, "band": 11, "detected": True},
        {"time": 3, "band": 12, "detected": True},
        {"time": 4, "band": 13, "detected": True},
    ]

    for obs in observations:
        history.ingest(obs)

    global_behavior = scheduler._analyze_global_behavior(
        history,
        current_time=4,
    )

    assert global_behavior.behavior == "scanning"

    score_next = scheduler._score_band(
        band=14,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=global_behavior,
    )

    score_far = scheduler._score_band(
        band=30,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=global_behavior,
    )

    assert score_next > score_far


def test_scanning_behavior_favors_previous_directional_band_for_reverse_scan():
    """Reverse scanning should favor the next band in the reverse direction."""
    scheduler = _scheduler()

    history = BandHistoryManager()

    observations = [
        {"time": 1, "band": 20, "detected": True},
        {"time": 2, "band": 19, "detected": True},
        {"time": 3, "band": 18, "detected": True},
        {"time": 4, "band": 17, "detected": True},
    ]

    for obs in observations:
        history.ingest(obs)

    global_behavior = scheduler._analyze_global_behavior(
        history,
        current_time=4,
    )

    assert global_behavior.behavior == "scanning"

    score_next = scheduler._score_band(
        band=16,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=global_behavior,
    )

    score_wrong_direction = scheduler._score_band(
        band=18,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=global_behavior,
    )

    assert score_next > score_wrong_direction


def test_agile_behavior_favors_recently_observed_hop_band():
    """Agile behavior should favor recently observed hop destinations."""
    scheduler = _scheduler()

    history = BandHistoryManager()

    observations = [
        {"time": 1, "band": 10, "detected": True},
        {"time": 2, "band": 30, "detected": True},
        {"time": 3, "band": 12, "detected": True},
        {"time": 4, "band": 35, "detected": True},
        {"time": 5, "band": 11, "detected": True},
        {"time": 6, "band": 32, "detected": True},
    ]

    for obs in observations:
        history.ingest(obs)

    global_behavior = scheduler._analyze_global_behavior(
        history,
        current_time=6,
    )

    assert global_behavior.behavior == "agile"

    score_recent_hop = scheduler._score_band(
        band=32,
        prob=0.5,
        history_manager=history,
        current_time=6,
        global_behavior=global_behavior,
    )

    score_unseen = scheduler._score_band(
        band=80,
        prob=0.5,
        history_manager=history,
        current_time=6,
        global_behavior=global_behavior,
    )

    assert score_recent_hop > score_unseen


def test_global_behavior_bonus_is_bounded():
    """Global Agile/Scanning behavior bonus must never exceed w_behavior."""
    scheduler = _scheduler()

    history = BandHistoryManager()

    observations = [
        {"time": 1, "band": 10, "detected": True},
        {"time": 2, "band": 11, "detected": True},
        {"time": 3, "band": 12, "detected": True},
        {"time": 4, "band": 13, "detected": True},
    ]

    for obs in observations:
        history.ingest(obs)

    global_behavior = scheduler._analyze_global_behavior(
        history,
        current_time=4,
    )

    base_score = scheduler._score_band(
        band=30,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=None,
    )

    behavior_score = scheduler._score_band(
        band=14,
        prob=0.5,
        history_manager=history,
        current_time=4,
        global_behavior=global_behavior,
    )

    assert behavior_score - base_score <= scheduler.w_behavior + 1e-9