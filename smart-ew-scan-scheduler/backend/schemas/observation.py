"""
observation.py

Previously this file defined placeholder Pydantic Observation/GroundTruth
models for use with MockSimulationEngine. Now that the real Person 1
modules are integrated, the REAL objects are used directly:

    Observation       -> smart-scan-person1/backend/receiver/virtual_receiver.py
    GroundTruthRecord -> smart-scan-person1/backend/environment/rf_environment.py

These are plain dataclasses, not Pydantic models, and are never sent to
the frontend directly -- the orchestrator reads their fields and builds
the frontend-facing WSDelta (schemas/simulation.py) explicitly. There is
intentionally no P3-side duplicate model for them anymore: duplicating
the shape here is exactly what caused the original mock schemas' field
names to drift out of sync with Person 1's real fields.
"""
