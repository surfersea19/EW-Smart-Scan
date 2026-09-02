"""
virtual_receiver.py

Models the EW receiver's physical limitation: it can only look at one
band at a time (instantaneous bandwidth << total spectrum). This is the
ONLY class allowed to query RFEnvironment, and it only ever asks about
a single band per scan — enforcing the ground-truth/observation
separation from ch. 12.

MVP behavior: deterministic hit/miss (signal present -> HIT, absent ->
MISS). Noise/probabilistic detection (ch. 13, 17) comes later as an
optional detection_model.py the receiver delegates to.
"""

from dataclasses import dataclass
from ..environment.rf_environment import RFEnvironment
from .detection_model import DetectionModel


@dataclass
class Observation:
    """
    What the receiver actually saw. This is the ONLY thing that should
    ever be handed to the ML/scheduler side of the project (ch. 19).
    Notice: no emitter_id. The receiver doesn't know which emitter it
    detected -- only that something was there, or wasn't.
    """
    time: int
    scanned_band: int
    detected: bool
    measured_power_db: float = None
    pulse_width_us: float = None
    pri_us: float = None


@dataclass
class ReceiverConfig:
    """Physical/operational parameters of the receiver."""
    dwell_time: int = 1     # time steps spent observing a band per scan
    tuning_time: int = 0    # time steps "lost" retuning to a new band (ch. 16)


class VirtualReceiver:
    """
    A software model of the EW receiver. Call scan(band, t) to observe
    a single band at a single time step. This is the ONLY class that
    is allowed to touch RFEnvironment.
    """

    def __init__(self, environment: RFEnvironment, config: ReceiverConfig = None,
                 detection_model: DetectionModel = None):
        self.environment = environment
        self.config = config or ReceiverConfig()
        # If no detection_model is given, falls back to the original
        # deterministic "active=HIT, always" oracle behavior -- keeps
        # earlier code/tests working unchanged.
        self.detection_model = detection_model
        self.current_band = None
        self.observation_log: list = []  # list[Observation], everything the receiver has seen

    def scan(self, band: int, t: int) -> Observation:
        """
        Tune to `band` and observe at time `t`. Asks the environment about
        ONLY this band -- never the full ground truth.

        MVP detection rule: if the band is active, it's a HIT, and we pull
        the (deterministic, noiseless) signal characteristics through. This
        will be replaced by a probabilistic detection_model.py later.
        """
        is_active = self.environment.is_band_active(band, t)
        record = self._find_ground_truth_record(band, t) if is_active else None

        pulse_width = None
        pri = None

        if self.detection_model is not None:
            # Probabilistic path: even an active emitter can be missed
            # (weak signal), and an inactive band can false-alarm.
            true_power = record.power_db if record is not None else None
            detected, measured_power = self.detection_model.detect(band, t, true_power)
            if detected and record is not None:
                # Only a real emitter has meaningful pulse width / PRI to report.
                pulse_width = record.pulse_width_us
                pri = record.pri_us
        else:
            # Deterministic fallback: active=HIT, always (original MVP behavior).
            detected = is_active
            measured_power = record.power_db if (detected and record is not None) else None
            if detected and record is not None:
                pulse_width = record.pulse_width_us
                pri = record.pri_us

        observation = Observation(
            time=t,
            scanned_band=band,
            detected=detected,
            measured_power_db=measured_power,
            pulse_width_us=pulse_width,
            pri_us=pri,
        )

        self.current_band = band
        self.observation_log.append(observation)
        return observation

    def _find_ground_truth_record(self, band: int, t: int):
        """
        Internal helper only: pulls the specific record's signal parameters
        so the observation has realistic power/PW/PRI values. This still
        respects the rule -- we already know detected=True for THIS band,
        we are not looking at any other band's state.
        """
        for r in self.environment.ground_truth_log:
            if r.time == t and r.band == band and r.active:
                return r
        return None

    def __repr__(self):
        return (
            f"VirtualReceiver(dwell={self.config.dwell_time}, "
            f"tuning={self.config.tuning_time}, observations={len(self.observation_log)})"
        )


if __name__ == "__main__":
    from ..environment.spectrum import Spectrum
    from ..environment.emitter import Emitter, EmitterConfig
    from ..environment.emitter_behaviors import PeriodicBehavior, AgileBehavior

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
    env.run(6)

    receiver = VirtualReceiver(env)

    # A naive sequential scanner: just walk band 0, 1, 2, ... regardless
    # of where the emitters actually are. This will mostly MISS -- that's
    # the whole point (this is the "dumb" baseline the smart scheduler
    # will later beat).
    print("--- Naive sequential scan ---")
    for t in range(6):
        band_to_scan = t % spectrum.num_bands
        obs = receiver.scan(band_to_scan, t)
        print(obs)

    print("\n--- Deliberately scanning where E1 lives (band 20) ---")
    band20 = spectrum.band_of_frequency(2000.0)
    for t in range(4):
        obs = receiver.scan(band20, t)
        print(obs)
