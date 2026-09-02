# Smart Scan Strategy — Person 1's Module (RF Environment + Virtual Receiver)

This package simulates an RF environment with multiple emitters and a
band-limited virtual receiver that scans one band at a time. It is
the input layer for the ML scheduler (Person 2) and the dashboard (Person 3).

## Install

From this directory:

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from backend.environment.scenario_generator import ScenarioGenerator, ScenarioConfig
from backend.receiver.virtual_receiver import VirtualReceiver
from backend.receiver.noise_model import NoiseModel, NoiseConfig
from backend.receiver.detection_model import DetectionModel, DetectionConfig
from backend.simulation.simulation_engine import SimulationEngine

# 1. Generate a random (but reproducible) scenario
env = ScenarioGenerator(ScenarioConfig(seed=42, num_emitters=6)).generate()

# 2. Build a receiver with realistic noise/detection
noise = NoiseModel(NoiseConfig(seed=1))
detector = DetectionModel(noise, DetectionConfig(detection_threshold_db=-80.0))
receiver = VirtualReceiver(env, detection_model=detector)

# 3. Run the simulation (default: naive sequential scheduler)
engine = SimulationEngine(env, receiver)
engine.run(num_scans=500)

print(engine.summary())
observations = receiver.observation_log  # <-- this is what Person 2 consumes
```

## The data contract (read this before building the scheduler/ML)

### `Observation` — what the receiver actually saw (use THIS for ML)

```python
Observation(
    time: int,
    scanned_band: int,
    detected: bool,
    measured_power_db: float | None,   # None if not detected
    pulse_width_us: float | None,
    pri_us: float | None,
)
```

Available as `receiver.observation_log` — a list of these, one per scan.

**Important — this is deliberately incomplete information**: there is no
`emitter_id`, and there is no information about any band that wasn't
scanned at that time step. This mirrors what a real receiver actually
knows. If your scheduler/ML code needs more than this, that's a sign
it's accidentally depending on ground truth — see below.

### `GroundTruthRecord` — the real state of the world (evaluation ONLY)

```python
GroundTruthRecord(
    time: int,
    emitter_id: str,
    emitter_type: str,
    band: int | None,
    active: bool,
    frequency_mhz: float | None,
    power_db: float | None,
    pulse_width_us: float | None,
    pri_us: float | None,
)
```

Available as `environment.ground_truth_log`.

**Do not train on this or feed it into the scheduler's decision
function.** It exists only to compute evaluation metrics after the
fact (hit rate, intercept time, Pd/Pfa, etc.) — comparing what the
receiver *observed* against what was *actually* happening. If a
scheduler function ever receives an `RFEnvironment` object directly,
that's a bug: it should only ever see `receiver.observation_log`.

### Plugging in a scheduler

Implement the `Scheduler` interface from `simulation_engine.py`:

```python
from backend.simulation.simulation_engine import Scheduler

class MySchedulerModel(Scheduler):
    def choose_band(self, t, observation_log, spectrum):
        # observation_log: list[Observation] — everything scanned so far
        # spectrum: Spectrum — band count / frequency ranges only, not
        #           ground truth
        # return: int, the band index to scan next
        ...

engine = SimulationEngine(env, receiver, scheduler=MySchedulerModel())
```

The included `NaiveSequentialScheduler` (bands 0, 1, 2, ... wrapping) is
the open-loop baseline every smarter scheduler should be benchmarked
against — it currently gets ~1% hit rate over a full 180-band sweep.

## Module map

| Module | Responsibility |
|---|---|
| `environment/spectrum.py` | Frequency <-> band index conversion |
| `environment/emitter.py` | Emitter identity/metadata + behavior delegation |
| `environment/emitter_behaviors.py` | Fixed/Periodic/Bursty/Agile/Scanning on-off & frequency rules |
| `environment/rf_environment.py` | Owns all emitters, advances time, produces ground truth |
| `environment/scenario_generator.py` | Randomized (seeded) scenario construction |
| `receiver/noise_model.py` | Background noise floor + fluctuation |
| `receiver/detection_model.py` | Probabilistic Pd/Pfa detection (energy detector) |
| `receiver/virtual_receiver.py` | Single-band-at-a-time scanning, produces `Observation`s |
| `simulation/simulation_engine.py` | Time loop wiring environment + scheduler + receiver |

## Known simplifications (documented on purpose)

- Detection model combines signal + noise power additively in dB rather
  than converting to linear watts first — a physics simplification,
  acceptable for scheduling research, not for RF link-budget accuracy.
- Scenario parameter ranges (`ScenarioConfig`) are currently synthetic
  placeholders, not yet derived from the TSRD dataset. Swap in
  TSRD-derived `ParamRange`s in `scenario_generator.py` without changing
  its interface when that's ready.

## Timing model: tuning_time and dwell_time

`SimulationEngine.step()` now charges realistic time costs per
scheduler decision (ch. 15/16):

- If the scheduler picks a **different** band than the receiver is
  currently on, `receiver.config.tuning_time` ticks are burned first.
  The world keeps advancing during this window, but the receiver is
  blind — **no `Observation` is produced** for tuning ticks. The very
  first scan of a run pays no tuning penalty (nothing to retune from).
- The receiver then observes the chosen band for
  `receiver.config.dwell_time` ticks, producing one `Observation` per
  tick.

Because of this, `SimulationEngine.run(num_scans)` takes a **number of
scheduler decisions**, not raw time ticks — the actual number of ticks
elapsed (`engine.current_time`) can be larger once `tuning_time` or
`dwell_time` are set above their defaults (1 and 0 respectively, which
reproduce the original "1 tick per scan" behavior exactly).

```python
receiver = VirtualReceiver(env, config=ReceiverConfig(dwell_time=2, tuning_time=3))
engine = SimulationEngine(env, receiver, scheduler=my_scheduler)
engine.run(50)  # 50 scheduler decisions, likely > 50 raw ticks elapsed
print(engine.current_time)  # total ticks actually spent
```

## Running tests

```bash
pytest tests/ -v
```
