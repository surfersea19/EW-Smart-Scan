from backend.environment.emitter import Emitter, EmitterConfig
from backend.environment.emitter_behaviors import (
    FixedBehavior, PeriodicBehavior, BurstyBehavior, AgileBehavior, ScanningBehavior,
)

CFG = EmitterConfig(emitter_id="E1", center_frequency_mhz=2000.0)


def test_fixed_behavior_always_on_by_default():
    e = Emitter(CFG, FixedBehavior())
    for t in range(10):
        assert e.get_state(t).active is True


def test_periodic_behavior_cycle_pattern():
    e = Emitter(CFG, PeriodicBehavior(on_duration=3, off_duration=2))
    expected = [True, True, True, False, False] * 2
    actual = [e.get_state(t).active for t in range(10)]
    assert actual == expected


def test_periodic_behavior_rejects_zero_durations():
    import pytest
    with pytest.raises(ValueError):
        PeriodicBehavior(on_duration=0, off_duration=2)


def test_bursty_behavior_is_reproducible_with_seed():
    e1 = Emitter(CFG, BurstyBehavior(transmit_probability=0.5, seed=123))
    e2 = Emitter(CFG, BurstyBehavior(transmit_probability=0.5, seed=123))
    seq1 = [e1.get_state(t).active for t in range(20)]
    seq2 = [e2.get_state(t).active for t in range(20)]
    assert seq1 == seq2


def test_bursty_behavior_probability_extremes():
    always_on = Emitter(CFG, BurstyBehavior(transmit_probability=1.0, seed=1))
    always_off = Emitter(CFG, BurstyBehavior(transmit_probability=0.0, seed=1))
    assert all(always_on.get_state(t).active for t in range(20))
    assert not any(always_off.get_state(t).active for t in range(20))


def test_agile_behavior_hops_through_list():
    e = Emitter(CFG, AgileBehavior(hop_frequencies_mhz=[100, 200, 300], hop_interval=1))
    freqs = [e.get_state(t).frequency_mhz for t in range(6)]
    assert freqs == [100, 200, 300, 100, 200, 300]


def test_agile_behavior_respects_hop_interval():
    e = Emitter(CFG, AgileBehavior(hop_frequencies_mhz=[100, 200], hop_interval=2))
    freqs = [e.get_state(t).frequency_mhz for t in range(4)]
    assert freqs == [100, 100, 200, 200]


def test_agile_behavior_always_active():
    e = Emitter(CFG, AgileBehavior(hop_frequencies_mhz=[100, 200]))
    assert all(e.get_state(t).active for t in range(10))


def test_scanning_behavior_sweeps_range():
    e = Emitter(CFG, ScanningBehavior(freq_start_mhz=0, freq_end_mhz=400, step_mhz=100, step_interval=1))
    freqs = [e.get_state(t).frequency_mhz for t in range(5)]
    assert freqs[0] == 0
    assert freqs[4] == 400


def test_scanning_behavior_ping_pong_reverses():
    e = Emitter(
        CFG,
        ScanningBehavior(freq_start_mhz=0, freq_end_mhz=200, step_mhz=100, step_interval=1, ping_pong=True),
    )
    freqs = [e.get_state(t).frequency_mhz for t in range(6)]
    # 0 -> 100 -> 200 -> 100 -> 0 -> 100 -> ...
    assert freqs == [0, 100, 200, 100, 0, 100]
