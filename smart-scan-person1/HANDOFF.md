# Person 1 — Final Handoff Document

**Status: FROZEN.** No further code changes will be made to this module.
This document is the authoritative interface reference for Person 2
(ML scheduler) and Person 3 (dashboard/evaluation).

---

## 1. Final Project Folder Structure

```
smart-scan-person1/
├── pyproject.toml
├── README.md
├── backend/
│   ├── __init__.py
│   ├── environment/
│   │   ├── __init__.py
│   │   ├── spectrum.py              # frequency <-> band index conversion
│   │   ├── emitter.py                # Emitter class, EmitterState, EmitterBehavior interface
│   │   ├── emitter_behaviors.py      # Fixed, Periodic, Bursty, Agile, Scanning
│   │   ├── rf_environment.py         # RFEnvironment, GroundTruthRecord
│   │   └── scenario_generator.py     # ScenarioGenerator, ScenarioConfig, ParamRange
│   ├── receiver/
│   │   ├── __init__.py
│   │   ├── virtual_receiver.py       # VirtualReceiver, Observation, ReceiverConfig
│   │   ├── noise_model.py            # NoiseModel, NoiseConfig
│   │   └── detection_model.py        # DetectionModel, DetectionConfig
│   └── simulation/
│       ├── __init__.py
│       └── simulation_engine.py      # SimulationEngine, Scheduler, NaiveSequentialScheduler
└── tests/
    ├── test_spectrum.py
    ├── test_emitter_behaviors.py
    ├── test_rf_environment.py
    ├── test_virtual_receiver.py
    ├── test_detection_model.py
    ├── test_scenario_generator.py
    └── test_simulation_engine.py
```

No `receiver_config.py` or `simulation_state.py` files exist separately
— `ReceiverConfig` lives inside `virtual_receiver.py`; simulation state
is held directly as attributes on `SimulationEngine`. Both were small
enough not to warrant separate files.

---

## 2. Install and Run

From the `smart-scan-person1/` root:

```bash
pip install -e ".[dev]"
```

This installs the `backend` package (editable) plus `pytest` and
`numpy`. Requires Python >= 3.9.

Run any module directly to see its self-test/demo:

```bash
python3 -m backend.environment.spectrum
python3 -m backend.simulation.simulation_engine
```

---

## 3. How to Generate a Scenario

```python
from backend.environment.scenario_generator import ScenarioGenerator, ScenarioConfig

config = ScenarioConfig(seed=42, num_emitters=6)   # any int seed, any emitter count
generator = ScenarioGenerator(config)
env = generator.generate()   # returns a fully-populated RFEnvironment
```

Same `seed` + same `ScenarioConfig` values always reproduces an
identical environment (frequencies, behaviors, all parameters) —
required for comparing schedulers fairly. `ScenarioConfig` also exposes
`spectrum_config`, `behavior_mix`, and per-behavior parameter ranges
(power, pulse width, PRI, hop counts, etc.) — see `scenario_generator.py`
for the full field list.

---

## 4. How to Run the Simulation

```python
from backend.receiver.virtual_receiver import VirtualReceiver, ReceiverConfig
from backend.receiver.noise_model import NoiseModel, NoiseConfig
from backend.receiver.detection_model import DetectionModel, DetectionConfig
from backend.simulation.simulation_engine import SimulationEngine

noise = NoiseModel(NoiseConfig(seed=1))
detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=1, tuning_time=0),
                            detection_model=detector)

engine = SimulationEngine(env, receiver)   # NaiveSequentialScheduler by default
engine.run(num_scans=500)                  # 500 scheduler decisions, not necessarily 500 ticks

print(engine.summary())              # {'total_scans', 'hits', 'misses', 'hit_rate'}
observations = receiver.observation_log    # <- hand this to Person 2's ML pipeline
```

`detection_model` is optional. Omitting it makes the receiver a
deterministic oracle (active band = always detected, inactive = never)
— useful for debugging, not for realistic evaluation.

`num_scans` counts **scheduler decisions**, not raw time ticks — see
section 11 for why these can differ.

---

## 5. Exact `Observation` Schema

Defined in `backend/receiver/virtual_receiver.py`. Available as
`receiver.observation_log: list[Observation]`.

```python
@dataclass
class Observation:
    time: int
    scanned_band: int
    detected: bool
    measured_power_db: float = None    # None if not detected
    pulse_width_us: float = None       # None if not detected
    pri_us: float = None               # None if not detected
```

No `emitter_id`, no `emitter_type`, no information about any band that
wasn't scanned at that time step.

---

## 6. Exact `GroundTruthRecord` Schema

Defined in `backend/environment/rf_environment.py`. Available as
`environment.ground_truth_log: list[GroundTruthRecord]` — **one record
per emitter per time step**, regardless of what the receiver scanned.

```python
@dataclass
class GroundTruthRecord:
    time: int
    emitter_id: str
    emitter_type: str
    band: int              # None if the emitter was inactive
    active: bool
    frequency_mhz: float = None
    power_db: float = None
    pulse_width_us: float = None
    pri_us: float = None
```

Evaluation-only. See section 9.

---

## 7. Exact `Scheduler` Interface

Defined in `backend/simulation/simulation_engine.py`:

```python
class Scheduler:
    def choose_band(self, t: int, observation_log: list, spectrum: Spectrum) -> int:
        raise NotImplementedError
```

- `t`: current simulation time (int)
- `observation_log`: `list[Observation]` — everything scanned so far (section 5 schema)
- `spectrum`: `Spectrum` object — gives `num_bands`, `band_range(i)`, `band_of_frequency(f)`, etc. Structural/config info only, no ground truth.
- Return: `int`, the band index to scan next.

Baseline implementation shipped: `NaiveSequentialScheduler` (bands
`0, 1, 2, ..., num_bands-1`, wrapping) — the open-loop strategy every
smarter scheduler should be benchmarked against.

---

## 8. What Person 2 IS Allowed to Use

- `receiver.observation_log` (`list[Observation]`) — the full history of what was actually scanned and detected.
- `spectrum` object — band count and frequency-range structure (not ground truth; this is receiver-side configuration knowledge, e.g. "there are 180 bands," which any real receiver would know about itself).
- `engine.summary()` and `receiver.observation_log` for computing your own evaluation metrics after a run.
- `ScenarioGenerator` / `ScenarioConfig` to generate training/test scenarios (seeded, reproducible).
- The `Scheduler` interface (section 7) to plug in your own model.

## 9. What Person 2 must NOT Use

- `environment.ground_truth_log` / `GroundTruthRecord` — must never be read inside `choose_band()` or any training-time decision logic. It exists only for **post-hoc evaluation** (comparing what was observed vs. what was really there).
- `environment.active_bands_at(t)` — a full-spectrum ground-truth query; not receiver-realistic.
- Any `emitter_id` / `emitter_type` — never exposed via `Observation` in the first place, so this should be structurally impossible, not just a rule to remember.
- The `RFEnvironment` object itself should never be passed into or referenced by `choose_band()`. If a scheduler implementation holds a reference to `environment`, that's a bug.

---

## 10. Plugging a Custom Scheduler into `SimulationEngine`

```python
from backend.simulation.simulation_engine import Scheduler, SimulationEngine

class MySchedulerModel(Scheduler):
    def choose_band(self, t, observation_log, spectrum):
        # your ML logic here, using ONLY observation_log + spectrum
        return chosen_band_index

engine = SimulationEngine(env, receiver, scheduler=MySchedulerModel())
engine.run(num_scans=1000)
```

No other wiring is required — `SimulationEngine` calls `choose_band()`
once per decision automatically.

---

## 11. Current Configurable Receiver Parameters

`ReceiverConfig` (`backend/receiver/virtual_receiver.py`):

| Parameter | Default | Meaning |
|---|---|---|
| `dwell_time` | `1` | Time ticks spent observing a band per scheduler decision; produces one `Observation` per tick. |
| `tuning_time` | `0` | Time ticks burned (receiver blind, no `Observation` produced) when switching to a *different* band than currently tuned. Not charged on the very first scan of a run. |

`DetectionConfig` (`backend/receiver/detection_model.py`):

| Parameter | Default | Meaning |
|---|---|---|
| `detection_threshold_db` | `-80.0` | Power level a measurement must exceed to count as detected. |

`NoiseConfig` (`backend/receiver/noise_model.py`):

| Parameter | Default | Meaning |
|---|---|---|
| `noise_floor_db` | `-90.0` | Average background noise power. |
| `noise_std_db` | `3.0` | Standard deviation of noise fluctuation, per (band, time) sample. |
| `seed` | `None` | RNG seed for reproducible noise. |

With defaults, `dwell_time=1` and `tuning_time=0` reproduce the
original "1 tick per scan" behavior exactly (regression-tested).

---

## 12. Current Configurable Emitter Parameters

`EmitterConfig` (`backend/environment/emitter.py`) — static identity/metadata:

| Field | Default | Meaning |
|---|---|---|
| `emitter_id` | required | Unique identifier (ground truth only, never in `Observation`) |
| `emitter_type` | `"generic"` | Free-text label |
| `center_frequency_mhz` | `1000.0` | Nominal frequency |
| `power_db` | `-40.0` | Transmit power |
| `pulse_width_us` | `1.0` | Pulse width |
| `pri_us` | `100.0` | Pulse Repetition Interval |

Behavior parameters (`backend/environment/emitter_behaviors.py`), one class per behavior:

| Behavior | Parameters |
|---|---|
| `FixedBehavior` | `on_duration`, `off_duration` (default: always on) |
| `PeriodicBehavior` | `on_duration`, `off_duration` (both required, >0) |
| `BurstyBehavior` | `transmit_probability` (0-1), `seed` |
| `AgileBehavior` | `hop_frequencies_mhz` (list), `hop_interval` |
| `ScanningBehavior` | `freq_start_mhz`, `freq_end_mhz`, `step_mhz`, `step_interval`, `ping_pong` (bool) |

`ScenarioConfig` (`backend/environment/scenario_generator.py`) auto-randomizes
all of the above within configurable `ParamRange(low, high)` bounds —
see that file for the full list of range fields (`power_range_db`,
`pulse_width_range_us`, `pri_range_us`, `periodic_on_range`,
`bursty_prob_range`, `agile_hop_count_range`,
`scanning_span_bands_range`, etc.).

---

## 13. Known Simplifications / Limitations

- **dB-additive noise combination**: `DetectionModel` combines signal + noise power additively in the dB domain rather than converting to linear watts, summing, and converting back. Acceptable for scheduling-focused research; not accurate enough for RF link-budget engineering.
- **Synthetic parameter ranges**: `ScenarioConfig`'s default ranges (power, pulse width, PRI, hop behavior) are hand-picked placeholders, not yet derived from the Turing Synthetic Radar Dataset (TSRD). The generator's interface is stable and ready to accept TSRD-derived ranges without modification — this was the planned next step before freeze.
- **No IQ/waveform-level simulation**: emitters are modeled at the event/PDW level (time, frequency, power, pulse width, PRI, active/inactive) — no I/Q samples, FFTs, spectrograms, modulation, or propagation/antenna physics.
- **Energy-detector model only**: detection uses a simple threshold-vs-noise model, not a matched filter or other production-grade detection theory.
- **Single-receiver assumption**: the simulation models exactly one receiver scanning one band at a time. No multi-receiver / multi-band-simultaneous scanning support.
- **First-scan tuning exemption**: the very first scan in any run never pays a tuning penalty, regardless of `tuning_time`, since there's no prior band to retune away from. This is a modeling choice, not a bug.

---

## 14. All Tests and Their Result

Run via `pytest tests/ -v` from the project root. **Last run: 42/42 PASSED.**

| Test file | Tests | Result |
|---|---|---|
| `test_spectrum.py` | 6 | ✅ all passed |
| `test_emitter_behaviors.py` | 10 | ✅ all passed |
| `test_rf_environment.py` | 4 | ✅ all passed |
| `test_virtual_receiver.py` | 5 | ✅ all passed |
| `test_detection_model.py` | 6 | ✅ all passed |
| `test_scenario_generator.py` | 5 | ✅ all passed |
| `test_simulation_engine.py` | 6 | ✅ all passed |
| **Total** | **42** | **✅ 42 passed, 0 failed** |

Notable structural guarantees enforced by these tests (not just logic checks):

- `test_observation_has_no_emitter_id_field` — confirms `Observation` cannot leak emitter identity.
- `test_receiver_facing_method_has_single_band_signature` — confirms `RFEnvironment.is_band_active()` only accepts one band at a time, preventing a bulk ground-truth query surface.
- `test_default_config_costs_exactly_one_tick_per_scan` — confirms default receiver config reproduces the original baseline exactly.
- `test_tuning_time_is_not_charged_on_first_scan` / `test_tuning_time_charged_when_switching_bands` / `test_receiver_is_blind_during_tuning_ticks` — confirm the timing model (section 11) behaves exactly as documented.
