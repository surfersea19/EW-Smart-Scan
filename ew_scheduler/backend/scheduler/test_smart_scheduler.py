import pytest
import sys
import os

# Add prediction and scheduler folders to path
SCHED_DIR = os.path.dirname(os.path.abspath(__file__))
PRED_DIR = os.path.abspath(os.path.join(SCHED_DIR, "..", "prediction"))
if SCHED_DIR not in sys.path:
    sys.path.insert(0, SCHED_DIR)
if PRED_DIR not in sys.path:
    sys.path.insert(0, PRED_DIR)

from history_manager import BandHistoryManager
from smart_scheduler import SmartScheduler


class MockPredictor:
    """Mock predictor returning configured probabilities for testing scoring logic."""

    def __init__(self, probabilities: dict[int, float] = None, default_prob: float = 0.3861):
        self.probabilities = probabilities or {}
        self.default_prob = default_prob

    def predict_band(self, band: int, history_manager, current_time: int) -> float:
        return self.probabilities.get(band, self.default_prob)

    def predict_all_bands(self, bands: list[int], history_manager, current_time: int) -> dict[int, float]:
        return {b: self.predict_band(b, history_manager, current_time) for b in bands}


def test_single_active_band_enters_memory():
    """
    Test requirement 10A: A band with confirmed detections (>= active_confirmation_hits)
    enters active_band_memory with valid metadata.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True, "power": -50.0})
    hm.ingest({"time": 11, "band": 16, "detected": True, "power": -48.0})

    mock_pred = MockPredictor(probabilities={16: 0.90})
    scheduler = SmartScheduler(mock_pred, active_confirmation_hits=2, epsilon=0.0)

    scheduler._update_active_memory([16, 20], hm, current_time=12)

    assert 16 in scheduler._active_memory, "Band 16 must enter active_memory after 2 hits"
    assert scheduler._active_memory[16]["last_hit_time"] == 11
    assert scheduler._active_memory[16]["confirmed_hits"] == 2
    assert 20 not in scheduler._active_memory, "Unvisited Band 20 must not be in active_memory"


def test_single_hit_does_not_confirm():
    """
    Test requirement 10B: A single hit is treated as tentative and does not confirm
    a band into active memory when active_confirmation_hits = 2.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True, "power": -50.0})

    mock_pred = MockPredictor(probabilities={16: 0.90})
    scheduler = SmartScheduler(mock_pred, active_confirmation_hits=2, epsilon=0.0)

    scheduler._update_active_memory([16], hm, current_time=11)
    assert 16 not in scheduler._active_memory, "Band with only 1 hit must not enter active_memory"


def test_two_active_bands_coexist():
    """
    Test requirement 10C: Multiple confirmed active bands can coexist simultaneously
    in active_band_memory.
    """
    hm = BandHistoryManager()
    # Band 16 confirmed
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})
    # Band 115 confirmed
    hm.ingest({"time": 20, "band": 115, "detected": True})
    hm.ingest({"time": 21, "band": 115, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.90, 115: 0.90})
    scheduler = SmartScheduler(mock_pred, active_confirmation_hits=2, epsilon=0.0)

    scheduler._update_active_memory([16, 115], hm, current_time=22)

    assert 16 in scheduler._active_memory, "Band 16 must be in active_memory"
    assert 115 in scheduler._active_memory, "Band 115 must be in active_memory"
    assert len(scheduler._active_memory) == 2


def test_multiple_active_candidates_prevent_monopoly_rotation():
    """
    Test requirement 10D: When multiple active candidates exist, one band cannot monopolize
    the receiver indefinitely; after tracking_dwell_limit consecutive scans, rotation cooldown
    forces the scheduler to switch to the other active candidate.
    """
    hm = BandHistoryManager()
    # Confirm Band 16 and Band 115 at t=20
    hm.ingest({"time": 19, "band": 16, "detected": True})
    hm.ingest({"time": 20, "band": 16, "detected": True})
    hm.ingest({"time": 19, "band": 115, "detected": True})
    hm.ingest({"time": 20, "band": 115, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.90, 115: 0.90, 50: 0.10})
    scheduler = SmartScheduler(
        mock_pred,
        epsilon=0.0,
        tracking_dwell_limit=4,
        tracking_cooldown_penalty=0.20,
        w_active=0.15,
    )

    # Initial decision at t=21 picks one of the active candidates
    first_choice = scheduler.select_band([16, 115, 50], hm, current_time=21)
    other_choice = 115 if first_choice == 16 else 16

    # Next 3 steps (steps 2, 3, 4) should continue dwelling on first_choice (up to dwell limit = 4)
    for step in range(2, 5):
        chosen = scheduler.select_band([16, 115, 50], hm, current_time=20 + step)
        assert chosen == first_choice, f"Step {step}: Should continue dwell on {first_choice}"

    assert scheduler._tracking_dwell == 4

    # On step 5 (decision 5), first_choice has reached dwell limit 4 and pays rotation cooldown -> switches to other_choice!
    chosen_step_5 = scheduler.select_band([16, 115, 50], hm, current_time=25)
    assert chosen_step_5 == other_choice, (
        f"Step 5: Scheduler must rotate to other active candidate ({other_choice}), got {chosen_step_5}"
    )


def test_return_to_previous_active_band_after_cooldown():
    """
    Test requirement 10E: After servicing Band 16, rotation dwell resets and the scheduler
    can smoothly return to Band 115.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 19, "band": 16, "detected": True})
    hm.ingest({"time": 20, "band": 16, "detected": True})
    hm.ingest({"time": 19, "band": 115, "detected": True})
    hm.ingest({"time": 20, "band": 115, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.90, 115: 0.90})
    scheduler = SmartScheduler(
        mock_pred,
        epsilon=0.0,
        tracking_dwell_limit=3,
        tracking_cooldown_penalty=0.20,
    )

    # Decisions 1..3 dwell on first candidate (e.g. Band 16)
    c1 = scheduler.select_band([16, 115], hm, current_time=21)
    c2 = 115 if c1 == 16 else 16
    scheduler.select_band([16, 115], hm, current_time=22)
    scheduler.select_band([16, 115], hm, current_time=23)

    # Decision 4 rotates to c2
    rot_1 = scheduler.select_band([16, 115], hm, current_time=24)
    assert rot_1 == c2, f"Expected rotation to {c2}, got {rot_1}"

    # Decisions 5..6 dwell on c2
    scheduler.select_band([16, 115], hm, current_time=25)
    scheduler.select_band([16, 115], hm, current_time=26)

    # Decision 7 rotates back to c1
    rot_2 = scheduler.select_band([16, 115], hm, current_time=27)
    assert rot_2 == c1, f"Expected rotation back to {c1}, got {rot_2}"


def test_expired_inactive_bands_leave_memory():
    """
    Test requirement 10F: Candidate bands leave active memory when inactive for > active_memory_timeout
    or after excessive consecutive misses (active_max_misses).
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.90})
    scheduler = SmartScheduler(
        mock_pred,
        active_memory_timeout=50,
        active_max_misses=3,
    )

    # Confirm in memory at t=15
    scheduler._update_active_memory([16], hm, current_time=15)
    assert 16 in scheduler._active_memory

    # Case 1: Timeout eviction at t=70 (gap=59 > timeout 50)
    scheduler._update_active_memory([16], hm, current_time=70)
    assert 16 not in scheduler._active_memory, "Band 16 must be evicted after timeout"

    # Case 2: Consecutive misses eviction
    hm2 = BandHistoryManager()
    hm2.ingest({"time": 10, "band": 20, "detected": True})
    hm2.ingest({"time": 11, "band": 20, "detected": True})
    scheduler._update_active_memory([20], hm2, current_time=12)
    assert 20 in scheduler._active_memory

    # Ingest 3 consecutive misses
    hm2.ingest({"time": 13, "band": 20, "detected": False})
    hm2.ingest({"time": 14, "band": 20, "detected": False})
    hm2.ingest({"time": 15, "band": 20, "detected": False})

    scheduler._update_active_memory([20], hm2, current_time=16)
    assert 20 not in scheduler._active_memory, "Band 20 must be evicted after 3 consecutive misses"


def test_unobserved_global_bands_remain_reachable():
    """
    Test requirement 10G: Unobserved bands remain reachable and are surveyed when
    no active bands exist, or via global exploration scoring.
    """
    hm = BandHistoryManager()
    mock_pred = MockPredictor(default_prob=0.3861)
    scheduler = SmartScheduler(mock_pred, epsilon=0.0)

    # No hits recorded -> sweeps unobserved bands
    chosen = scheduler.select_band([0, 1, 2, 3], hm, current_time=1)
    assert chosen in [0, 1, 2, 3]


def test_high_prob_recently_detected_beats_unobserved():
    """
    Baseline & Req 10I: High-probability recently detected band (e.g. P=0.92)
    scores higher than an unobserved band (P=0.386) and wins selection initially.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 10, "detected": True, "power": -50.0})

    mock_pred = MockPredictor(probabilities={10: 0.92, 20: 0.3861})
    scheduler = SmartScheduler(mock_pred, epsilon=0.0, seed=42)
    scheduler._last_scanned = 10
    scheduler._consecutive_scans = 1

    score_10 = scheduler._score_band(10, 0.92, hm, current_time=11)
    score_20 = scheduler._score_band(20, 0.3861, hm, current_time=11)

    assert score_10 > score_20, (
        f"Detected band (score={score_10:.4f}) must beat unobserved band (score={score_20:.4f})"
    )

    chosen = scheduler.select_band([10, 20], hm, current_time=11)
    assert chosen == 10, f"Expected Band 10 to be chosen for initial burst exploitation, got {chosen}"


def test_repeated_selection_progressively_penalized():
    """
    Baseline & Req 10I: Score monotonically decreases as consecutive selections increase.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 9, "band": 10, "detected": True})

    mock_pred = MockPredictor(probabilities={10: 0.90})
    scheduler = SmartScheduler(
        mock_pred,
        epsilon=0.0,
        repeat_penalty_weight=0.20,
        repeat_penalty_start=2,
        repeat_penalty_cap=0.40,
    )
    scheduler._last_scanned = 10

    scores = {}
    for runs in [1, 2, 3, 4, 6, 8, 12]:
        scheduler._consecutive_scans = runs
        s = scheduler._score_band(10, 0.90, hm, current_time=10)
        scores[runs] = s

    assert abs(scores[1] - scores[2]) < 1e-4
    assert scores[3] < scores[2]
    assert scores[4] < scores[3]
    assert scores[6] < scores[4]
    assert scores[8] < scores[6]
    assert scores[12] <= scores[8]


def test_exploration_bonus_increases_with_staleness():
    """
    Baseline & Req 10I: Long-unvisited bands receive a monotonically increasing
    exploration bonus as time since last scan increases.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 0, "band": 5, "detected": False})

    mock_pred = MockPredictor(probabilities={5: 0.20})
    scheduler = SmartScheduler(
        mock_pred,
        epsilon=0.0,
        exploration_bonus_weight=0.10,
        exploration_staleness_scale=100,
    )

    score_t10 = scheduler._score_band(5, 0.20, hm, current_time=10)
    score_t50 = scheduler._score_band(5, 0.20, hm, current_time=50)
    score_t100 = scheduler._score_band(5, 0.20, hm, current_time=100)
    score_t200 = scheduler._score_band(5, 0.20, hm, current_time=200)

    assert score_t10 < score_t50 < score_t100
    assert abs(score_t100 - score_t200) < 1e-4


def test_exploration_still_functioning():
    """
    Baseline & Req 10I: Epsilon exploration picks the least-scanned band.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 1, "band": 0, "detected": False})
    hm.ingest({"time": 2, "band": 0, "detected": False})
    hm.ingest({"time": 3, "band": 1, "detected": False})

    mock_pred = MockPredictor(default_prob=0.3861)
    scheduler = SmartScheduler(mock_pred, epsilon=1.0, seed=42)

    chosen = scheduler.select_band([0, 1, 2], hm, current_time=4)
    assert chosen == 2, f"Expected least-scanned band (Band 2) to be chosen by exploration, got {chosen}"


# ======================================================================
# BOUNDED DISCOVERY & CANDIDATE DISCOVERY TESTS
# ======================================================================

def test_single_hit_creates_temporary_discovery_candidate_not_active_memory():
    """
    Test Discovery Req 6: A single hit creates only a temporary discovery candidate,
    NOT confirmed active memory. It does not receive the active bonus.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True, "power": -50.0})

    mock_pred = MockPredictor(probabilities={16: 0.80, 20: 0.20})
    scheduler = SmartScheduler(mock_pred, active_confirmation_hits=2, epsilon=0.0)

    scheduler._update_active_memory([16, 20], hm, current_time=11)

    assert 16 not in scheduler._active_memory, "Single hit must NOT enter confirmed active memory"
    assert 16 in scheduler._discovery_candidates, "Single hit must create a temporary discovery candidate"
    assert scheduler._discovery_candidates[16]["discovery_hit_count"] == 1
    assert scheduler._discovery_candidates[16]["last_hit_time"] == 10

    # Verify score does not include w_active
    score_no_active = scheduler._score_band(16, 0.80, hm, current_time=11)
    # Put in active memory manually to check difference
    scheduler._active_memory[16] = {"last_hit_time": 10, "confirmed_hits": 2}
    score_with_active = scheduler._score_band(16, 0.80, hm, current_time=11)
    assert score_with_active > score_no_active, "Confirmed active memory must provide active bonus"


def test_temporary_candidate_expires():
    """
    Test Discovery Req 7: Temporary candidates expire when inactive for > timeout
    or after excessive consecutive misses.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.80})
    scheduler = SmartScheduler(mock_pred, discovery_candidate_timeout=30, active_max_misses=3)

    # In discovery candidates at t=12
    scheduler._update_active_memory([16], hm, current_time=12)
    assert 16 in scheduler._discovery_candidates

    # Timeout eviction at t=45 (gap = 35 > timeout 30)
    scheduler._update_active_memory([16], hm, current_time=45)
    assert 16 not in scheduler._discovery_candidates, "Temporary candidate must expire after timeout"

    # Consecutive misses eviction
    hm2 = BandHistoryManager()
    hm2.ingest({"time": 10, "band": 20, "detected": True})
    scheduler._update_active_memory([20], hm2, current_time=11)
    assert 20 in scheduler._discovery_candidates

    hm2.ingest({"time": 12, "band": 20, "detected": False})
    hm2.ingest({"time": 13, "band": 20, "detected": False})
    hm2.ingest({"time": 14, "band": 20, "detected": False})
    scheduler._update_active_memory([20], hm2, current_time=15)
    assert 20 not in scheduler._discovery_candidates, "Temporary candidate must expire after 3 consecutive misses"


def test_temporary_candidate_promotes_to_confirmed_active_memory():
    """
    Test Discovery Req: A temporary candidate promotes to confirmed active memory
    when a second hit is observed within the active window.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.80})
    scheduler = SmartScheduler(mock_pred, active_confirmation_hits=2)

    scheduler._update_active_memory([16], hm, current_time=11)
    assert 16 in scheduler._discovery_candidates
    assert 16 not in scheduler._active_memory

    # Second hit arrives
    hm.ingest({"time": 12, "band": 16, "detected": True})
    scheduler._update_active_memory([16], hm, current_time=13)
    assert 16 in scheduler._active_memory, "Must be promoted to confirmed active memory on 2nd hit"
    assert 16 not in scheduler._discovery_candidates, "Must be removed from temporary discovery candidates once confirmed"


def test_single_confirmed_active_band_cannot_monopolize_indefinitely():
    """
    Test Discovery Req 1 & 2: A single confirmed active band cannot monopolize indefinitely.
    After the configured exploitation interval (discovery_interval - 1 decisions),
    a non-active band is selected for discovery.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})

    # High probability for Band 16 (0.95), lower for others
    mock_pred = MockPredictor(probabilities={16: 0.95, 20: 0.40, 30: 0.30})
    scheduler = SmartScheduler(mock_pred, epsilon=0.0, discovery_interval=5)

    # Steps 1 to 4: Confirmed active Band 16 is selected normally
    for step in range(1, 5):
        chosen = scheduler.select_band([16, 20, 30], hm, current_time=11 + step)
        assert chosen == 16, f"Step {step}: Band 16 should be selected normally during exploitation budget"
        assert scheduler._consecutive_active_scans == step

    assert scheduler._consecutive_active_scans == 4

    # Step 5: Bounded discovery decision forced! Must pick a non-active band (Band 20 or 30)
    discovery_choice = scheduler.select_band([16, 20, 30], hm, current_time=16)
    assert discovery_choice != 16, f"Step 5: Must force discovery outside confirmed active band 16, got {discovery_choice}"
    assert discovery_choice in [20, 30]
    assert scheduler._consecutive_active_scans == 0, "Consecutive active scans must reset after discovery decision"


def test_discovery_does_not_use_pure_random_selection():
    """
    Test Discovery Req 3: Discovery candidate selection uses existing ML scoring / staleness,
    not pure random selection.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})

    # Band 30 has highest probability among non-active candidates (0.40 vs 0.10, 0.20)
    mock_pred = MockPredictor(probabilities={16: 0.95, 20: 0.10, 30: 0.40, 40: 0.20})
    scheduler = SmartScheduler(mock_pred, epsilon=0.0, discovery_interval=5)

    # Exploit Band 16 for 4 decisions
    for t in range(12, 16):
        c = scheduler.select_band([16, 20, 30, 40], hm, current_time=t)
        assert c == 16, f"t={t}: Band 16 should be selected during exploitation"

    # Decision 5 is forced discovery: must choose highest-scoring non-active band (Band 30)
    chosen = scheduler.select_band([16, 20, 30, 40], hm, current_time=16)
    assert chosen == 30, f"Discovery must pick highest-scoring non-active candidate (Band 30), got {chosen}"


def test_discovery_does_not_become_blind_round_robin():
    """
    Test Discovery Req 4: Discovery is driven by scoring, not blind round-robin cycling.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.95, 20: 0.10, 30: 0.40, 40: 0.20})
    scheduler = SmartScheduler(mock_pred, epsilon=0.0, discovery_interval=3)

    # Cycle 1 discovery (after 2 active scans)
    scheduler.select_band([16, 20, 30, 40], hm, current_time=12)
    scheduler.select_band([16, 20, 30, 40], hm, current_time=13)
    disc_1 = scheduler.select_band([16, 20, 30, 40], hm, current_time=14)
    assert disc_1 == 30, f"First discovery should pick Band 30, got {disc_1}"

    # Cycle 2 discovery (after 2 active scans)
    scheduler.select_band([16, 20, 30, 40], hm, current_time=15)
    scheduler.select_band([16, 20, 30, 40], hm, current_time=16)
    disc_2 = scheduler.select_band([16, 20, 30, 40], hm, current_time=17)
    # Band 30 still has higher score (P=0.40) than Band 20 (0.10) or Band 40 (0.20)
    assert disc_2 == 30, f"Second discovery should score-pick Band 30 rather than blind next-in-line (Band 40), got {disc_2}"


def test_multi_band_tracking_preserved_with_two_active_bands():
    """
    Test Discovery Req 5: When >=2 confirmed active bands exist, existing multi-band
    tracking dwell & rotation operate normally without discovery forcing.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})
    hm.ingest({"time": 10, "band": 115, "detected": True})
    hm.ingest({"time": 11, "band": 115, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.90, 115: 0.90, 50: 0.10})
    scheduler = SmartScheduler(
        mock_pred,
        epsilon=0.0,
        tracking_dwell_limit=4,
        tracking_cooldown_penalty=0.20,
        discovery_interval=5,
    )

    # 4 decisions dwell on first choice
    c1 = scheduler.select_band([16, 115, 50], hm, current_time=12)
    c2 = 115 if c1 == 16 else 16
    for t in range(13, 16):
        assert scheduler.select_band([16, 115, 50], hm, current_time=t) == c1

    # Decision 5 rotates to c2 (the other active candidate), NOT forcing discovery on Band 50
    rot = scheduler.select_band([16, 115, 50], hm, current_time=16)
    assert rot == c2, f"Expected rotation between active candidates to {c2}, got {rot}"


def test_confirmed_active_band_selected_normally_outside_discovery():
    """
    Test Discovery Req 8: Confirmed active band is selected normally and enjoys
    active bonus outside forced discovery steps.
    """
    hm = BandHistoryManager()
    hm.ingest({"time": 10, "band": 16, "detected": True})
    hm.ingest({"time": 11, "band": 16, "detected": True})

    mock_pred = MockPredictor(probabilities={16: 0.70, 20: 0.30})
    scheduler = SmartScheduler(mock_pred, epsilon=0.0, discovery_interval=5, w_active=0.15)

    # Decision 1: Band 16 receives +0.15 active bonus and wins over Band 20
    chosen = scheduler.select_band([16, 20], hm, current_time=12)
    assert chosen == 16, f"Confirmed active band 16 should be selected normally, got {chosen}"


def test_discovery_operates_without_ground_truth():
    """
    Test Discovery Req 9: Discovery and candidate management strictly operate
    using BandHistoryManager receiver observations, with no ground truth access.
    """
    hm = BandHistoryManager()
    mock_pred = MockPredictor(default_prob=0.3861)
    scheduler = SmartScheduler(mock_pred, discovery_interval=5)

    # Verify method signatures only take bands, history_manager, and current_time
    import inspect
    sig = inspect.signature(scheduler.select_band)
    params = list(sig.parameters.keys())
    assert params == ["bands", "history_manager", "current_time"], (
        f"select_band signature must strictly be ['bands', 'history_manager', 'current_time'], got {params}"
    )

    sig_mem = inspect.signature(scheduler._update_active_memory)
    params_mem = list(sig_mem.parameters.keys())
    assert params_mem == ["bands", "history_manager", "current_time"], (
        f"_update_active_memory signature must strictly be ['bands', 'history_manager', 'current_time'], got {params_mem}"
    )



