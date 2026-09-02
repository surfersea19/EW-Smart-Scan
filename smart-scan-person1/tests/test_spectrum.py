import pytest
from backend.environment.spectrum import Spectrum, SpectrumConfig


def test_default_spectrum_shape():
    s = Spectrum()
    assert s.num_bands == 180
    assert s.freq_min == 0.0
    assert s.freq_max == 18000.0
    assert s.band_width_mhz == pytest.approx(100.0)


def test_band_of_frequency_matches_band_range():
    s = Spectrum()
    freq = 6243.7
    band = s.band_of_frequency(freq)
    low, high = s.band_range(band)
    assert low <= freq < high


def test_band_edges():
    s = Spectrum(SpectrumConfig(freq_min_mhz=0, freq_max_mhz=1000, num_bands=10))
    assert s.band_of_frequency(0.0) == 0
    assert s.band_of_frequency(999.9) == 9
    assert s.band_of_frequency(1000.0) == 9  # exact max edge stays in last band


def test_out_of_range_frequency_raises():
    s = Spectrum(SpectrumConfig(freq_min_mhz=0, freq_max_mhz=1000, num_bands=10))
    with pytest.raises(ValueError):
        s.band_of_frequency(1500.0)
    with pytest.raises(ValueError):
        s.band_of_frequency(-1.0)


def test_invalid_band_index_raises():
    s = Spectrum(SpectrumConfig(freq_min_mhz=0, freq_max_mhz=1000, num_bands=10))
    with pytest.raises(ValueError):
        s.band_range(10)
    with pytest.raises(ValueError):
        s.band_range(-1)


def test_list_bands_length():
    s = Spectrum(SpectrumConfig(num_bands=25))
    assert len(s.list_bands()) == 25
    assert s.list_bands()[0] == 0
    assert s.list_bands()[-1] == 24
