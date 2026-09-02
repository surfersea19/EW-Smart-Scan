# Smart EW Scan Scheduler — Person 3 (Backend Integration + Dashboard)

This is a working end-to-end prototype: FastAPI backend + React/TS/Vite/Tailwind
frontend, live over WebSocket. Person 1's simulation and Person 2's ML/scheduler
are currently **mocked** behind typed interfaces (`Protocol` classes) so the
whole pipeline runs and is demoable *today*, independent of their progress.

## Running it

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Visit http://localhost:8000 — should return `{"status": "ok", ...}`.
Interactive API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit http://localhost:5173. Click START to see live ticks flowing in.

Run both at once, backend first.

## What's real vs. mocked right now

| Piece | Status |
|---|---|
| FastAPI app, routes, WebSocket loop | Real, working |
| Pydantic schemas (the data contract) | Real — this is the spec to hand Persons 1 & 2 |
| React dashboard, all panels, WebSocket wiring | Real, working |
| `MockSimulationEngine` (backend/services/simulation_service.py) | Placeholder for Person 1 |
| `MockPredictor` (backend/services/prediction_service.py) | Placeholder for Person 2 |
| `MockSmartScheduler` (backend/services/scheduler_service.py) | Placeholder for Person 2 |
| Baseline schedulers (sequential/random) | Real — these stay, they're Person 3's |
| Comparison endpoint (`/comparison`) | Real — always runs actual ticks, never hardcodes numbers |

## Integrating Person 1's real simulation

1. They implement a class matching `SimulationEngineProtocol` in
   `backend/services/simulation_service.py`:
   `reset(scenario)`, `step()`, `tune(band)`, `observe() -> Observation`,
   `ground_truth() -> GroundTruth`.
2. Swap the instantiation in `get_simulation_engine()` to their class.
3. Nothing in `orchestrator.py`, the API routes, or the frontend needs to change,
   as long as `Observation` and `GroundTruth` fields match `schemas/observation.py`.

## Integrating Person 2's real ML/scheduler

1. Predictor: implement `PredictorProtocol.predict(obs_history, num_bands, top_k)`
   returning `list[BandPrediction]`, matching `schemas/prediction.py`. Swap in
   `get_predictor()`.
2. Scheduler: implement `SchedulerProtocol.decide(predictions, current_band,
   num_bands, recently_scanned)` returning `SchedulerDecision`, matching
   `schemas/scheduler.py`. Register it under the `"smart_ml"` key in
   `get_scheduler()` in `scheduler_service.py`.
3. **Constraint to enforce on their side too:** the predictor must only ever
   receive `obs_history` (receiver observations), never ground truth.

## Ground truth / observation separation

Ground truth is fetched *only* inside `orchestrator.py`, *only* for metrics
computation, and is never attached to `SimulationState` or `WSDelta` (the
models that reach the frontend). If you ever need a debug "simulation truth"
view, add a **separate** WebSocket message type or REST endpoint for it —
don't fold it into the existing receiver-facing payload.

## Next steps (per the original dev-order plan)

- Stage 13/18/19 are done (tracks panel, controls, comparison) at MVP level.
- Not yet built: dedicated Results page (stage 21), EventLog component,
  scenario presets, automated tests (stage 30). Ask me to build any of these
  next — each is a self-contained addition to this structure.
