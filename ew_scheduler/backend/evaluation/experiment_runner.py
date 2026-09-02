# backend/evaluation/experiment_runner.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prediction'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scheduler'))

import random
from metrics import SimulationResult
from history_manager import BandHistoryManager


def extract_bursts(ground_truth: dict[int, list[int]]) -> dict[int, list[dict]]:
    """
    Convert ground truth active time steps into burst objects.
    A burst is a contiguous run of active time steps for one band.

    Returns:
        { band: [ {start, end, intercepted, intercept_time}, ... ] }
    """
    bursts = {}

    for band, active_times in ground_truth.items():
        if not active_times:
            bursts[band] = []
            continue

        sorted_times = sorted(active_times)
        band_bursts  = []
        burst_start  = sorted_times[0]
        prev         = sorted_times[0]

        for t in sorted_times[1:]:
            if t == prev + 1:
                prev = t
            else:
                band_bursts.append({
                    "start":          burst_start,
                    "end":            prev,
                    "intercepted":    False,
                    "intercept_time": None,
                })
                burst_start = t
                prev        = t

        # Close final burst
        band_bursts.append({
            "start":          burst_start,
            "end":            prev,
            "intercepted":    False,
            "intercept_time": None,
        })

        bursts[band] = band_bursts

    return bursts


def run_simulation(
    scheduler,
    bands: list[int],
    ground_truth: dict[int, list[int]],
    total_steps: int,
    scheduler_name: str = "unnamed",
    noise_prob: float   = 0.0,
    seed: int           = 42,
) -> SimulationResult:
    """
    Run one complete simulation with the given scheduler.

    scheduler:       any BaseScheduler subclass
    bands:           list of all band IDs
    ground_truth:    { band: [active_time_steps] }
    total_steps:     how many time steps to simulate
    scheduler_name:  label for results
    noise_prob:      probability of a false detection (sensor noise)
    seed:            for reproducibility

    Returns: SimulationResult with all metrics computed.
    """
    rng = random.Random(seed)
    scheduler.reset()

    hm     = BandHistoryManager(max_history_per_band=200)
    result = SimulationResult(scheduler_name=scheduler_name)

    # Build fast lookup: (band, time) -> active
    gt_active = set()
    for band, times in ground_truth.items():
        for t in times:
            gt_active.add((band, t))

    result.total_active_steps = len(gt_active)

    # Extract bursts for intercept time calculation
    bursts = extract_bursts(ground_truth)

    # ----------------------------------------------------------------
    # MAIN SIMULATION LOOP
    # ----------------------------------------------------------------

    for t in range(1, total_steps + 1):

        # 1. Scheduler picks a band
        chosen_band = scheduler.select_band(bands, hm, current_time=t)

        # 2. Check ground truth
        actually_active = (chosen_band, t) in gt_active

        # 3. Determine detected (with optional noise)
        if actually_active:
            detected = True
        else:
            detected = rng.random() < noise_prob

        # 4. Build observation
        obs = {"time": t, "band": chosen_band, "detected": detected}
        if detected and actually_active:
            obs["power"] = rng.uniform(-50, -30)

        # 5. Feed to history manager
        hm.ingest(obs)

        # 6. Update counters
        result.total_steps += 1
        if detected:
            result.total_hits += 1
        else:
            result.total_misses += 1

        # 7. Log decision
        result.decision_log.append({
            "time":                t,
            "band":                chosen_band,
            "detected":            detected,
            "ground_truth_active": actually_active,
        })

        # 8. Update burst interception records
        for burst in bursts.get(chosen_band, []):
            if burst["intercepted"]:
                continue
            if burst["start"] <= t <= burst["end"]:
                burst["intercepted"]    = True
                burst["intercept_time"] = t - burst["start"]

    # ----------------------------------------------------------------
    # COMPUTE INTERCEPT TIME STATISTICS
    # ----------------------------------------------------------------

    for band_bursts in bursts.values():
        for burst in band_bursts:
            if burst["intercepted"]:
                result.intercept_times.append(burst["intercept_time"])
            else:
                result.missed_bursts += 1

    return result
