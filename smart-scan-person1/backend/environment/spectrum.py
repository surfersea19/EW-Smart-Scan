"""
spectrum.py

Defines how the total RF spectrum is divided into discrete bands.

Every other module (emitter, receiver, environment) should go through
this class to convert between "real" frequency (MHz) and "band index"
(what the receiver actually tunes to). Nobody else should do this math
themselves — one source of truth avoids off-by-one bugs across files.

Default range (0-18000 MHz) matches the Turing Synthetic Radar Dataset's
Stare Mode coverage, so emitter frequencies sampled from TSRD will land
inside a spectrum that can actually contain them.
"""

from dataclasses import dataclass
import numpy as np


@dataclass
class SpectrumConfig:
    """Configuration for the spectrum. Change these to reshape the whole simulation."""
    freq_min_mhz: float = 0.0
    freq_max_mhz: float = 18000.0
    num_bands: int = 180  # 180 bands x 100 MHz each = 18000 MHz total


class Spectrum:
    """
    Represents the total frequency range, divided into equal-width bands.

    Band indices are 0-based: band 0, band 1, ..., band (num_bands - 1).
    """

    def __init__(self, config: SpectrumConfig = None):
        self.config = config or SpectrumConfig()

        if self.config.freq_max_mhz <= self.config.freq_min_mhz:
            raise ValueError("freq_max_mhz must be greater than freq_min_mhz")
        if self.config.num_bands <= 0:
            raise ValueError("num_bands must be positive")

        self.freq_min = self.config.freq_min_mhz
        self.freq_max = self.config.freq_max_mhz
        self.num_bands = self.config.num_bands

        # Edges of every band, e.g. [0, 100, 200, ..., 18000] for 180 bands
        self.band_edges = np.linspace(self.freq_min, self.freq_max, self.num_bands + 1)
        self.band_width_mhz = self.band_edges[1] - self.band_edges[0]

    def band_of_frequency(self, freq_mhz: float) -> int:
        """
        Given a real frequency, return which band index it falls into.
        Frequencies outside the spectrum range raise an error rather than
        silently clipping — that usually means a config mismatch upstream.
        """
        if freq_mhz < self.freq_min or freq_mhz > self.freq_max:
            raise ValueError(
                f"Frequency {freq_mhz} MHz is outside spectrum range "
                f"[{self.freq_min}, {self.freq_max}] MHz"
            )
        # searchsorted finds the correct bucket; clip handles the exact-max edge case
        band = int(np.searchsorted(self.band_edges, freq_mhz, side="right") - 1)
        return min(band, self.num_bands - 1)

    def band_range(self, band_index: int) -> tuple:
        """Given a band index, return its (low_mhz, high_mhz) frequency range."""
        self._validate_band_index(band_index)
        return (float(self.band_edges[band_index]), float(self.band_edges[band_index + 1]))

    def band_center(self, band_index: int) -> float:
        """Center frequency of a band — useful as a single representative value."""
        low, high = self.band_range(band_index)
        return (low + high) / 2.0

    def list_bands(self) -> list:
        """Return all band indices, e.g. [0, 1, 2, ..., 179]."""
        return list(range(self.num_bands))

    def _validate_band_index(self, band_index: int):
        if not (0 <= band_index < self.num_bands):
            raise ValueError(
                f"band_index {band_index} out of range [0, {self.num_bands - 1}]"
            )

    def __repr__(self):
        return (
            f"Spectrum({self.freq_min}-{self.freq_max} MHz, "
            f"{self.num_bands} bands, {self.band_width_mhz:.2f} MHz/band)"
        )


if __name__ == "__main__":
    # Quick manual sanity check — run this file directly to see it work.
    spectrum = Spectrum()
    print(spectrum)

    test_freq = 6243.7
    band = spectrum.band_of_frequency(test_freq)
    print(f"Frequency {test_freq} MHz -> band {band}, range {spectrum.band_range(band)}")

    print(f"Band 0 range: {spectrum.band_range(0)}")
    print(f"Band 179 range: {spectrum.band_range(179)}")
    print(f"Total bands: {len(spectrum.list_bands())}")
