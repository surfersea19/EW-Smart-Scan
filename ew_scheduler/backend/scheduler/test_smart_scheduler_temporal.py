# backend/scheduler/test_smart_scheduler_temporal.py

import pytest
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
from periodicity_detector import PeriodicityDetector


class FixedMockPredictor:
    def __init__(self, prob_map=None, default_prob=0.30):
        self.prob_map = prob_map or {}
        self.default_prob = default_prob

    def predict_band(self, band, hm, t):
        return self.prob_map.get(band, self.default_prob)

    def predict_all_bands(self, bands, hm, t):
        return {b: self.predict_band(b, hm, t) for b in bands}


def test_temporal_score_boost_on_approaching_active_window():
    """
    Test that a periodic band receives a priority boost right at its expected pulse window.
    """
    bands = [10, 20]
    predictor = FixedMockPredictor({10: 0.30, 20: 0.30})
    scheduler = SmartScheduler(
        predictor,
        w_prob=0.5,
        w_stale=0.0,
        w_unc=0.0,
        w_recent=0.0,
        epsilon=0.0,
        w_temporal=0.25,
        seed=42,
    )
    # Bypass cold start
    scheduler._cold_start_remaining = []
    scheduler._cold_start_visited = set(bands)
    scheduler._cold_start_initialized = True

    hm = BandHistoryManager()
    # Band 10 has periodic hits at t=10, t=20, t=30 (period=10)
    hm.ingest({"time": 10, "band": 10, "detected": True})
    hm.ingest({"time": 20, "band": 10, "detected": True})
    hm.ingest({"time": 30, "band": 10, "detected": True})

    # Band 20 has no hits (or random)
    hm.ingest({"time": 10, "band": 20, "detected": False})
    hm.ingest({"time": 20, "band": 20, "detected": False})
    hm.ingest({"time": 30, "band": 20, "detected": False})

    # At t=40: Band 10 is at its exact expected active window
    score_10_t40 = scheduler._score_band(10, 0.30, hm, current_time=40)
    score_20_t40 = scheduler._score_band(20, 0.30, hm, current_time=40)

    assert score_10_t40 > score_20_t40, "Periodic band 10 must score higher at t=40"

    chosen = scheduler.select_band(bands, hm, current_time=40)
    assert chosen == 10, "Scheduler must select periodic band 10 at t=40"


def test_temporal_score_drops_during_off_window():
    """
    Test that when far from the expected pulse window, temporal bonus drops to near 0.
    """
    bands = [10, 20]
    # Give Band 20 slightly higher base probability (0.35 vs 0.30)
    predictor = FixedMockPredictor({10: 0.30, 20: 0.35})
    scheduler = SmartScheduler(
        predictor,
        w_prob=1.0,
        w_stale=0.0,
        w_unc=0.0,
        w_recent=0.0,
        w_active=0.0,
        epsilon=0.0,
        w_temporal=0.20,
        seed=42,
    )
    scheduler._cold_start_remaining = []
    scheduler._cold_start_visited = set(bands)
    scheduler._cold_start_initialized = True

    hm = BandHistoryManager()
    # Band 10 periodic at 10, 20, 30 (period=10)
    hm.ingest({"time": 10, "band": 10, "detected": True})
    hm.ingest({"time": 20, "band": 10, "detected": True})
    hm.ingest({"time": 30, "band": 10, "detected": True})

    # At t=35: Band 10 is halfway through off-cycle (proximity ~ 0)
    # Band 20 has higher probability and should win
    chosen_at_35 = scheduler.select_band(bands, hm, current_time=35)
    assert chosen_at_35 == 20, "Band 20 should win when Band 10 is in off-window at t=35"

    # At t=40: Band 10 enters expected active window and should win despite slightly lower base prob
    chosen_at_40 = scheduler.select_band(bands, hm, current_time=40)
    assert chosen_at_40 == 10, "Band 10 should win when entering active window at t=40"


def test_cold_start_permutation_preserved():
    """
    Verify cold start permutation operates normally regardless of temporal settings.
    """
    bands = list(range(10))
    predictor = FixedMockPredictor()

    sched_standard = SmartScheduler(predictor, w_temporal=0.0, seed=123)
    sched_temporal = SmartScheduler(predictor, w_temporal=0.25, seed=123)
    hm = BandHistoryManager()

    decisions_standard = [sched_standard.select_band(bands, hm, t) for t in range(len(bands))]
    decisions_temporal = [sched_temporal.select_band(bands, hm, t) for t in range(len(bands))]

    assert decisions_standard == decisions_temporal
    assert len(set(decisions_temporal)) == len(bands)


def test_warm_start_prior_compatibility():
    """
    Verify that Phase 5 persistent warm-start prior and Phase 6 temporal intelligence coexist cleanly.
    """
    bands = [1, 2]
    predictor = FixedMockPredictor({1: 0.30, 2: 0.30})

    from types import SimpleNamespace
    mock_prior = SimpleNamespace(
        bands=[
            SimpleNamespace(band_id=1, hit_ratio=0.8, confidence=1.0),
            SimpleNamespace(band_id=2, hit_ratio=0.1, confidence=1.0),
        ]
    )

    scheduler = SmartScheduler(
        predictor,
        prior_knowledge=mock_prior,
        warm_prior_weight=0.10,
        w_temporal=0.15,
        w_prob=0.5,
        w_stale=0.0,
        w_unc=0.0,
        w_recent=0.0,
        epsilon=0.0,
        seed=42,
    )
    scheduler._cold_start_remaining = []
    scheduler._cold_start_initialized = True

    hm = BandHistoryManager()
    score_1 = scheduler._score_band(1, 0.30, hm, current_time=1)
    score_2 = scheduler._score_band(2, 0.30, hm, current_time=1)

    # Band 1 has higher warm prior (0.8 vs 0.1) and no temporal history yet
    assert score_1 > score_2


def test_explain_decision_temporal():
    """
    Verify explain_decision runs cleanly and outputs without crashing.
    """
    bands = [5, 10]
    predictor = FixedMockPredictor()
    scheduler = SmartScheduler(predictor, w_temporal=0.15, seed=42)
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 5, "detected": True})
    hm.ingest({"time": 20, "band": 5, "detected": True})

    # Call explain_decision
    scheduler.explain_decision(bands, hm, current_time=25)
