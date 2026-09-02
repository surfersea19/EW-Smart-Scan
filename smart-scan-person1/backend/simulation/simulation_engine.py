"""
simulation_engine.py

The orchestrator. Owns the time loop. Each scheduler "decision" now
costs a realistic number of raw time ticks (ch. 15/16), not always 1:

    for each scheduler decision:
        1. scheduler picks a band to scan next (sees observations only)
        2. IF switching to a different band: burn tuning_time ticks,
           world keeps moving, receiver observes nothing
        3. observe the chosen band for dwell_time ticks, each producing
           an Observation
        4. repeat

This is the single entry point that ties environment/ + receiver/
together, and is where Person 2's real scheduler gets plugged in later
-- it just needs to match the Scheduler interface below.

For now, we ship a NaiveSequentialScheduler as a placeholder/baseline,
matching ch. 18's note that Person 1 can test with a simple sequential
scanner before the smart scheduler exists.
"""

from ..environment.spectrum import Spectrum
from ..environment.rf_environment import RFEnvironment
from ..receiver.virtual_receiver import VirtualReceiver, Observation


class Scheduler:
    """
    Interface every scheduler must implement (naive baseline or Person 2's
    ML-driven one later). choose_band is given the receiver's observation
    log so far -- NEVER the environment -- to decide where to look next.
    """

    def choose_band(self, t: int, observation_log: list, spectrum: Spectrum) -> int:
        raise NotImplementedError


class NaiveSequentialScheduler(Scheduler):
    """
    Baseline/placeholder scheduler: walks bands 0, 1, 2, ..., num_bands-1,
    then wraps around. This is the "open loop" strategy described in the
    original problem statement -- it exists so Person 1's pipeline is
    testable end-to-end before Person 2's smart scheduler exists, and
    later serves as the baseline the smart scheduler must beat.
    """

    def choose_band(self, t: int, observation_log: list, spectrum: Spectrum) -> int:
        return t % spectrum.num_bands


class SimulationEngine:
    """
    Runs the full time loop, wiring together the environment, a scheduler,
    and the receiver. Produces the receiver's observation log -- the clean
    dataset (ch. 19) that gets handed to Person 2's ML pipeline.
    """

    def __init__(self, environment: RFEnvironment, receiver: VirtualReceiver,
                 scheduler: Scheduler = None):
        self.environment = environment
        self.receiver = receiver
        self.scheduler = scheduler or NaiveSequentialScheduler()
        self.current_time = 0

    def step(self) -> list:
        """
        Perform ONE scheduler decision: choose a band, pay any tuning-time
        penalty if switching to a different band (receiver is blind during
        this -- the world keeps moving, but nothing is observed), then
        observe the chosen band for dwell_time ticks.

        Returns the list of Observations produced this decision (normally
        length == receiver.config.dwell_time).
        """
        # Scheduler decides where to look, using ONLY past observations
        # -- never touches self.environment directly.
        band = self.scheduler.choose_band(
            self.current_time, self.receiver.observation_log, self.environment.spectrum
        )

        # Tuning penalty: only paid when switching AWAY from the band the
        # receiver is currently sitting on. The very first scan pays no
        # penalty -- there's nothing to retune away from yet.
        switching_bands = (
            self.receiver.current_band is not None and band != self.receiver.current_band
        )
        tuning_ticks = self.receiver.config.tuning_time if switching_bands else 0

        for _ in range(tuning_ticks):
            # World keeps moving during tuning, but the receiver can't
            # observe anything -- so no receiver.scan() call here at all.
            self.environment.step()
            self.current_time += 1

        observations = []
        for _ in range(self.receiver.config.dwell_time):
            self.environment.step()
            obs = self.receiver.scan(band, self.current_time)
            observations.append(obs)
            self.current_time += 1

        return observations

    def run(self, num_scans: int) -> list:
        """
        Run num_scans scheduler decisions (NOT raw time ticks -- each
        decision may burn multiple ticks once tuning_time/dwell_time > 1).
        Returns the full observation log.
        """
        for _ in range(num_scans):
            self.step()
        return self.receiver.observation_log

    def summary(self) -> dict:
        """
        Quick evaluation stats (foundation for the figures of merit in the
        problem statement -- intercept rate, etc. Full metrics module comes
        later once Person 2/3 define exactly what they need).
        """
        obs = self.receiver.observation_log
        hits = sum(1 for o in obs if o.detected)
        return {
            "total_scans": len(obs),
            "hits": hits,
            "misses": len(obs) - hits,
            "hit_rate": hits / len(obs) if obs else 0.0,
        }


if __name__ == "__main__":
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

    environment = RFEnvironment(spectrum, emitters=[e1, e2])
    receiver = VirtualReceiver(environment)
    engine = SimulationEngine(environment, receiver)  # naive scheduler by default

    engine.run(180)  # one full sweep of all 180 bands

    print(engine.summary())
    print("\nFirst 5 hits:")
    hits = [o for o in receiver.observation_log if o.detected]
    for o in hits[:5]:
        print(o)
