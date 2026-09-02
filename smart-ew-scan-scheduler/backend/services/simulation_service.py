"""
Simulation service.

This is Person 1's territory: RF environment, emitters, virtual receiver.

`SimulationEngineProtocol` is the CONTRACT. `MockSimulationEngine` is a
working stand-in so the rest of the system (backend orchestration +
frontend) can be built and demoed independently.

TO INTEGRATE PERSON 1's REAL CODE:
  Implement SimulationEngineProtocol in their module, then swap the
  instantiation in `get_simulation_engine()` below. Nothing else in the
  backend should need to change.
"""
from __future__ import annotations
import random
import math
from typing import Protocol, Optional

from schemas.observation import Observation, GroundTruth
from schemas.simulation import ScenarioConfig


class SimulationEngineProtocol(Protocol):
    def reset(self, scenario: ScenarioConfig) -> None: ...
    def step(self) -> None: ...
    def tune(self, band: int) -> None: ...
    def observe(self) -> Observation: ...
    def ground_truth(self) -> GroundTruth: ...


class _Emitter:
    """Internal, ground-truth-only representation of a single emitter."""

    def __init__(self, emitter_id: str, band: int, kind: str, num_bands: int):
        self.id = emitter_id
        self.home_band = band
        self.kind = kind  # "periodic" | "agile" | "continuous"
        self.num_bands = num_bands
        self.period = random.randint(5, 20)
        self.duty = random.uniform(0.2, 0.5)

    def active_band(self, t: int) -> Optional[int]:
        if self.kind == "continuous":
            return self.home_band
        if self.kind == "periodic":
            phase = t % self.period
            return self.home_band if phase < self.period * self.duty else None
        if self.kind == "agile":
            # Hops bands but stays "on" most of the time
            if t % 3 == 0:
                return (self.home_band + random.randint(-5, 5)) % self.num_bands
            return self.home_band
        return None


class MockSimulationEngine:
    """
    Lightweight stand-in for Person 1's real spectrum/emitter/receiver
    simulation. Matches SimulationEngineProtocol.
    """

    def __init__(self):
        self.scenario = ScenarioConfig()
        self.time = 0
        self.emitters: list[_Emitter] = []
        self.current_band: int = 0
        self._noise_std = {"low": 3.0, "medium": 6.0, "high": 10.0}

    def reset(self, scenario: ScenarioConfig) -> None:
        self.scenario = scenario
        self.time = 0
        self.current_band = 0
        kinds = ["periodic", "agile", "continuous"]
        self.emitters = [
            _Emitter(
                emitter_id=f"E{i+1}",
                band=random.randint(0, scenario.num_bands - 1),
                kind=random.choice(kinds),
                num_bands=scenario.num_bands,
            )
            for i in range(scenario.num_emitters)
        ]

    def step(self) -> None:
        self.time += 1

    def tune(self, band: int) -> None:
        self.current_band = band % max(self.scenario.num_bands, 1)

    def _active_bands_now(self) -> list[int]:
        bands = set()
        for e in self.emitters:
            b = e.active_band(self.time)
            if b is not None:
                bands.add(b)
        return sorted(bands)

    def observe(self) -> Observation:
        active = self._active_bands_now()
        detected = self.current_band in active
        noise = self._noise_std.get(self.scenario.noise_level, 6.0)
        power = None
        pulse_width = None
        pri = None
        if detected:
            power = round(-40 + random.gauss(0, noise / 3), 1)
            pulse_width = round(random.uniform(2, 15), 1)
            pri = round(random.uniform(50, 200), 1)
        return Observation(
            time=self.time,
            band=self.current_band,
            detected=detected,
            power=power,
            pulse_width=pulse_width,
            pri=pri,
        )

    def ground_truth(self) -> GroundTruth:
        active = self._active_bands_now()
        active_emitters = [
            e.id for e in self.emitters if e.active_band(self.time) is not None
        ]
        return GroundTruth(
            time=self.time, active_bands=active, active_emitters=active_emitters
        )


_engine_instance: Optional[MockSimulationEngine] = None


def get_simulation_engine() -> SimulationEngineProtocol:
    """
    Single place to swap MockSimulationEngine -> Person 1's real engine.
    """
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = MockSimulationEngine()
    return _engine_instance
