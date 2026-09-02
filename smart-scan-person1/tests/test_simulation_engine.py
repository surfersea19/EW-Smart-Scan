from backend.environment.spectrum import Spectrum
from backend.environment.emitter import Emitter, EmitterConfig
from backend.environment.emitter_behaviors import PeriodicBehavior
from backend.environment.rf_environment import RFEnvironment
from backend.receiver.virtual_receiver import VirtualReceiver, ReceiverConfig
from backend.simulation.simulation_engine import SimulationEngine, Scheduler, NaiveSequentialScheduler


def build_env():
    spectrum = Spectrum()
    e1 = Emitter(
        EmitterConfig(emitter_id="E1", center_frequency_mhz=2000.0),
        PeriodicBehavior(on_duration=3, off_duration=3),
    )
    return RFEnvironment(spectrum, emitters=[e1]), spectrum


class AlternatingScheduler(Scheduler):
    """Deliberately jumps between two far-apart bands every decision,
    to force a tuning penalty on every single step."""
    def __init__(self, band_a=20, band_b=100):
        self.band_a, self.band_b = band_a, band_b
        self.toggle = 0

    def choose_band(self, t, observation_log, spectrum):
        self.toggle = 1 - self.toggle
        return self.band_a if self.toggle else self.band_b


def test_default_config_costs_exactly_one_tick_per_scan():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env)  # default dwell=1, tuning=0
    engine = SimulationEngine(env, receiver, scheduler=NaiveSequentialScheduler())
    engine.run(10)
    assert engine.current_time == 10
    assert len(receiver.observation_log) == 10


def test_dwell_time_produces_multiple_observations_per_decision():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=3, tuning_time=0))
    engine = SimulationEngine(env, receiver, scheduler=NaiveSequentialScheduler())
    engine.run(2)  # 2 scheduler decisions
    assert len(receiver.observation_log) == 6  # 2 decisions * dwell 3
    assert engine.current_time == 6


def test_tuning_time_is_not_charged_on_first_scan():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=1, tuning_time=5))
    engine = SimulationEngine(env, receiver, scheduler=AlternatingScheduler())
    engine.step()  # first ever decision -- nothing to retune away from
    assert engine.current_time == 1  # no tuning penalty paid


def test_tuning_time_charged_when_switching_bands():
    env, spectrum = build_env()
    receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=1, tuning_time=4))
    engine = SimulationEngine(env, receiver, scheduler=AlternatingScheduler())
    engine.step()  # t: 0 -> 1, no penalty (first scan)
    engine.step()  # switches band -> 4 tuning ticks + 1 dwell tick = 5
    assert engine.current_time == 1 + 5


def test_tuning_time_not_charged_when_staying_on_same_band():
    env, spectrum = build_env()

    class SameBandScheduler(Scheduler):
        def choose_band(self, t, observation_log, spectrum):
            return 20  # always the same band -- never switches

    receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=1, tuning_time=10))
    engine = SimulationEngine(env, receiver, scheduler=SameBandScheduler())
    engine.run(5)
    assert engine.current_time == 5  # no tuning penalty ever paid


def test_receiver_is_blind_during_tuning_ticks():
    """
    While tuning, the world still moves (ground truth is generated) but
    no Observation should be produced -- the receiver genuinely can't
    see anything during that window.
    """
    env, spectrum = build_env()
    receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=1, tuning_time=3))
    engine = SimulationEngine(env, receiver, scheduler=AlternatingScheduler())

    engine.step()  # first scan: band_b=100, t=0 -> 1, no tuning
    engine.step()  # switches to band_a=20: 3 blind ticks (t=1,2,3) then 1 observed tick (t=4)

    times_observed = [o.time for o in receiver.observation_log]
    assert times_observed == [0, 4]  # ticks 1, 2, 3 produced no observation
    assert len(env.ground_truth_log) == engine.current_time  # world still advanced every tick
