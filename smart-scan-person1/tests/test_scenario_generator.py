from backend.environment.scenario_generator import ScenarioGenerator, ScenarioConfig


def test_generates_requested_number_of_emitters():
    env = ScenarioGenerator(ScenarioConfig(seed=1, num_emitters=8)).generate()
    assert len(env.emitters) == 8


def test_same_seed_is_fully_reproducible():
    env1 = ScenarioGenerator(ScenarioConfig(seed=99, num_emitters=5)).generate()
    env2 = ScenarioGenerator(ScenarioConfig(seed=99, num_emitters=5)).generate()

    freqs1 = [e.center_frequency_mhz for e in env1.emitters]
    freqs2 = [e.center_frequency_mhz for e in env2.emitters]
    types1 = [e.emitter_type for e in env1.emitters]
    types2 = [e.emitter_type for e in env2.emitters]

    assert freqs1 == freqs2
    assert types1 == types2


def test_different_seeds_generally_differ():
    env1 = ScenarioGenerator(ScenarioConfig(seed=1, num_emitters=5)).generate()
    env2 = ScenarioGenerator(ScenarioConfig(seed=2, num_emitters=5)).generate()
    freqs1 = [e.center_frequency_mhz for e in env1.emitters]
    freqs2 = [e.center_frequency_mhz for e in env2.emitters]
    assert freqs1 != freqs2


def test_all_emitter_frequencies_within_spectrum_bounds():
    env = ScenarioGenerator(ScenarioConfig(seed=7, num_emitters=10)).generate()
    for e in env.emitters:
        assert env.spectrum.freq_min <= e.center_frequency_mhz <= env.spectrum.freq_max


def test_generated_environment_runs_without_error():
    env = ScenarioGenerator(ScenarioConfig(seed=3, num_emitters=6)).generate()
    env.run(20)
    assert len(env.ground_truth_log) == 20 * 6
