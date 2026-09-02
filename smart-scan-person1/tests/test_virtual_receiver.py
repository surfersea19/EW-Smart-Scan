import dataclasses
from backend.environment.spectrum import Spectrum
from backend.environment.emitter import Emitter, EmitterConfig
from backend.environment.emitter_behaviors import PeriodicBehavior
from backend.environment.rf_environment import RFEnvironment
from backend.receiver.virtual_receiver import VirtualReceiver, Observation
from backend.receiver.noise_model import NoiseModel, NoiseConfig
from backend.receiver.detection_model import DetectionModel, DetectionConfig


def build_env():
    spectrum = Spectrum()
    e1 = Emitter(
        EmitterConfig(emitter_id="E1", center_frequency_mhz=2000.0, power_db=-40.0),
        PeriodicBehavior(on_duration=2, off_duration=2),
    )
    env = RFEnvironment(spectrum, emitters=[e1])
    env.run(4)
    return env, spectrum


def test_observation_has_no_emitter_id_field():
    """
    Structural guarantee for ch. 12/19: the receiver must never reveal
    which emitter it detected -- only whether something was there.
    """
    field_names = {f.name for f in dataclasses.fields(Observation)}
    assert "emitter_id" not in field_names
    assert "emitter_type" not in field_names


def test_deterministic_scan_matches_ground_truth():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env)  # no detection_model -> deterministic oracle
    band20 = spectrum.band_of_frequency(2000.0)

    obs0 = receiver.scan(band20, 0)  # active
    obs2 = receiver.scan(band20, 2)  # inactive

    assert obs0.detected is True
    assert obs0.measured_power_db == -40.0
    assert obs2.detected is False
    assert obs2.measured_power_db is None


def test_scanning_empty_band_never_detects():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env)
    empty_band = spectrum.band_of_frequency(15000.0)
    for t in range(4):
        assert receiver.scan(empty_band, t).detected is False


def test_probabilistic_receiver_strong_signal_detects_reliably():
    env, spectrum = build_env()
    noise = NoiseModel(NoiseConfig(seed=1))
    detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
    receiver = VirtualReceiver(env, detection_model=detector)
    band20 = spectrum.band_of_frequency(2000.0)

    # -40dB signal is far above -80dB threshold; should always detect when active
    assert receiver.scan(band20, 0).detected is True
    assert receiver.scan(band20, 1).detected is True


def test_observation_log_accumulates_in_order():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env)
    band20 = spectrum.band_of_frequency(2000.0)
    for t in range(4):
        receiver.scan(band20, t)
    assert [o.time for o in receiver.observation_log] == [0, 1, 2, 3]
