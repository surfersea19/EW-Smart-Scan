"""
noise_model.py

Models background RF noise: a fluctuating power level present in every
band at every time step, whether or not an emitter is transmitting.
This is what makes detection probabilistic instead of a perfect oracle.

Kept deliberately simple: Gaussian fluctuation around a fixed noise
floor. Real receivers have frequency- and temperature-dependent noise;
that's a refinement for later, not needed to demonstrate Pd/Pfa tradeoffs.
"""

import random
from dataclasses import dataclass


@dataclass
class NoiseConfig:
    noise_floor_db: float = -90.0   # average background power level
    noise_std_db: float = 3.0       # how much it fluctuates, step to step
    seed: int = None                # for reproducible scenarios


class NoiseModel:
    """
    Produces a noise power sample for any (band, time) pair. Samples are
    cached so repeated queries for the same (band, t) return the same
    value within a run -- noise at a specific instant shouldn't change
    just because something asked twice.
    """

    def __init__(self, config: NoiseConfig = None):
        self.config = config or NoiseConfig()
        self._rng = random.Random(self.config.seed)
        self._cache = {}

    def get_noise_sample_db(self, band: int, t: int) -> float:
        key = (band, t)
        if key not in self._cache:
            sample = self._rng.gauss(self.config.noise_floor_db, self.config.noise_std_db)
            self._cache[key] = sample
        return self._cache[key]

    def __repr__(self):
        return f"NoiseModel(floor={self.config.noise_floor_db}dB, std={self.config.noise_std_db}dB)"


if __name__ == "__main__":
    noise = NoiseModel(NoiseConfig(seed=42))
    print(noise)
    samples = [noise.get_noise_sample_db(band=5, t=t) for t in range(10)]
    print("Noise samples at band 5, t=0..9:", [round(s, 2) for s in samples])

    # Same (band, t) queried twice should return the identical cached value
    print("Repeat query at t=0:", noise.get_noise_sample_db(band=5, t=0))
