# backend/prediction/test_periodicity_detector.py

import pytest
import os
import sys

PRED_DIR = os.path.dirname(os.path.abspath(__file__))
if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)

from history_manager import BandHistoryManager
from periodicity_detector import PeriodicityDetector, PeriodicityResult, UNKNOWN_TIME


def test_zero_hits():
    detector = PeriodicityDetector()
    res = detector.analyze_hits([], current_time=100)
    assert not res.is_periodic
    assert res.estimated_period == 0.0
    assert res.period_regularity == 0.0
    assert res.confidence == 0.0
    assert res.last_hit_time is None
    assert res.expected_next_time is None
    assert res.time_to_next == UNKNOWN_TIME
    assert res.temporal_proximity == 0.0
    assert res.recurrence_score == 0.0


def test_single_hit():
    detector = PeriodicityDetector()
    res = detector.analyze_hits([25], current_time=50)
    assert not res.is_periodic
    assert res.estimated_period == 0.0
    assert res.period_regularity == 0.0
    assert res.confidence == 0.0
    assert res.last_hit_time == 25
    assert res.expected_next_time is None
    assert res.time_to_next == UNKNOWN_TIME
    assert res.temporal_proximity == 0.0


def test_two_regular_hits():
    detector = PeriodicityDetector()
    res = detector.analyze_hits([10, 20], current_time=25)
    assert res.estimated_period == 10.0
    assert res.period_regularity == 1.0
    assert res.last_hit_time == 20
    assert res.expected_next_time == 30
    assert res.time_to_next == 5.0
    assert 0.0 <= res.temporal_proximity <= 1.0


def test_three_regular_hits():
    detector = PeriodicityDetector()
    res = detector.analyze_hits([10, 20, 30], current_time=30)
    assert res.is_periodic
    assert res.estimated_period == 10.0
    assert res.period_regularity == 1.0
    assert res.confidence >= 0.6
    assert res.last_hit_time == 30
    assert res.time_to_next == 0.0
    assert res.temporal_proximity == pytest.approx(1.0, abs=1e-3)


def test_consecutive_burst_dwell_clustering():
    detector = PeriodicityDetector(cluster_gap=1)
    # Burst 1 at 10..12, Burst 2 at 30..32, Burst 3 at 50..52
    hits = [10, 11, 12, 30, 31, 32, 50, 51, 52]
    res = detector.analyze_hits(hits, current_time=55)
    assert res.is_periodic
    assert res.estimated_period == 20.0
    assert res.period_regularity >= 0.95
    assert res.last_hit_time == 52
    # Next burst onset expected at 70 (or 50 + 20)
    assert res.expected_next_time == 70


def test_irregular_bursty_hits():
    detector = PeriodicityDetector()
    # Intermittent intervals with large variance: 13, 18, 17, 34
    hits = [10, 23, 41, 58, 92]
    res = detector.analyze_hits(hits, current_time=100)
    # Irregular intervals should have low regularity and not be marked periodic
    assert not res.is_periodic or res.confidence < 0.5
    assert res.period_regularity < 0.75


def test_jittered_periodic_hits():
    detector = PeriodicityDetector()
    # Nominal period 15 with slight +/- 1 jitter
    hits = [10, 26, 40, 55, 71]
    res = detector.analyze_hits(hits, current_time=75)
    assert res.is_periodic
    assert 14.0 <= res.estimated_period <= 16.0
    assert res.period_regularity > 0.80


def test_sparse_missed_cycles():
    detector = PeriodicityDetector()
    # Periodic with T=10, but receiver missed scan at 20 and 50 -> intervals: 20, 10, 20
    hits = [10, 30, 40, 60]
    res = detector.analyze_hits(hits, current_time=60)
    assert res.is_periodic
    assert res.estimated_period == pytest.approx(10.0, abs=0.5)


def test_proximity_evolution():
    detector = PeriodicityDetector()
    hits = [10, 20, 30, 40]

    # At t=40 (right after hit):
    res_40 = detector.analyze_hits(hits, current_time=40)
    assert res_40.temporal_proximity == pytest.approx(1.0, abs=1e-3)
    assert res_40.time_to_next == 0.0

    # At t=45 (halfway through period 10):
    res_45 = detector.analyze_hits(hits, current_time=45)
    assert res_45.temporal_proximity < 0.1
    assert res_45.time_to_next == 5.0

    # At t=49 (1 step before next expected hit at 50):
    res_49 = detector.analyze_hits(hits, current_time=49)
    assert res_49.temporal_proximity > 0.6
    assert res_49.time_to_next == 1.0

    # At t=50 (exact next cycle):
    res_50 = detector.analyze_hits(hits, current_time=50)
    assert res_50.temporal_proximity == pytest.approx(1.0, abs=1e-3)
    assert res_50.time_to_next == 0.0


def test_no_future_leakage():
    detector = PeriodicityDetector()
    full_history = [10, 20, 30, 40, 50, 60]

    # When evaluating at t=25, hits at 30, 40, 50, 60 must be completely ignored
    res_at_25 = detector.analyze_hits(full_history, current_time=25)
    assert res_at_25.last_hit_time == 20
    assert res_at_25.expected_next_time == 30
    assert res_at_25.time_to_next == 5.0

    # When evaluating at t=5, no hits exist yet
    res_at_5 = detector.analyze_hits(full_history, current_time=5)
    assert res_at_5.last_hit_time is None
    assert res_at_5.estimated_period == 0.0


def test_analyze_band_with_history_manager():
    detector = PeriodicityDetector()
    hm = BandHistoryManager()

    hm.ingest({"time": 10, "band": 5, "detected": True})
    hm.ingest({"time": 15, "band": 5, "detected": False})
    hm.ingest({"time": 20, "band": 5, "detected": True})
    hm.ingest({"time": 25, "band": 5, "detected": False})
    hm.ingest({"time": 30, "band": 5, "detected": True})

    res = detector.analyze_band(hm, band=5, current_time=30)
    assert res.is_periodic
    assert res.estimated_period == 10.0
    assert res.last_hit_time == 30
    assert res.temporal_proximity == pytest.approx(1.0, abs=1e-3)
