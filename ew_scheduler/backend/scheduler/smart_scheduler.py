# backend/scheduler/smart_scheduler.py

import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "prediction",
    ),
)

import random

from base_scheduler import BaseScheduler
from history_manager import BandHistoryManager
from predict import Predictor
from periodicity_detector import PeriodicityDetector
from behavior_detector import BehaviorDetector


class SmartScheduler(BaseScheduler):
    """
    ML-driven scheduler with Active-Band Memory, Multi-Band Tracking,
    Temporal / Periodicity Intelligence, Behavior Intelligence,
    anti-overexploitation, and adaptive exploration.
    """

    def __init__(
        self,
        predictor: Predictor,
        w_prob: float = 0.70,
        w_stale: float = 0.20,
        w_unc: float = 0.10,
        w_recent: float = 0.10,
        epsilon: float = 0.15,
        stale_cap: int = 50,
        seed: int = None,
        repeat_penalty_weight: float = 0.20,
        repeat_penalty_start: int = 2,
        repeat_penalty_cap: float = 0.40,
        exploration_bonus_weight: float = 0.05,
        exploration_staleness_scale: int = 100,
        active_confirmation_hits: int = 2,
        active_window: int = 20,
        active_memory_timeout: int = 50,
        active_max_misses: int = 4,
        w_active: float = 0.15,
        tracking_dwell_limit: int = 4,
        tracking_dwell_bonus: float = 0.10,
        tracking_cooldown_penalty: float = 0.20,
        discovery_interval: int = 5,
        discovery_candidate_timeout: int = 50,
        prior_knowledge=None,
        warm_prior_weight: float = 0.05,
        periodicity_detector: PeriodicityDetector = None,
        w_temporal: float = 0.15,
        behavior_detector: BehaviorDetector = None,
        w_behavior: float = 0.10,
    ):
        self.predictor = predictor

        # Phase 6: temporal intelligence
        self.periodicity_detector = (
            periodicity_detector
            or PeriodicityDetector()
        )
        self.w_temporal = w_temporal

        # Phase 7: behavior intelligence
        self.behavior_detector = (
            behavior_detector
            or BehaviorDetector()
        )
        self.w_behavior = w_behavior

        self.w_prob = w_prob
        self.w_stale = w_stale
        self.w_unc = w_unc
        self.w_recent = w_recent
        self.epsilon = epsilon
        self.stale_cap = stale_cap

        self._seed = seed
        self._rng = random.Random(seed)
        self._initial_rng_state = self._rng.getstate()

        self._cold_start_seed = seed
        self._cold_start_rng = random.Random(seed)

        self.repeat_penalty_weight = repeat_penalty_weight
        self.repeat_penalty_start = repeat_penalty_start
        self.repeat_penalty_cap = repeat_penalty_cap
        self.exploration_bonus_weight = exploration_bonus_weight
        self.exploration_staleness_scale = (
            exploration_staleness_scale
        )

        self.active_confirmation_hits = (
            active_confirmation_hits
        )
        self.active_window = active_window
        self.active_memory_timeout = (
            active_memory_timeout
        )
        self.active_max_misses = active_max_misses
        self.w_active = w_active
        self.tracking_dwell_limit = tracking_dwell_limit
        self.tracking_dwell_bonus = tracking_dwell_bonus
        self.tracking_cooldown_penalty = (
            tracking_cooldown_penalty
        )

        self.discovery_interval = discovery_interval
        self.discovery_candidate_timeout = (
            discovery_candidate_timeout
        )

        self.warm_prior_weight = warm_prior_weight
        self._warm_prior_by_band: dict[int, float] = {}

        if prior_knowledge is not None:
            for band_knowledge in getattr(
                prior_knowledge,
                "bands",
                [],
            ):
                band_id = getattr(
                    band_knowledge,
                    "band_id",
                    None,
                )

                hit_ratio = getattr(
                    band_knowledge,
                    "hit_ratio",
                    0.0,
                )

                confidence = getattr(
                    band_knowledge,
                    "confidence",
                    0.0,
                )

                if isinstance(band_id, int):
                    evidence_strength = max(
                        0.0,
                        min(
                            hit_ratio * confidence,
                            1.0,
                        ),
                    )

                    self._warm_prior_by_band[
                        band_id
                    ] = evidence_strength

        self._last_scanned = None
        self._consecutive_scans = 0
        self._tracking_dwell = 0
        self._consecutive_active_scans = 0
        self._active_memory: dict[int, dict] = {}
        self._discovery_candidates: dict[int, dict] = {}
        self._cold_start_remaining: list[int] = []
        self._cold_start_visited: set[int] = set()
        self._cold_start_initialized = False

    def reset(self) -> None:
        self._last_scanned = None
        self._consecutive_scans = 0
        self._tracking_dwell = 0
        self._consecutive_active_scans = 0
        self._active_memory = {}
        self._discovery_candidates = {}
        self._cold_start_remaining = []
        self._cold_start_visited = set()
        self._cold_start_initialized = False

        self._rng.setstate(self._initial_rng_state)
        self._cold_start_rng = random.Random(
            self._cold_start_seed
        )

    def _select_cold_start_band(
        self,
        bands: list[int],
    ) -> int | None:
        available_bands = list(
            dict.fromkeys(bands)
        )
        available_set = set(available_bands)

        if not self._cold_start_initialized:
            self._cold_start_remaining = available_bands
            self._cold_start_rng.shuffle(
                self._cold_start_remaining
            )
            self._cold_start_initialized = True

        else:
            self._cold_start_remaining = [
                band
                for band in self._cold_start_remaining
                if band in available_set
            ]

            pending = set(
                self._cold_start_remaining
            )

            additions = [
                band
                for band in available_bands
                if (
                    band not in self._cold_start_visited
                    and band not in pending
                )
            ]

            self._cold_start_rng.shuffle(additions)

            self._cold_start_remaining = (
                additions
                + self._cold_start_remaining
            )

        if self._cold_start_remaining:
            chosen = self._cold_start_remaining.pop()
            self._cold_start_visited.add(chosen)
            return chosen

        return None

    # ------------------------------------------------------------------
    # ACTIVE-BAND MEMORY & DISCOVERY
    # ------------------------------------------------------------------

    def _update_active_memory(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> None:

        for band in list(
            self._active_memory.keys()
        ):
            last_hit = history_manager.last_hit_time(
                band
            )

            if (
                last_hit is None
                or (
                    current_time - last_hit
                ) > self.active_memory_timeout
            ):
                del self._active_memory[band]
                continue

            band_hist = history_manager.get_band_history(
                band
            )

            consec_misses = 0

            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break

            if consec_misses >= self.active_max_misses:
                del self._active_memory[band]

        for band in list(
            self._discovery_candidates.keys()
        ):
            if band in self._active_memory:
                del self._discovery_candidates[band]
                continue

            last_hit = history_manager.last_hit_time(
                band
            )

            if (
                last_hit is None
                or (
                    current_time - last_hit
                ) > self.discovery_candidate_timeout
            ):
                del self._discovery_candidates[band]
                continue

            band_hist = history_manager.get_band_history(
                band
            )

            consec_misses = 0

            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break

            if consec_misses >= self.active_max_misses:
                del self._discovery_candidates[band]

        for band in bands:
            band_hist = history_manager.get_band_history(
                band
            )

            consec_misses = 0

            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break

            if consec_misses >= self.active_max_misses:
                continue

            recent = history_manager.get_band_history(
                band,
                n=self.active_window,
            )

            hits = sum(
                1
                for obs in recent
                if obs["detected"]
            )

            last_hit = history_manager.last_hit_time(
                band
            )

            if last_hit is None:
                continue

            if hits >= self.active_confirmation_hits:
                if (
                    current_time - last_hit
                ) <= self.active_memory_timeout:
                    self._active_memory[band] = {
                        "last_hit_time": last_hit,
                        "confirmed_hits": hits,
                    }

                    if (
                        band
                        in self._discovery_candidates
                    ):
                        del self._discovery_candidates[
                            band
                        ]

            elif hits >= 1:
                if (
                    current_time - last_hit
                ) <= self.discovery_candidate_timeout:
                    if band not in self._active_memory:
                        self._discovery_candidates[
                            band
                        ] = {
                            "last_hit_time": last_hit,
                            "discovery_hit_count": hits,
                        }

    # ------------------------------------------------------------------
    # GLOBAL BEHAVIOR ANALYSIS
    # ------------------------------------------------------------------

    def _analyze_global_behavior(
        self,
        history_manager: BandHistoryManager,
        current_time: int,
    ):
        """
        Infer behavior from the complete receiver observation history.

        Only observations available up to current_time are used.
        No ground truth, emitter identity, or future information is used.
        """
        from global_history import get_global_observations

        observations = get_global_observations(
            history_manager
        )

        if not observations:
            return None

        return self.behavior_detector.analyze(
            observations,
            current_time=current_time,
        )

    # ------------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------------

    def _score_band(
        self,
        band: int,
        prob: float,
        history_manager: BandHistoryManager,
        current_time: int,
        global_behavior=None,
    ) -> float:

        # 1. Predicted activity probability
        score = self.w_prob * prob

        # 2. Staleness
        t_last = history_manager.last_scan_time(
            band
        )

        gap = (
            current_time - t_last
            if t_last is not None
            else self.stale_cap
        )

        staleness = min(
            gap / self.stale_cap,
            1.0,
        )

        score += self.w_stale * staleness

        # 3. Model uncertainty
        uncertainty = (
            0.5 - abs(prob - 0.5)
        )

        score += self.w_unc * (
            uncertainty / 0.5
        )

        # 4. Exploration bonus
        gap_explore = (
            current_time - t_last
            if t_last is not None
            else self.exploration_staleness_scale
        )

        exploration_ratio = min(
            gap_explore
            / self.exploration_staleness_scale,
            1.0,
        )

        exploration_bonus = (
            self.exploration_bonus_weight
            * exploration_ratio
        )

        score += exploration_bonus

        # 5. Persistent historical evidence
        score += (
            self.warm_prior_weight
            * self._warm_prior_by_band.get(
                band,
                0.0,
            )
        )

        # 6. Temporal / periodicity intelligence
        if (
            self.w_temporal > 0.0
            and self.periodicity_detector is not None
        ):
            pres = (
                self.periodicity_detector.analyze_band(
                    history_manager,
                    band,
                    current_time,
                )
            )

            temporal_signal = (
                pres.temporal_proximity
                * pres.period_regularity
                * pres.confidence
            )

            score += (
                self.w_temporal
                * temporal_signal
            )

        # 7. Existing per-band behavior intelligence
        #
        # Kept unchanged for this step.
        if (
            self.w_behavior > 0.0
            and self.behavior_detector is not None
        ):
            band_history = (
                history_manager.get_band_history(
                    band
                )
            )

            behavior_result = (
                self.behavior_detector.analyze(
                    band_history,
                    current_time=current_time,
                )
            )

            if (
                behavior_result.behavior
                != "unknown"
            ):
                behavior_signal = max(
                    0.0,
                    min(
                        behavior_result.confidence,
                        1.0,
                    ),
                )

                score += (
                    self.w_behavior
                    * behavior_signal
                )

        # 8. Phase 7: candidate-specific global behavior intelligence
        #
        # Agile and Scanning are cross-band behaviors, so their
        # scheduling signal must use the complete observation history.
        #
        # The bonus is deliberately bounded and additive so behavior
        # intelligence cannot overpower the existing ML/temporal score.

        global_behavior_bonus = 0.0

        if (
            self.w_behavior > 0.0
            and global_behavior is not None
            and global_behavior.behavior in {
                "agile",
                "scanning",
            }
        ):
            features = global_behavior.features

            # Only detected observations are meaningful for movement.
            from global_history import get_global_observations

            global_observations = (
                get_global_observations(
                    history_manager
                )
            )

            detected_observations = [
                obs
                for obs in global_observations
                if (
                    obs.get("detected", False)
                    and obs.get("time", 0) <= current_time
                )
            ]

            if len(detected_observations) >= 2:

                recent_detected = (
                    detected_observations[-10:]
                )

                recent_bands = [
                    obs["band"]
                    for obs in recent_detected
                ]

                # --------------------------------------------------
                # Scanning:
                # Favor the next band in the observed direction.
                # --------------------------------------------------

                if (
                    global_behavior.behavior
                    == "scanning"
                ):
                    last_band = recent_bands[-1]

                    previous_band = (
                        recent_bands[-2]
                    )

                    direction = (
                        last_band
                        - previous_band
                    )

                    if direction != 0:

                        expected_band = (
                            last_band
                            + (
                                1
                                if direction > 0
                                else -1
                            )
                        )

                        if band == expected_band:
                            global_behavior_bonus = (
                                self.w_behavior
                                * global_behavior.confidence
                            )

                        # A candidate adjacent to the latest
                        # observed band receives only half the
                        # directional bonus. This keeps the policy
                        # conservative under partial observability.
                        elif (
                            abs(
                                band - last_band
                            )
                            == 1
                        ):
                            global_behavior_bonus = (
                                0.5
                                * self.w_behavior
                                * global_behavior.confidence
                            )

                # --------------------------------------------------
                # Agile:
                # Favor recently observed hop destinations.
                # --------------------------------------------------

                elif (
                    global_behavior.behavior
                    == "agile"
                ):
                    recent_unique = set(
                        recent_bands[-5:]
                    )

                    if band in recent_unique:
                        global_behavior_bonus = (
                            self.w_behavior
                            * global_behavior.confidence
                        )

                    # Nearby bands receive only a weak bonus.
                    # Agile emitters may hop non-locally, so this is
                    # intentionally much weaker than an observed hop.
                    elif any(
                        abs(
                            band - recent_band
                        )
                        <= 1
                        for recent_band
                        in recent_unique
                    ):
                        global_behavior_bonus = (
                            0.25
                            * self.w_behavior
                            * global_behavior.confidence
                        )

            # Final safety bound.
            global_behavior_bonus = max(
                0.0,
                min(
                    global_behavior_bonus,
                    self.w_behavior,
                ),
            )

            score += global_behavior_bonus

        # 9. Active-band memory
        if band in self._active_memory:
            score += self.w_active

            if (
                band == self._last_scanned
                and self._tracking_dwell
                < self.tracking_dwell_limit
            ):
                score += self.tracking_dwell_bonus

        # 10. Repeat / cooldown penalties
        if band == self._last_scanned:

            score -= (
                self.w_recent
                * (1.0 - prob)
            )

            if (
                self._consecutive_scans
                > self.repeat_penalty_start
            ):
                excess = (
                    self._consecutive_scans
                    - self.repeat_penalty_start
                )

                repeat_penalty = min(
                    self.repeat_penalty_cap,
                    self.repeat_penalty_weight
                    * (excess / 10.0),
                )

                score -= repeat_penalty

            if (
                len(self._active_memory) >= 2
                and self._tracking_dwell
                >= self.tracking_dwell_limit
            ):
                score -= (
                    self.tracking_cooldown_penalty
                )

        return score

    # ------------------------------------------------------------------
    # EXPLORATION
    # ------------------------------------------------------------------

    def _exploration_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
    ) -> int:

        counts = {
            b: history_manager.scan_count(b)
            for b in bands
        }

        min_count = min(
            counts.values()
        )

        candidates = [
            b
            for b, c in counts.items()
            if c == min_count
        ]

        return self._rng.choice(
            candidates
        )

    def _update_run_tracking(
        self,
        chosen: int,
    ) -> None:

        if chosen == self._last_scanned:
            self._consecutive_scans += 1
            self._tracking_dwell += 1

        else:
            self._last_scanned = chosen
            self._consecutive_scans = 1
            self._tracking_dwell = 1

    # ------------------------------------------------------------------
    # BAND SELECTION
    # ------------------------------------------------------------------

    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:

        cold_start_band = (
            self._select_cold_start_band(bands)
        )

        if cold_start_band is not None:
            return cold_start_band

        self._update_active_memory(
            bands,
            history_manager,
            current_time,
        )

        # Analyze complete observation history once.
        #
        # This result is currently passed through to _score_band()
        # without affecting the score. The actual candidate-specific
        # behavior policy will be added in the next step.
        global_behavior = (
            self._analyze_global_behavior(
                history_manager,
                current_time,
            )
        )

        force_discovery = False

        if (
            len(self._active_memory) < 2
            and self._consecutive_active_scans
            >= (
                self.discovery_interval - 1
            )
        ):
            non_active_bands = [
                b
                for b in bands
                if b not in self._active_memory
            ]

            if non_active_bands:
                force_discovery = True

        if force_discovery:
            candidate_bands = [
                b
                for b in bands
                if b not in self._active_memory
            ]

            if (
                self._rng.random()
                < self.epsilon
            ):
                chosen = self._exploration_band(
                    candidate_bands,
                    history_manager,
                )

            else:
                predictions = (
                    self.predictor.predict_all_bands(
                        candidate_bands,
                        history_manager,
                        current_time,
                    )
                )

                scores = {
                    band: self._score_band(
                        band,
                        prob,
                        history_manager,
                        current_time,
                        global_behavior,
                    )
                    for band, prob
                    in predictions.items()
                }

                chosen = max(
                    scores,
                    key=lambda b: scores[b],
                )

            self._update_run_tracking(
                chosen
            )

            self._consecutive_active_scans = 0

            return chosen

        if (
            self._rng.random()
            < self.epsilon
        ):
            chosen = self._exploration_band(
                bands,
                history_manager,
            )

            self._update_run_tracking(
                chosen
            )

            if chosen in self._active_memory:
                self._consecutive_active_scans += 1
            else:
                self._consecutive_active_scans = 0

            return chosen

        predictions = (
            self.predictor.predict_all_bands(
                bands,
                history_manager,
                current_time,
            )
        )

        scores = {
            band: self._score_band(
                band,
                prob,
                history_manager,
                current_time,
                global_behavior,
            )
            for band, prob
            in predictions.items()
        }

        chosen = max(
            scores,
            key=lambda b: scores[b],
        )

        self._update_run_tracking(
            chosen
        )

        if chosen in self._active_memory:
            self._consecutive_active_scans += 1
        else:
            self._consecutive_active_scans = 0

        return chosen

    # ------------------------------------------------------------------
    # DIAGNOSTICS
    # ------------------------------------------------------------------

    def explain_decision(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
        top_n: int = 5,
    ) -> None:

        self._update_active_memory(
            bands,
            history_manager,
            current_time,
        )

        global_behavior = (
            self._analyze_global_behavior(
                history_manager,
                current_time,
            )
        )

        predictions = (
            self.predictor.predict_all_bands(
                bands,
                history_manager,
                current_time,
            )
        )

        scored = []

        for band, prob in predictions.items():

            score = self._score_band(
                band,
                prob,
                history_manager,
                current_time,
                global_behavior,
            )

            t_last = history_manager.last_scan_time(
                band
            )

            gap = (
                current_time - t_last
                if t_last is not None
                else self.stale_cap
            )

            staleness = min(
                gap / self.stale_cap,
                1.0,
            )

            uncertainty = (
                0.5 - abs(prob - 0.5)
            )

            gap_explore = (
                current_time - t_last
                if t_last is not None
                else self.exploration_staleness_scale
            )

            explore_bonus = (
                self.exploration_bonus_weight
                * min(
                    gap_explore
                    / self.exploration_staleness_scale,
                    1.0,
                )
            )

            active_bonus = (
                self.w_active
                if band in self._active_memory
                else 0.0
            )

            temporal_bonus = 0.0
            period_est = 0.0

            if (
                self.w_temporal > 0.0
                and self.periodicity_detector is not None
            ):
                pres = (
                    self.periodicity_detector.analyze_band(
                        history_manager,
                        band,
                        current_time,
                    )
                )

                temporal_bonus = (
                    self.w_temporal
                    * (
                        pres.temporal_proximity
                        * pres.period_regularity
                        * pres.confidence
                    )
                )

                period_est = (
                    pres.estimated_period
                )

            behavior_bonus = 0.0
            behavior_name = "unknown"
            behavior_confidence = 0.0

            if (
                self.w_behavior > 0.0
                and self.behavior_detector is not None
            ):
                behavior_result = (
                    self.behavior_detector.analyze(
                        history_manager.get_band_history(
                            band
                        ),
                        current_time=current_time,
                    )
                )

                behavior_name = (
                    behavior_result.behavior
                )

                behavior_confidence = (
                    behavior_result.confidence
                )

                if behavior_name != "unknown":
                    behavior_bonus = (
                        self.w_behavior
                        * max(
                            0.0,
                            min(
                                behavior_confidence,
                                1.0,
                            ),
                        )
                    )

            repeat_penalty = 0.0
            cooldown_penalty = 0.0

            if band == self._last_scanned:

                if (
                    self._consecutive_scans
                    > self.repeat_penalty_start
                ):
                    excess = (
                        self._consecutive_scans
                        - self.repeat_penalty_start
                    )

                    repeat_penalty = min(
                        self.repeat_penalty_cap,
                        self.repeat_penalty_weight
                        * (excess / 10.0),
                    )

                if (
                    len(self._active_memory) >= 2
                    and self._tracking_dwell
                    >= self.tracking_dwell_limit
                ):
                    cooldown_penalty = (
                        self.tracking_cooldown_penalty
                    )

            scored.append(
                {
                    "band": band,
                    "score": score,
                    "prob": prob,
                    "staleness": staleness,
                    "uncertainty": uncertainty,
                    "explore_bonus": explore_bonus,
                    "active_bonus": active_bonus,
                    "temporal_bonus": temporal_bonus,
                    "period_est": period_est,
                    "behavior_bonus": behavior_bonus,
                    "behavior": behavior_name,
                    "behavior_confidence": behavior_confidence,
                    "repeat_penalty": (
                        repeat_penalty
                        + cooldown_penalty
                    ),
                }
            )

        scored.sort(
            key=lambda x: x["score"],
            reverse=True,
        )

        active_list = sorted(
            list(self._active_memory.keys())
        )

        discovery_list = sorted(
            list(
                self._discovery_candidates.keys()
            )
        )

        print(
            f"\nScheduler decision at "
            f"t={current_time} "
            f"(last={self._last_scanned}, "
            f"dwell={self._tracking_dwell}, "
            f"consec_active="
            f"{self._consecutive_active_scans}, "
            f"active_memory={active_list}, "
            f"discovery_candidates="
            f"{discovery_list}):"
        )

        if global_behavior is not None:
            print(
                f"  Global behavior: "
                f"{global_behavior.behavior} "
                f"(confidence="
                f"{global_behavior.confidence:.3f})"
            )
        else:
            print(
                "  Global behavior: unknown"
            )

        print(
            f"  {'Band':<6} "
            f"{'Score':<8} "
            f"{'P(act)':<8} "
            f"{'Stale':<8} "
            f"{'Uncert':<8} "
            f"{'ExpBon':<8} "
            f"{'ActBon':<8} "
            f"{'TmpBon':<8} "
            f"{'BehBon':<8} "
            f"{'Behavior':<10} "
            f"{'Penalties':<8}"
        )

        print(
            f"  {'-' * 110}"
        )

        for i, row in enumerate(
            scored[:top_n]
        ):
            marker = (
                " <- CHOSEN"
                if i == 0
                else ""
            )

            print(
                f"  {row['band']:<6} "
                f"{row['score']:<8.3f} "
                f"{row['prob']:<8.3f} "
                f"{row['staleness']:<8.3f} "
                f"{row['uncertainty']:<8.3f} "
                f"{row['explore_bonus']:<8.3f} "
                f"{row['active_bonus']:<8.3f} "
                f"{row['temporal_bonus']:<8.3f} "
                f"{row['behavior_bonus']:<8.3f} "
                f"{row['behavior']:<10} "
                f"{row['repeat_penalty']:<8.3f}"
                f"{marker}"
            )