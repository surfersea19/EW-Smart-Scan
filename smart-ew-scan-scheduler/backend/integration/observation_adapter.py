"""
observation_adapter.py

Person 1's real Observation dataclass (backend/receiver/virtual_receiver.py):
    time, scanned_band, detected, measured_power_db, pulse_width_us, pri_us

Person 2's BandHistoryManager.ingest() expects a dict:
    {time, band, detected, power (optional), pulse_width (optional), pri (optional)}

This is the ONLY place that translation happens. Pure functions, no
state, no ground truth involved -- this only ever sees what the
receiver actually observed.
"""
from typing import Any


def p1_observation_to_p2_dict(obs: Any) -> dict:
    """
    obs: a Person 1 Observation instance (duck-typed here, not imported,
    so this module has zero import-time dependency on P1's package --
    only field access at call time).
    """
    result = {
        "time": obs.time,
        "band": obs.scanned_band,
        "detected": obs.detected,
    }
    # Match P2's own convention (see ew_scheduler/backend/evaluation/
    # experiment_runner.py): only attach power/pulse_width/pri when the
    # observation actually detected something -- an undetected scan has
    # no meaningful signal characteristics to report.
    if obs.detected:
        if obs.measured_power_db is not None:
            result["power"] = obs.measured_power_db
        if obs.pulse_width_us is not None:
            result["pulse_width"] = obs.pulse_width_us
        if obs.pri_us is not None:
            result["pri"] = obs.pri_us
    return result
