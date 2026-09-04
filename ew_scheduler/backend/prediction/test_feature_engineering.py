import pytest
import sys
import os
import math

PRED_DIR = os.path.dirname(os.path.abspath(__file__))
if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)

from history_manager import BandHistoryManager
from feature_engineering import FeatureExtractor, UNKNOWN_POWER


def test_time_decay_monotonic():
    """
    Test A: Time decay on a single band.
    History: t=10 HIT.
    Extract at t=10, t=30, t=50.
    Verify time_decayed_hit_sum decreases monotonically.
    """
    fe = FeatureExtractor(tau=20.0)
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 5, "detected": True, "power": -50.0})

    f_t10 = fe.extract(5, hm, current_time=10)
    f_t30 = fe.extract(5, hm, current_time=30)
    f_t50 = fe.extract(5, hm, current_time=50)

    val_10 = f_t10["time_decayed_hit_sum"]
    val_30 = f_t30["time_decayed_hit_sum"]
    val_50 = f_t50["time_decayed_hit_sum"]

    # Exact expected values: exp(0)=1.0, exp(-1)=0.367879, exp(-2)=0.135335
    assert abs(val_10 - 1.0) < 1e-5
    assert abs(val_30 - math.exp(-1)) < 1e-5
    assert abs(val_50 - math.exp(-2)) < 1e-5

    assert val_10 > val_30 > val_50, "time_decayed_hit_sum must strictly decrease with elapsed time"


def test_no_rescan_decay():
    """
    Test B: Time decay without rescanning.
    History: t=10 HIT. No observations added afterward.
    Extract at t=10, t=30, t=100.
    Verify the decayed feature changes even though history is unchanged.
    """
    fe = FeatureExtractor(tau=20.0)
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 8, "detected": True, "power": -45.0})

    # History remains static with 1 observation
    assert hm.scan_count(8) == 1

    f_10 = fe.extract(8, hm, current_time=10)["time_decayed_hit_sum"]
    f_30 = fe.extract(8, hm, current_time=30)["time_decayed_hit_sum"]
    f_100 = fe.extract(8, hm, current_time=100)["time_decayed_hit_sum"]

    assert f_10 == pytest.approx(1.0, rel=1e-4)
    assert f_30 == pytest.approx(math.exp(-1.0), rel=1e-4)
    assert f_100 == pytest.approx(math.exp(-4.5), rel=1e-4)
    assert f_100 < 0.02, "After 90 idle ticks, activity must decay to near 0"


def test_consecutive_hits():
    """
    Test C: Consecutive hits counting.
    HIT, HIT, HIT -> consecutive_hits=3.
    Then MISS -> consecutive_hits=0.
    """
    fe = FeatureExtractor()
    hm = BandHistoryManager()

    hm.ingest({"time": 1, "band": 3, "detected": True, "power": -50.0})
    assert fe.extract(3, hm, current_time=1)["consecutive_hits"] == 1.0

    hm.ingest({"time": 2, "band": 3, "detected": True, "power": -50.0})
    assert fe.extract(3, hm, current_time=2)["consecutive_hits"] == 2.0

    hm.ingest({"time": 3, "band": 3, "detected": True, "power": -50.0})
    assert fe.extract(3, hm, current_time=3)["consecutive_hits"] == 3.0

    # Next observation is a MISS
    hm.ingest({"time": 4, "band": 3, "detected": False})
    assert fe.extract(3, hm, current_time=4)["consecutive_hits"] == 0.0


def test_consecutive_misses():
    """
    Test D: Consecutive misses counting.
    MISS, MISS -> consecutive_misses=2.
    Then HIT -> consecutive_misses=0.
    """
    fe = FeatureExtractor()
    hm = BandHistoryManager()

    hm.ingest({"time": 1, "band": 7, "detected": False})
    assert fe.extract(7, hm, current_time=1)["consecutive_misses"] == 1.0

    hm.ingest({"time": 2, "band": 7, "detected": False})
    assert fe.extract(7, hm, current_time=2)["consecutive_misses"] == 2.0

    # Next observation is a HIT
    hm.ingest({"time": 3, "band": 7, "detected": True, "power": -55.0})
    assert fe.extract(7, hm, current_time=3)["consecutive_misses"] == 0.0


def test_adjacent_activity_and_decay():
    """
    Test E: Adjacent band activity.
    B40 HIT at t=10.
    Extract B41 at t=10 -> adjacent_band_activity > 0.
    Extract B42 at t=10 -> adjacent_band_activity == 0.
    Verify activity decays with time at t=30.
    """
    fe = FeatureExtractor(tau=20.0)
    hm = BandHistoryManager()

    hm.ingest({"time": 10, "band": 40, "detected": True, "power": -60.0})

    # At t=10:
    # Band 41 neighbor is Band 40 (hit at t=10) -> adjacent_activity = exp(0) = 1.0
    f_b41_t10 = fe.extract(41, hm, current_time=10)
    assert f_b41_t10["adjacent_band_activity"] == pytest.approx(1.0, rel=1e-4)

    # Band 39 neighbor is Band 40 (hit at t=10) -> adjacent_activity = exp(0) = 1.0
    f_b39_t10 = fe.extract(39, hm, current_time=10)
    assert f_b39_t10["adjacent_band_activity"] == pytest.approx(1.0, rel=1e-4)

    # Band 42 neighbors are 41 and 43 (both unobserved / 0 hits) -> adjacent_activity = 0.0
    f_b42_t10 = fe.extract(42, hm, current_time=10)
    assert f_b42_t10["adjacent_band_activity"] == 0.0

    # At t=30 (20 ticks later):
    # Band 41 neighbor Band 40 activity decays to exp(-20/20) = exp(-1) = 0.3679
    f_b41_t30 = fe.extract(41, hm, current_time=30)
    assert f_b41_t30["adjacent_band_activity"] == pytest.approx(math.exp(-1), rel=1e-4)
    assert f_b41_t30["adjacent_band_activity"] < f_b41_t10["adjacent_band_activity"]


def test_unknown_power_not_stronger_than_real_signal():
    """
    Test F: Unknown power representation.
    Verify an unobserved band receives UNKNOWN_POWER = -100.0 dBm,
    which is strictly less than real observed radar powers (-90 to -35 dBm).
    """
    fe = FeatureExtractor()
    hm = BandHistoryManager()

    # Band 1 is unobserved
    f_unobserved = fe.extract(1, hm, current_time=10)
    assert f_unobserved["last_power"] == UNKNOWN_POWER
    assert f_unobserved["last_power"] == -100.0

    # Band 2 has real weak detection (-85 dBm)
    hm.ingest({"time": 10, "band": 2, "detected": True, "power": -85.0})
    f_detected = fe.extract(2, hm, current_time=10)
    assert f_detected["last_power"] == -85.0

    # Unobserved power must be strictly weaker than any real detection
    assert f_unobserved["last_power"] < f_detected["last_power"], (
        "Unobserved band power must be lower than real detected signal power"
    )
