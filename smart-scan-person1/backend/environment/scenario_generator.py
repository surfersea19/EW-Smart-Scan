"""
scenario_generator.py

Automatically builds varied RFEnvironment test scenarios instead of
hand-writing each one (ch. 21). Uses synthetic/randomized parameter
ranges for now -- these ranges are placeholders to be replaced with
TSRD-derived distributions later (ch. 22-23), but the generator's
*shape* (config in, RFEnvironment out) won't need to change when that
happens -- only where the parameter ranges come from.

Everything is seeded, so a given ScenarioConfig always produces the
exact same environment -- essential for comparing scheduler strategies
fairly (they need to be tested against identical scenarios).
"""

import random
from dataclasses import dataclass, field

from .spectrum import Spectrum, SpectrumConfig
from .emitter import Emitter, EmitterConfig
from .emitter_behaviors import (
    FixedBehavior, PeriodicBehavior, BurstyBehavior, AgileBehavior, ScanningBehavior,
)
from .rf_environment import RFEnvironment


@dataclass
class ParamRange:
    """A simple (min, max) range to sample a float from. Named for clarity
    at call sites rather than passing raw tuples everywhere."""
    low: float
    high: float

    def sample(self, rng: random.Random) -> float:
        return rng.uniform(self.low, self.high)


@dataclass
class ScenarioConfig:
    """
    Describes HOW to generate a scenario, not the scenario itself.
    Change these ranges to make scenarios harsher/easier/more varied.
    """
    seed: int = 0
    spectrum_config: SpectrumConfig = field(default_factory=SpectrumConfig)

    num_emitters: int = 5
    behavior_mix: tuple = ("fixed", "periodic", "bursty", "agile", "scanning")

    power_range_db: ParamRange = field(default_factory=lambda: ParamRange(-90, -35))
    pulse_width_range_us: ParamRange = field(default_factory=lambda: ParamRange(0.5, 20.0))
    pri_range_us: ParamRange = field(default_factory=lambda: ParamRange(50, 500))

    # Behavior-specific ranges
    periodic_on_range: ParamRange = field(default_factory=lambda: ParamRange(1, 5))
    periodic_off_range: ParamRange = field(default_factory=lambda: ParamRange(1, 5))
    bursty_prob_range: ParamRange = field(default_factory=lambda: ParamRange(0.1, 0.6))
    agile_hop_count_range: ParamRange = field(default_factory=lambda: ParamRange(2, 6))
    agile_hop_interval_range: ParamRange = field(default_factory=lambda: ParamRange(1, 4))
    scanning_span_bands_range: ParamRange = field(default_factory=lambda: ParamRange(5, 30))
    scanning_step_interval_range: ParamRange = field(default_factory=lambda: ParamRange(1, 3))


class ScenarioGenerator:
    """
    Builds a fully-configured RFEnvironment from a ScenarioConfig.
    Deterministic given the same seed -- rerunning produces an identical
    environment, which is what lets you compare two scheduler strategies
    on exactly the same "world."
    """

    def __init__(self, config: ScenarioConfig = None):
        self.config = config or ScenarioConfig()
        self._rng = random.Random(self.config.seed)

    def generate(self) -> RFEnvironment:
        spectrum = Spectrum(self.config.spectrum_config)
        emitters = [self._build_emitter(i, spectrum) for i in range(self.config.num_emitters)]
        return RFEnvironment(spectrum, emitters=emitters)

    def _build_emitter(self, index: int, spectrum: Spectrum) -> Emitter:
        cfg = self.config
        rng = self._rng

        emitter_id = f"E{index + 1}"
        behavior_type = rng.choice(cfg.behavior_mix)

        power_db = cfg.power_range_db.sample(rng)
        pulse_width_us = cfg.pulse_width_range_us.sample(rng)
        pri_us = cfg.pri_range_us.sample(rng)

        # Pick a nominal frequency inside the spectrum for all behaviors
        # except "scanning", which needs a start/end range instead.
        nominal_freq = rng.uniform(spectrum.freq_min, spectrum.freq_max)

        emitter_config = EmitterConfig(
            emitter_id=emitter_id,
            emitter_type=behavior_type,
            center_frequency_mhz=nominal_freq,
            power_db=power_db,
            pulse_width_us=pulse_width_us,
            pri_us=pri_us,
        )

        behavior = self._build_behavior(behavior_type, nominal_freq, spectrum, rng)
        return Emitter(emitter_config, behavior)

    def _build_behavior(self, behavior_type: str, nominal_freq: float,
                         spectrum: Spectrum, rng: random.Random):
        cfg = self.config

        if behavior_type == "fixed":
            return FixedBehavior(on_duration=1, off_duration=0)

        if behavior_type == "periodic":
            on = max(1, round(cfg.periodic_on_range.sample(rng)))
            off = max(1, round(cfg.periodic_off_range.sample(rng)))
            return PeriodicBehavior(on_duration=on, off_duration=off)

        if behavior_type == "bursty":
            p = cfg.bursty_prob_range.sample(rng)
            return BurstyBehavior(transmit_probability=p, seed=rng.randint(0, 1_000_000))

        if behavior_type == "agile":
            hop_count = max(2, round(cfg.agile_hop_count_range.sample(rng)))
            interval = max(1, round(cfg.agile_hop_interval_range.sample(rng)))
            # Build a hop list of random frequencies within the spectrum,
            # centered loosely around the nominal frequency.
            hop_freqs = [
                min(max(nominal_freq + rng.uniform(-500, 500), spectrum.freq_min), spectrum.freq_max)
                for _ in range(hop_count)
            ]
            return AgileBehavior(hop_frequencies_mhz=hop_freqs, hop_interval=interval)

        if behavior_type == "scanning":
            span_bands = max(2, round(cfg.scanning_span_bands_range.sample(rng)))
            span_mhz = span_bands * spectrum.band_width_mhz
            start = max(spectrum.freq_min, nominal_freq - span_mhz / 2)
            end = min(spectrum.freq_max, start + span_mhz)
            step_interval = max(1, round(cfg.scanning_step_interval_range.sample(rng)))
            return ScanningBehavior(
                freq_start_mhz=start, freq_end_mhz=end,
                step_mhz=spectrum.band_width_mhz, step_interval=step_interval,
            )

        raise ValueError(f"Unknown behavior_type: {behavior_type}")


if __name__ == "__main__":
    config = ScenarioConfig(seed=42, num_emitters=6)
    generator = ScenarioGenerator(config)
    env = generator.generate()

    print(f"Generated {len(env.emitters)} emitters:")
    for e in env.emitters:
        print(f"  {e}")

    env.run(20)
    print("\nActive bands over first 20 steps:")
    for t in range(20):
        bands = env.active_bands_at(t)
        if bands:
            print(f"  t={t}: {bands}")

    # Determinism check: same seed -> identical scenario
    env2 = ScenarioGenerator(ScenarioConfig(seed=42, num_emitters=6)).generate()
    same = all(
        e1.center_frequency_mhz == e2.center_frequency_mhz
        for e1, e2 in zip(env.emitters, env2.emitters)
    )
    print(f"\nSame seed reproduces identical scenario: {same}")
