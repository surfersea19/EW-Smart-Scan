"""
simulation_service.py -- REAL Person 1 integration.

Replaces the earlier MockSimulationEngine. Wraps P1's real
ScenarioGenerator -> RFEnvironment -> VirtualReceiver -> SimulationEngine.

P1's SimulationEngine owns the only clock (see HANDOFF.md #4/#7 and
simulation_engine.py -- `SimulationEngine.step()` internally drives
`environment.step()` and `receiver.scan()` itself). This wrapper does
not add a second clock -- `step_once()` calls P1's real `engine.step()`
exactly once per call, nothing more.

Band count is never hardcoded here: after building the real environment,
`scenario.num_bands` is overwritten with `environment.spectrum.num_bands`
-- the spectrum is the single source of truth (see integration analysis,
"BAND CONFIGURATION").
"""
from integration.repo_paths import register_p1_p2_on_path

register_p1_p2_on_path()

# Real Person 1 imports (path registered above; P1 uses relative imports
# internally, so it must be imported as the `backend` package rooted at
# smart-scan-person1/, exactly as register_p1_p2_on_path() sets up).
from backend.environment.scenario_generator import (  # noqa: E402
    ScenarioGenerator,
    ScenarioConfig as P1ScenarioConfig,
)
from backend.environment.spectrum import SpectrumConfig  # noqa: E402
from backend.receiver.virtual_receiver import VirtualReceiver  # noqa: E402
from backend.receiver.noise_model import NoiseModel, NoiseConfig  # noqa: E402
from backend.receiver.detection_model import DetectionModel, DetectionConfig  # noqa: E402
from backend.simulation.simulation_engine import SimulationEngine  # noqa: E402

from schemas.simulation import ScenarioConfig as P3ScenarioConfig

# P3-side UI convenience mapping only -- P1's NoiseConfig takes a raw std
# dev in dB; the frontend exposes a simpler low/medium/high control. This
# mapping lives entirely in P3 and never touches P1's code or defaults.
_NOISE_STD_BY_LEVEL = {"low": 1.5, "medium": 3.0, "high": 6.0}


class RealSimulationEngine:
    """P3-side wrapper around Person 1's real simulation stack."""

    def __init__(self):
        self.environment = None
        self.receiver = None
        self.engine = None
        self.scenario: P3ScenarioConfig = P3ScenarioConfig()

    def reset(self, scenario: P3ScenarioConfig, p1_scheduler) -> None:
        """
        p1_scheduler: any object implementing Person 1's Scheduler ABC
        (a `choose_band(t, observation_log, spectrum) -> int` method) --
        in practice always a SchedulerAdapter wrapping a Person 2
        scheduler (see integration/scheduler_adapter.py).
        """
        p1_config = P1ScenarioConfig(
            seed=scenario.scenario_seed,
            spectrum_config=SpectrumConfig(num_bands=scenario.num_bands),
            num_emitters=scenario.num_emitters,
        )
        generator = ScenarioGenerator(p1_config)
        self.environment = generator.generate()

        noise_std = _NOISE_STD_BY_LEVEL.get(scenario.noise_level, 3.0)
        noise = NoiseModel(NoiseConfig(noise_std_db=noise_std, seed=scenario.scenario_seed))
        detector = DetectionModel(noise, DetectionConfig())
        self.receiver = VirtualReceiver(self.environment, detection_model=detector)
        self.engine = SimulationEngine(self.environment, self.receiver, scheduler=p1_scheduler)

        # Read the real band count back from the spectrum -- never trust
        # a separately tracked P3 number as the source of truth.
        scenario.num_bands = self.environment.spectrum.num_bands
        self.scenario = scenario

    def step_once(self):
        """One scheduler decision. May internally cost more than one raw
        simulation tick if tuning_time/dwell_time > 1 (P1's real timing
        model, untouched). Returns the list of new Observations produced
        (normally length 1 with default receiver config)."""
        return self.engine.step()

    @property
    def current_time(self) -> int:
        """
        P1's real, single authoritative clock (SimulationEngine.current_time
        -- raw ticks, incremented once per environment.step() call inside
        P1's own step(), whether during a tuning-blind tick or a dwell/
        observation tick). This is the ONLY time value P3 is allowed to
        consult to decide whether ScenarioConfig.duration has been
        reached (see orchestrator.py) -- P3 introduces no clock of its
        own anywhere.
        """
        return self.engine.current_time


_engine_instance = None


def get_simulation_engine() -> RealSimulationEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RealSimulationEngine()
    return _engine_instance
