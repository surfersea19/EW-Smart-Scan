"""
rf_environment.py

The simulated RF world. Owns a collection of Emitters and a Spectrum.
At each time step, asks every emitter for its current state and records
that as ground truth.

This class knows everything. The receiver (built next) is only ever
allowed to query it for ONE band at a time — see virtual_receiver.py.
Nothing in this file should ever be handed directly to the ML/scheduler
side of the project; ground truth is for evaluation only (ch. 10, 12).
"""

from dataclasses import dataclass, field
from .spectrum import Spectrum
from .emitter import Emitter, EmitterState


@dataclass
class GroundTruthRecord:
    """One row of ground truth: what one emitter was doing at one time step."""
    time: int
    emitter_id: str
    emitter_type: str
    band: int
    active: bool
    frequency_mhz: float = None
    power_db: float = None
    pulse_width_us: float = None
    pri_us: float = None


class RFEnvironment:
    """
    The full simulated world: a spectrum plus a set of emitters, advancing
    through discrete time steps and recording ground truth at each one.
    """

    def __init__(self, spectrum: Spectrum, emitters: list = None):
        self.spectrum = spectrum
        self.emitters: list = emitters or []
        self.current_time: int = 0
        self.ground_truth_log: list = []  # list[GroundTruthRecord], full history

    def add_emitter(self, emitter: Emitter):
        self.emitters.append(emitter)

    def step(self) -> list:
        """
        Advance the world by one time step. Ask every emitter for its
        state, convert active emitters' frequencies to band indices,
        record ground truth, and return this step's records.
        """
        step_records = []

        for emitter in self.emitters:
            state: EmitterState = emitter.get_state(self.current_time)

            band = None
            if state.active and state.frequency_mhz is not None:
                # An emitter could in principle report a frequency outside
                # our spectrum config; that's a scenario bug, so let it raise.
                band = self.spectrum.band_of_frequency(state.frequency_mhz)

            record = GroundTruthRecord(
                time=self.current_time,
                emitter_id=emitter.emitter_id,
                emitter_type=emitter.emitter_type,
                band=band,
                active=state.active,
                frequency_mhz=state.frequency_mhz,
                power_db=state.power_db,
                pulse_width_us=state.pulse_width_us,
                pri_us=state.pri_us,
            )
            step_records.append(record)
            self.ground_truth_log.append(record)

        self.current_time += 1
        return step_records

    def run(self, num_steps: int) -> list:
        """Convenience: step forward num_steps times, return the full log."""
        for _ in range(num_steps):
            self.step()
        return self.ground_truth_log

    def active_bands_at(self, t: int) -> set:
        """
        Ground-truth helper (for evaluation only, NEVER for the receiver):
        which bands had at least one active emitter at time t?
        """
        return {
            r.band for r in self.ground_truth_log
            if r.time == t and r.active and r.band is not None
        }

    def is_band_active(self, band: int, t: int) -> bool:
        """
        Ground-truth helper: was this specific band active at time t?
        This is the ONLY method the virtual receiver should call — it asks
        about one band, not the whole spectrum. See virtual_receiver.py.
        """
        return band in self.active_bands_at(t)

    def __repr__(self):
        return (
            f"RFEnvironment(emitters={len(self.emitters)}, "
            f"time={self.current_time}, spectrum={self.spectrum})"
        )


if __name__ == "__main__":
    from .emitter import EmitterConfig
    from .emitter_behaviors import PeriodicBehavior, AgileBehavior

    spectrum = Spectrum()

    e1 = Emitter(
        config=EmitterConfig(
            emitter_id="E1", emitter_type="radar_A", center_frequency_mhz=2000.0
        ),
        behavior=PeriodicBehavior(on_duration=2, off_duration=2),
    )
    e2 = Emitter(
        config=EmitterConfig(
            emitter_id="E2", emitter_type="radar_B", center_frequency_mhz=5000.0
        ),
        behavior=AgileBehavior(hop_frequencies_mhz=[5000, 5300, 5600], hop_interval=1),
    )

    env = RFEnvironment(spectrum, emitters=[e1, e2])
    env.run(6)

    for t in range(6):
        print(f"t={t}  active_bands={env.active_bands_at(t)}")

    print("\nIs band", spectrum.band_of_frequency(5300), "active at t=1?",
          env.is_band_active(spectrum.band_of_frequency(5300), 1))
