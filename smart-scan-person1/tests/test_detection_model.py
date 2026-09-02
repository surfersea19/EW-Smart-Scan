from backend.receiver.noise_model import NoiseModel, NoiseConfig
from backend.receiver.detection_model import DetectionModel, DetectionConfig


def test_noise_sample_is_cached_per_band_and_time():
    noise = NoiseModel(NoiseConfig(seed=1))
    a = noise.get_noise_sample_db(band=1, t=1)
    b = noise.get_noise_sample_db(band=1, t=1)
    assert a == b


def test_noise_samples_differ_across_time_generally():
    noise = NoiseModel(NoiseConfig(seed=1))
    samples = {noise.get_noise_sample_db(band=1, t=t) for t in range(20)}
    assert len(samples) > 1  # not all identical


def test_strong_signal_detected_almost_always():
    noise = NoiseModel(NoiseConfig(seed=2))
    detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
    hits = sum(detector.detect(band=1, t=t, true_signal_power_db=-40.0)[0] for t in range(300))
    assert hits / 300 > 0.99


def test_very_weak_signal_rarely_detected():
    noise = NoiseModel(NoiseConfig(seed=3))
    detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
    hits = sum(detector.detect(band=1, t=t, true_signal_power_db=-95.0)[0] for t in range(300))
    assert hits / 300 < 0.05


def test_false_alarm_rate_is_low_with_conservative_threshold():
    noise = NoiseModel(NoiseConfig(noise_floor_db=-90.0, noise_std_db=3.0, seed=4))
    detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
    false_alarms = sum(
        detector.detect(band=1, t=t, true_signal_power_db=None)[0] for t in range(300)
    )
    assert false_alarms / 300 < 0.05


def test_lowering_threshold_increases_false_alarm_rate():
    noise = NoiseModel(NoiseConfig(noise_floor_db=-90.0, noise_std_db=3.0, seed=5))
    strict = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
    loose = DetectionModel(noise, DetectionConfig(detection_threshold_db=-91.0))

    strict_fa = sum(strict.detect(band=2, t=t, true_signal_power_db=None)[0] for t in range(300))
    loose_fa = sum(loose.detect(band=2, t=t, true_signal_power_db=None)[0] for t in range(300))

    assert loose_fa > strict_fa
