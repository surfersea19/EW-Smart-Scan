
# Smart Scan Strategy for Electronic Warfare

An intelligent spectrum surveillance and scan scheduling system for Electronic Warfare (EW).

The project addresses the challenge of monitoring a wide frequency spectrum when a receiver has limited instantaneous bandwidth. Instead of scanning frequency bands sequentially, the system learns from previous receiver observations and intelligently selects which band should be scanned next.

## Problem Statement

Electronic Warfare systems may need to continuously monitor a wide frequency spectrum to detect hostile communication or radar emitters.

A receiver typically cannot observe the entire spectrum at once because its instantaneous bandwidth is limited. Therefore, the system must decide which frequency band to scan next.

> **How can a receiver intelligently select the next frequency band to maximize detection and interception of active emitters while making efficient use of limited scan opportunities?**

Emitters may exhibit different behaviors such as fixed-frequency, periodic, bursty, frequency-agile, and scanning activity.

## Proposed Solution

This project develops an end-to-end Smart Scan Strategy that combines:

- RF environment and emitter simulation
- Virtual receiver and detection modelling
- Observation history
- Feature engineering
- Machine-learning-based activity prediction
- Intelligent scan scheduling
- Performance evaluation
- Real-time visualization and control

The system learns from observations made by the receiver and predicts which frequency bands are likely to contain future activity. The Smart Scheduler then uses these predictions along with factors such as staleness, uncertainty, recent scanning, and exploration to select the next band.

## System Architecture

``
                RF Environment
             Emitters + Behaviors
                      │
                      ▼
              Virtual Receiver
                      │
                      ▼
                 Observation
                      │
                      ▼
             Observation History
                      │
                      ▼
             Feature Engineering
                      │
                      ▼
               ML Prediction
                      │
                      ▼
              Smart Scheduler
                      │
                      ▼
                Next Band
                      │
                      ▼
              Receiver Scan
                      │
                      └──────────► Repeat
``

## Ground Truth Isolation

Ground truth exists inside the simulation environment and represents the actual state of simulated emitters.

Ground truth is used only for:

* Evaluation
* Performance metrics
* Experiment analysis
* Training-label generation
* Optional clearly labelled simulation-truth visualization

Ground truth is **never provided to the live predictor or scheduler**.

The live decision pipeline is:

```text
RF Environment
      │
      ▼
Receiver Observation
      │
      ▼
Observation History
      │
      ▼
Feature Engineering
      │
      ▼
ML Prediction
      │
      ▼
Smart Scheduler
      │
      ▼
Next Band
```

This ensures that the scheduler makes decisions using only information that would actually be available to the receiver.

## Project Modules

### Person 1 — RF Simulation

`smart-scan-person1/`

Responsible for:

* Spectrum modelling
* Emitter modelling
* Emitter behaviours
* RF environment
* Noise modelling
* Detection modelling
* Virtual receiver
* Simulation engine
* Observations
* Ground truth

### Person 2 — ML Prediction & Scheduling

`ew_scheduler/`

Responsible for:

* Observation history
* Feature engineering
* Dataset generation
* ML model training
* Activity prediction
* Sequential scheduler
* Random scheduler
* Smart ML scheduler
* Evaluation and comparison

### Person 3 — Backend & Dashboard

`smart-ew-scan-scheduler/`

Responsible for:

* FastAPI backend
* API layer
* WebSocket communication
* React dashboard
* Real-time simulation visualization
* Prediction visualization
* Scheduler visualization
* Metrics and comparison dashboard

### Integration Layer

Connects the three modules without unnecessarily rewriting their core implementations.

```text
P1
RF Simulation
    │
    ▼
Observation
    │
    ▼
Integration Layer
    │
    ▼
P2
Prediction + Smart Scheduler
    │
    ▼
Next Band
    │
    ▼
P1 Simulation

P3
FastAPI + WebSocket + React
        │
        ▼
Visualizes and controls the integrated system
```

## Frequency Spectrum

The current RF simulation uses a configurable spectrum with a default configuration of:

* Frequency range: 0–18 GHz
* Number of bands: 180
* Bandwidth per band: 100 MHz

These values are obtained from the simulation configuration rather than being independently hard-coded into the dashboard.

## Emitter Behaviours

The simulation supports multiple emitter activity patterns:

* **Fixed** — emitter remains associated with a fixed frequency band.
* **Periodic** — emitter follows a recurring activity pattern.
* **Bursty** — emitter produces intermittent bursts.
* **Frequency Agile** — emitter changes operating frequency.
* **Scanning** — emitter moves across frequency bands.

## Machine Learning

The prediction system learns from historical receiver observations.

Features include information such as:

* Recent detection count
* Recent miss count
* Hit ratio
* Time since last detection
* Time since last scan
* Number of scans
* Last measured power
* Historical lag features

The predictor estimates the probability that a frequency band will be active in the future.

Supported models include:

* Logistic Regression
* Random Forest
* XGBoost

## Smart Scheduler

The Smart Scheduler combines ML predictions with additional scheduling factors.

```text
Score =
    Prediction Probability
  + Staleness
  + Uncertainty
  - Recent Scan Penalty
  + Exploration
```

This allows the scheduler to balance:

* Exploitation of likely-active bands
* Exploration of uncertain bands
* Revisiting stale bands
* Avoiding excessive repeated scans

## Baseline Schedulers

The Smart Scheduler is evaluated against simpler strategies.

### Sequential Scheduler

```text
0 → 1 → 2 → 3 → ... → N
```

### Random Scheduler

Selects frequency bands randomly.

### Smart ML Scheduler

Uses observation history, ML predictions, and scheduling factors to intelligently select the next band.

## Evaluation Metrics

The system evaluates scan strategies using metrics including:

* Probability of Detection
* Intercept Rate
* Average Intercept Time
* False Alarm / False Positive behaviour
* Burst interception statistics
* Scan efficiency

Performance values are generated from actual simulation experiments rather than hard-coded dashboard values.

## Real-Time Dashboard

The dashboard provides real-time visualization and control of the integrated system.

Major capabilities include:

* Spectrum visualization
* Waterfall/history visualization
* Receiver status
* ML prediction probabilities
* Smart Scheduler decisions
* Scheduler decision factors
* Simulation controls
* Scenario controls
* Performance metrics
* Sequential vs Random vs Smart comparison
* Predicted activity visualization
* Event/activity log

The dashboard distinguishes between:

**Observed Data** — Information actually obtained by the receiver.

**Predicted Activity** — Activity estimated by the ML model.

**Ground Truth** — Actual hidden simulation state used for evaluation.

## Repository Structure

```text
EW-Smart-Scan/
│
├── ew_scheduler/
│   ├── backend/
│   │   ├── prediction/
│   │   ├── scheduler/
│   │   └── evaluation/
│   └── run_pipeline.py
│
├── smart-scan-person1/
│   ├── backend/
│   │   ├── environment/
│   │   ├── receiver/
│   │   └── simulation/
│   └── tests/
│
└── smart-ew-scan-scheduler/
    ├── backend/
    │   ├── api/
    │   ├── services/
    │   ├── schemas/
    │   └── websocket/
    │
    └── frontend/
        └── src/
            ├── components/
            ├── pages/
            ├── services/
            └── store/
```

## Technology Stack

### Backend

* Python
* FastAPI
* Pydantic
* WebSockets
* NumPy
* Pandas
* Scikit-learn
* XGBoost
* Joblib

### Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* Zustand
* Plotly

### Development

* Git
* GitHub

## Running the Project

### P1 — RF Simulation

```bash
cd smart-scan-person1
pytest
```

### P2 — ML Scheduler

```bash
cd ew_scheduler
python run_pipeline.py
```

### P3 — Backend

```bash
cd smart-ew-scan-scheduler/backend
python -m uvicorn main:app --reload
```

### P3 — Frontend

```bash
cd smart-ew-scan-scheduler/frontend
npm install
npm run dev
```

## Design Principles

### Observation-Only Decision Making

The live scheduler uses only information available through receiver observations.

### Ground Truth Isolation

Hidden simulation ground truth is separated from live prediction and scheduling.

### Modular Architecture

RF simulation, ML scheduling, evaluation, and visualization have separate responsibilities.

### Adapter-Based Integration

Interfaces between independently developed modules are connected through integration/adapter components rather than unnecessarily rewriting working modules.

### Real Evaluation

Performance metrics are generated from actual experiments.

### Explainable Scheduling

Where possible, the system exposes the factors that contributed to the Smart Scheduler's band-selection decision.

## Development Status

| Component                | Status         |
| ------------------------ | -------------- |
| RF Environment           | ✅ Implemented  |
| Emitter Behaviours       | ✅ Implemented  |
| Virtual Receiver         | ✅ Implemented  |
| Simulation Engine        | ✅ Implemented  |
| Observation History      | ✅ Implemented  |
| Feature Engineering      | ✅ Implemented  |
| ML Prediction            | ✅ Implemented  |
| Smart Scheduler          | ✅ Implemented  |
| Baseline Schedulers      | ✅ Implemented  |
| Evaluation Framework     | ✅ Implemented  |
| FastAPI Backend          | ✅ Implemented  |
| WebSocket Layer          | ✅ Implemented  |
| React Dashboard          | ✅ Implemented  |
| P1 + P2 + P3 Integration | 🚧 In Progress |

## Future Scope

* Advanced temporal prediction
* Emitter identification
* Persistent emitter tracking
* Frequency-agility prediction
* Multi-receiver coordination
* Adaptive scan parameters
* Reinforcement-learning-based scheduling
* Larger spectrum scenarios
* Hardware/SDR integration
* Real-world RF data integration

## Objective

The ultimate objective is to demonstrate an intelligent Electronic Warfare spectrum surveillance system that can make more effective scan decisions than fixed sequential or random scanning strategies while operating under realistic receiver information constraints.

---

**Smart Scan Strategy for Electronic Warfare**
*RF Simulation + Machine Learning + Intelligent Scheduling + Real-Time Visualization*

```
```

Branch protection test.
