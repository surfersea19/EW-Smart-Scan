import inspect
from backend.environment.spectrum import Spectrum
from backend.environment.emitter import Emitter, EmitterConfig
from backend.environment.emitter_behaviors import PeriodicBehavior, AgileBehavior
from backend.environment.rf_environment import RFEnvironment


def build_env():
    spectrum = Spectrum()
    e1 = Emitter(
        EmitterConfig(emitter_id="E1", emitter_type="radar_A", center_frequency_mhz=2000.0),
        PeriodicBehavior(on_duration=2, off_duration=2),
    )
    e2 = Emitter(
        EmitterConfig(emitter_id="E2", emitter_type="radar_B", center_frequency_mhz=5000.0),
        AgileBehavior(hop_frequencies_mhz=[5000, 5300, 5600], hop_interval=1),
    )
    env = RFEnvironment(spectrum, emitters=[e1, e2])
    return env, spectrum


def test_ground_truth_matches_behavior_definition():
    env, spectrum = build_env()
    env.run(6)
    band20 = spectrum.band_of_frequency(2000.0)
    # PeriodicBehavior(on=2, off=2) -> active at t=0,1,4,5 ; inactive t=2,3
    expected_active = {0, 1, 4, 5}
    for t in range(6):
        is_active = env.is_band_active(band20, t)
        assert is_active == (t in expected_active), f"mismatch at t={t}"


def test_is_band_active_only_reports_the_requested_band():
    """
    The receiver is only allowed to call is_band_active(band, t) for ONE
    band. This test checks that calling it for a band with no emitter
    returns False even while OTHER bands are active at that same t --
    i.e. it doesn't leak information about bands you didn't ask about.
    """
    env, spectrum = build_env()
    env.run(2)
    unrelated_band = spectrum.band_of_frequency(15000.0)  # nowhere near E1 or E2
    assert env.is_band_active(unrelated_band, 0) is False


def test_ground_truth_log_grows_by_num_emitters_each_step():
    env, spectrum = build_env()
    env.run(3)
    assert len(env.ground_truth_log) == 3 * len(env.emitters)


def test_receiver_facing_method_has_single_band_signature():
    """
    Structural guarantee: is_band_active must take a single band index,
    not a collection -- this is what stops the receiver from ever asking
    "what's active everywhere" in one call.
    """
    sig = inspect.signature(RFEnvironment.is_band_active)
    params = list(sig.parameters)
    assert "band" in params
    assert "bands" not in params  # would indicate an accidental bulk-query API
