"""
emitter.py

Defines a generic RF emitter as: static identity/metadata + a pluggable
"behavior" that decides its moment-to-moment state (active/inactive,
current frequency).

Real behaviors (Fixed, Periodic, Bursty, Agile, Scanning) live in
emitter_behaviors.py. This file only includes a minimal placeholder
behavior so Emitter is independently testable before that file exists.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmitterState:
    """
    What an emitter is doing at a single time step.
    This is the row that will eventually feed into ground truth (ch. 10).
    """
    time: int
    emitter_id: str
    active: bool
    frequency_mhz: float = None
    power_db: float = None
    pulse_width_us: float = None
    pri_us: float = None


class EmitterBehavior(ABC):
    """
    Interface every behavior (Fixed, Periodic, Bursty, Agile, Scanning...)
    must implement. Emitter doesn't care which one it's holding.
    """

    @abstractmethod
    def get_state(self, t: int, emitter: "Emitter") -> EmitterState:
        """Return this emitter's state at time step t."""
        raise NotImplementedError


class _AlwaysOnBehavior(EmitterBehavior):
    """
    Placeholder only: emitter transmits continuously at its nominal
    frequency/power. Used so Emitter can be tested before real behaviors
    (emitter_behaviors.py) exist. Do not use this for actual scenarios.
    """

    def get_state(self, t: int, emitter: "Emitter") -> EmitterState:
        return EmitterState(
            time=t,
            emitter_id=emitter.emitter_id,
            active=True,
            frequency_mhz=emitter.center_frequency_mhz,
            power_db=emitter.power_db,
            pulse_width_us=emitter.pulse_width_us,
            pri_us=emitter.pri_us,
        )


@dataclass
class EmitterConfig:
    """Static metadata describing an emitter's identity and nominal parameters."""
    emitter_id: str
    emitter_type: str = "generic"
    center_frequency_mhz: float = 1000.0
    power_db: float = -40.0
    pulse_width_us: float = 1.0
    pri_us: float = 100.0


class Emitter:
    """
    A single RF emitter. Holds static identity/metadata (via EmitterConfig)
    and delegates all on/off and frequency-change logic to a behavior object.
    """

    def __init__(self, config: EmitterConfig, behavior: EmitterBehavior = None):
        self.config = config
        self.emitter_id = config.emitter_id
        self.emitter_type = config.emitter_type
        self.center_frequency_mhz = config.center_frequency_mhz
        self.power_db = config.power_db
        self.pulse_width_us = config.pulse_width_us
        self.pri_us = config.pri_us

        # Default to placeholder behavior if none given (real behaviors come next file)
        self.behavior = behavior or _AlwaysOnBehavior()

    def get_state(self, t: int) -> EmitterState:
        """Ask this emitter's behavior what it's doing at time t."""
        return self.behavior.get_state(t, self)

    def __repr__(self):
        return (
            f"Emitter(id={self.emitter_id}, type={self.emitter_type}, "
            f"freq={self.center_frequency_mhz}MHz, behavior={type(self.behavior).__name__})"
        )


if __name__ == "__main__":
    # Quick manual sanity check
    config = EmitterConfig(
        emitter_id="E1",
        emitter_type="test_radar",
        center_frequency_mhz=6243.7,
        power_db=-40.0,
        pulse_width_us=8.0,
        pri_us=100.0,
    )
    emitter = Emitter(config)
    print(emitter)

    for t in range(3):
        state = emitter.get_state(t)
        print(state)
