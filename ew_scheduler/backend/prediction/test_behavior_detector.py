# backend/prediction/test_behavior_detector.py

from backend.prediction.behavior_detector import BehaviorDetector


def obs(time, band, detected=True):
    return {
        "time": time,
        "band": band,
        "detected": detected,
    }


def test_unknown_with_insufficient_evidence():
    detector = BehaviorDetector(min_hits=4)

    result = detector.analyze(
        [
            obs(1, 10),
            obs(2, 10),
            obs(3, 10, False),
        ],
        current_time=3,
    )

    assert result.behavior == "unknown"


def test_fixed_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [obs(t, 10) for t in range(1, 7)],
        current_time=6,
    )

    assert result.behavior == "fixed"
    assert result.confidence >= 0.5
    assert result.features.unique_hit_bands == 1


def test_periodic_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [obs(t, 10) for t in [1, 3, 5, 7, 9, 11]],
        current_time=11,
    )

    assert result.behavior == "periodic"
    assert result.features.inter_hit_cv == 0.0


def test_bursty_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [obs(t, 10) for t in [1, 2, 6, 7, 13, 14]],
        current_time=14,
    )

    assert result.behavior == "bursty"
    assert result.features.inter_hit_cv > 0.0


def test_scanning_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [obs(t, 20 + t) for t in range(6)],
        current_time=5,
    )

    assert result.behavior == "scanning"
    assert result.features.adjacent_ratio == 1.0
    assert result.features.direction_consistency == 1.0


def test_agile_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [
            obs(1, 10),
            obs(2, 30),
            obs(3, 12),
            obs(4, 35),
            obs(5, 11),
            obs(6, 32),
        ],
        current_time=6,
    )

    assert result.behavior == "agile"
    assert result.features.unique_hit_bands >= 4


def test_misses_affect_hit_ratio_but_not_movement_sequence():
    detector = BehaviorDetector()

    result = detector.analyze(
        [
            obs(1, 20),
            obs(2, 21, False),
            obs(3, 21),
            obs(4, 22),
            obs(5, 23),
        ],
        current_time=5,
    )

    assert result.features.hit_ratio == 4 / 5
    assert result.features.unique_hit_bands == 4


def test_future_observations_are_ignored():
    detector = BehaviorDetector()

    result = detector.extract_features(
        [
            obs(1, 10),
            obs(2, 10),
            obs(3, 10),
            obs(4, 10),
            obs(100, 99),
        ],
        current_time=4,
    )

    assert result.hit_count == 4
    assert result.unique_hit_bands == 1

def test_ping_pong_scanning_behavior():
    detector = BehaviorDetector()

    result = detector.analyze(
        [
            obs(1, 10),
            obs(2, 11),
            obs(3, 12),
            obs(4, 13),
            obs(5, 14),
            obs(6, 15),
            obs(7, 14),
            obs(8, 13),
            obs(9, 12),
            obs(10, 11),
        ],
        current_time=10,
    )

    assert result.behavior == "scanning"


def test_non_structured_large_jumps_are_not_perfect_agile():
    detector = BehaviorDetector()

    result = detector.analyze(
        [
            obs(1, 10),
            obs(2, 25),
            obs(3, 11),
            obs(4, 40),
            obs(5, 18),
            obs(6, 33),
        ],
        current_time=6,
    )

    assert result.scores["agile"] < 1.0