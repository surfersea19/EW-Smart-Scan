"""
detection_model.py

Turns "is there a signal here" into a probabilistic decision instead of
a perfect oracle lookup. Implements a simple energy detector:

    received_power = true_signal_power + noise_sample   (signal present)
    received_power = noise_sample                        (signal absent)
    detected = received_power > detection_threshold_db

This produces exactly the four classic outcomes:
    signal present, detected      -> HIT (true positive)
    signal present, not detected  -> MISSED DETECTION (false negative)
    signal absent, detected       -> FALSE ALARM (false positive)
    signal absent, not detected   -> correct rejection (true negative)

which are the building blocks of Pd and Pfa (ch. 13, 17), and of the
problem statement's requested figures of merit.
"""

from dataclasses import dataclass
from .noise_model import NoiseModel


@dataclass
class DetectionConfig:
    detection_threshold_db: float = -80.0


class DetectionModel:
    """
    Decides HIT/MISS given ground truth (is a signal really there, and
    how strong) plus a noise sample. Does NOT know about emitters or the
    environment directly -- it's a pure function of power in, power out.
    """

    def __init__(self, noise_model: NoiseModel, config: DetectionConfig = None):
        self.noise_model = noise_model
        self.config = config or DetectionConfig()

    def detect(self, band: int, t: int, true_signal_power_db: float = None) -> tuple:
        """
        true_signal_power_db=None means no emitter is actually transmitting
        in this band at this time (ground truth says inactive).

        Returns (detected: bool, measured_power_db: float) -- the measured
        power is returned even on a false alarm, since a real receiver
        doesn't know it was "just noise" until proven otherwise.
        """
        noise_sample = self.noise_model.get_noise_sample_db(band, t)

        if true_signal_power_db is not None:
            # Simplification: combining dB values additively rather than
            # converting to linear watts, summing, converting back. Close
            # enough for a scheduling-focused simulation; flag if we ever
            # need true RF power-summation accuracy.
            measured_power_db = true_signal_power_db + (noise_sample - self.noise_model.config.noise_floor_db)
        else:
            measured_power_db = noise_sample

        detected = measured_power_db > self.config.detection_threshold_db
        return detected, measured_power_db

    def __repr__(self):
        return f"DetectionModel(threshold={self.config.detection_threshold_db}dB)"


if __name__ == "__main__":
    noise = NoiseModel()
    detector = DetectionModel(noise)
    print(detector)

    print("\n--- Strong signal (-40dB), should almost always detect ---")
    hits = sum(detector.detect(band=1, t=t, true_signal_power_db=-40.0)[0] for t in range(200))
    print(f"Empirical Pd: {hits/200:.2%}")

    print("\n--- Weak signal (-88dB), close to threshold, should sometimes miss ---")
    hits = sum(detector.detect(band=2, t=t, true_signal_power_db=-88.0)[0] for t in range(200))
    print(f"Empirical Pd: {hits/200:.2%}")

    print("\n--- No signal at all, should rarely false-alarm ---")
    false_alarms = sum(detector.detect(band=3, t=t, true_signal_power_db=None)[0] for t in range(200))
    print(f"Empirical Pfa: {false_alarms/200:.2%}")
