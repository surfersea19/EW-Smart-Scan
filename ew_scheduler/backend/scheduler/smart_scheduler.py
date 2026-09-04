# backend/scheduler/smart_scheduler.py

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'prediction'))

import random
from base_scheduler import BaseScheduler
from history_manager import BandHistoryManager
from predict import Predictor


class SmartScheduler(BaseScheduler):
    """
    ML-driven scheduler with Active-Band Memory, Multi-Band Tracking,
    anti-overexploitation, and adaptive exploration.

    Combines:
      - Predicted activity probability (primary signal)
      - Active-band memory candidate tracking (multi-emitter co-existence)
      - Tracking dwell rotation cooldown (prevents single-band monopoly)
      - Staleness & uncertainty scoring
      - Bounded long-term coverage exploration bonus
      - Progressive consecutive repeat penalty
      - Epsilon-greedy exploration (least-scanned band)

    All weights and parameters are tunable.
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
        # Active-band memory parameters
        active_confirmation_hits: int = 2,
        active_window: int = 20,
        active_memory_timeout: int = 50,
        active_max_misses: int = 4,
        w_active: float = 0.15,
        tracking_dwell_limit: int = 4,
        tracking_dwell_bonus: float = 0.10,
        tracking_cooldown_penalty: float = 0.20,
        # Bounded Discovery parameters
        discovery_interval: int = 5,
        discovery_candidate_timeout: int = 50,
    ):
        self.predictor = predictor
        self.w_prob = w_prob
        self.w_stale = w_stale
        self.w_unc = w_unc
        self.w_recent = w_recent
        self.epsilon = epsilon
        self.stale_cap = stale_cap
        self._rng = random.Random(seed)
        # Cold start has an independent stream so its permutation never
        # consumes draws that the established epsilon/exploration policy
        # would otherwise make after normal scheduling begins.
        self._cold_start_seed = seed
        self._cold_start_rng = random.Random(seed)

        # Anti-overexploitation & exploration parameters
        self.repeat_penalty_weight = repeat_penalty_weight
        self.repeat_penalty_start = repeat_penalty_start
        self.repeat_penalty_cap = repeat_penalty_cap
        self.exploration_bonus_weight = exploration_bonus_weight
        self.exploration_staleness_scale = exploration_staleness_scale

        # Active-band memory parameters
        self.active_confirmation_hits = active_confirmation_hits
        self.active_window = active_window
        self.active_memory_timeout = active_memory_timeout
        self.active_max_misses = active_max_misses
        self.w_active = w_active
        self.tracking_dwell_limit = tracking_dwell_limit
        self.tracking_dwell_bonus = tracking_dwell_bonus
        self.tracking_cooldown_penalty = tracking_cooldown_penalty

        # Bounded Discovery parameters
        self.discovery_interval = discovery_interval
        self.discovery_candidate_timeout = discovery_candidate_timeout

        # Internal state
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
        self._cold_start_rng = random.Random(self._cold_start_seed)

    def _select_cold_start_band(self, bands: list[int]) -> int | None:
        """Return the next band in the one-pass cold-start permutation.

        The first supplied band list is copied and shuffled as values, rather
        than synthesizing indexes, so this works for arbitrary spectrum sizes
        and non-contiguous band IDs. ``None`` signals that cold start is over.
        """
        available_bands = list(dict.fromkeys(bands))
        available_set = set(available_bands)

        if not self._cold_start_initialized:
            self._cold_start_remaining = available_bands
            self._cold_start_rng.shuffle(self._cold_start_remaining)
            self._cold_start_initialized = True
        else:
            # Keep the original pending order for bands still available.
            # Newly available, unvisited bands are shuffled using only the
            # cold-start RNG and queued after existing pending exploration.
            self._cold_start_remaining = [
                band for band in self._cold_start_remaining
                if band in available_set
            ]
            pending = set(self._cold_start_remaining)
            additions = [
                band for band in available_bands
                if band not in self._cold_start_visited and band not in pending
            ]
            self._cold_start_rng.shuffle(additions)
            self._cold_start_remaining = additions + self._cold_start_remaining

        if self._cold_start_remaining:
            chosen = self._cold_start_remaining.pop()
            self._cold_start_visited.add(chosen)
            return chosen
        return None

    # ------------------------------------------------------------------
    # ACTIVE-BAND MEMORY & DISCOVERY CANDIDATE MANAGEMENT
    # ------------------------------------------------------------------

    def _update_active_memory(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> None:
        """
        Maintains confirmed active bands and temporary discovery candidates
        using receiver observations only. Ground truth is never accessed.
        """
        # 1. Expire inactive / dead confirmed candidate bands
        for band in list(self._active_memory.keys()):
            last_hit = history_manager.last_hit_time(band)
            if last_hit is None or (current_time - last_hit) > self.active_memory_timeout:
                del self._active_memory[band]
                continue

            # Evict if excessive consecutive misses on this band
            band_hist = history_manager.get_band_history(band)
            consec_misses = 0
            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break
            if consec_misses >= self.active_max_misses:
                del self._active_memory[band]

        # 2. Expire inactive / dead temporary discovery candidates
        for band in list(self._discovery_candidates.keys()):
            if band in self._active_memory:
                del self._discovery_candidates[band]
                continue

            last_hit = history_manager.last_hit_time(band)
            if last_hit is None or (current_time - last_hit) > self.discovery_candidate_timeout:
                del self._discovery_candidates[band]
                continue

            band_hist = history_manager.get_band_history(band)
            consec_misses = 0
            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break
            if consec_misses >= self.active_max_misses:
                del self._discovery_candidates[band]

        # 3. Process candidate bands from observations
        for band in bands:
            # Do not confirm or add if recent consecutive misses indicate channel went silent
            band_hist = history_manager.get_band_history(band)
            consec_misses = 0
            for obs in reversed(band_hist):
                if not obs["detected"]:
                    consec_misses += 1
                else:
                    break
            if consec_misses >= self.active_max_misses:
                continue

            recent = history_manager.get_band_history(band, n=self.active_window)
            hits = sum(1 for obs in recent if obs["detected"])
            last_hit = history_manager.last_hit_time(band)

            if last_hit is None:
                continue

            # Confirmed active candidate: requires >= active_confirmation_hits (default 2)
            if hits >= self.active_confirmation_hits:
                if (current_time - last_hit) <= self.active_memory_timeout:
                    self._active_memory[band] = {
                        "last_hit_time": last_hit,
                        "confirmed_hits": hits,
                    }
                    if band in self._discovery_candidates:
                        del self._discovery_candidates[band]
            # Temporary discovery candidate: single hit (tentative, unconfirmed)
            elif hits >= 1:
                if (current_time - last_hit) <= self.discovery_candidate_timeout:
                    if band not in self._active_memory:
                        self._discovery_candidates[band] = {
                            "last_hit_time": last_hit,
                            "discovery_hit_count": hits,
                        }

    # ------------------------------------------------------------------
    # SCORING
    # ------------------------------------------------------------------

    def _score_band(
        self,
        band: int,
        prob: float,
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> float:
        # 1. Predicted activity probability
        score = self.w_prob * prob

        # 2. Staleness (short/medium-term gap)
        t_last = history_manager.last_scan_time(band)
        gap = (current_time - t_last) if t_last is not None else self.stale_cap
        staleness = min(gap / self.stale_cap, 1.0)
        score += self.w_stale * staleness

        # 3. Model uncertainty
        uncertainty = 0.5 - abs(prob - 0.5)
        score += self.w_unc * (uncertainty / 0.5)

        # 4. Long-term coverage / exploration bonus for unvisited / stale bands
        gap_explore = (current_time - t_last) if t_last is not None else self.exploration_staleness_scale
        exploration_ratio = min(gap_explore / self.exploration_staleness_scale, 1.0)
        exploration_bonus = self.exploration_bonus_weight * exploration_ratio
        score += exploration_bonus

        # 5. Active-band memory priority bonus & dwell lock
        if band in self._active_memory:
            score += self.w_active
            if band == self._last_scanned and self._tracking_dwell < self.tracking_dwell_limit:
                score += self.tracking_dwell_bonus

        # 6. Penalties for currently selected band
        if band == self._last_scanned:
            # Immediate rescan penalty scaled by (1.0 - prob)
            score -= self.w_recent * (1.0 - prob)

            # Progressive consecutive repeat penalty
            if self._consecutive_scans > self.repeat_penalty_start:
                excess = self._consecutive_scans - self.repeat_penalty_start
                repeat_penalty = min(
                    self.repeat_penalty_cap,
                    self.repeat_penalty_weight * (excess / 10.0),
                )
                score -= repeat_penalty

            # Multi-band tracking rotation cooldown:
            # When multiple active candidates exist and this band reached dwell limit,
            # apply rotation penalty to give other confirmed active candidates priority.
            if len(self._active_memory) >= 2 and self._tracking_dwell >= self.tracking_dwell_limit:
                score -= self.tracking_cooldown_penalty

        return score

    # ------------------------------------------------------------------
    # EXPLORATION & SELECTION
    # ------------------------------------------------------------------

    def _exploration_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
    ) -> int:
        """Pick the least-scanned band. Ties broken randomly."""
        counts = {b: history_manager.scan_count(b) for b in bands}
        min_count = min(counts.values())
        candidates = [b for b, c in counts.items() if c == min_count]
        return self._rng.choice(candidates)

    def _update_run_tracking(self, chosen: int) -> None:
        """Update consecutive selection and active tracking dwell."""
        if chosen == self._last_scanned:
            self._consecutive_scans += 1
            self._tracking_dwell += 1
        else:
            self._last_scanned = chosen
            self._consecutive_scans = 1
            self._tracking_dwell = 1

    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:
        # Cold start deliberately precedes every normal scheduling mechanism.
        # With no receiver history, model scores carry no discriminative
        # information; a seeded permutation provides broad, unbiased coverage.
        cold_start_band = self._select_cold_start_band(bands)
        if cold_start_band is not None:
            return cold_start_band

        # Update active candidate memory and temporary discovery candidates using observations so far
        self._update_active_memory(bands, history_manager, current_time)

        # Check for bounded discovery decision:
        # When fewer than 2 confirmed active candidates exist (0 or 1), and we have spent
        # (discovery_interval - 1) consecutive decisions on a confirmed active band,
        # force 1 discovery decision among bands outside confirmed active memory.
        force_discovery = False
        if len(self._active_memory) < 2 and self._consecutive_active_scans >= (self.discovery_interval - 1):
            non_active_bands = [b for b in bands if b not in self._active_memory]
            if non_active_bands:
                force_discovery = True

        if force_discovery:
            candidate_bands = [b for b in bands if b not in self._active_memory]
            if self._rng.random() < self.epsilon:
                chosen = self._exploration_band(candidate_bands, history_manager)
            else:
                predictions = self.predictor.predict_all_bands(
                    candidate_bands, history_manager, current_time
                )
                scores = {
                    band: self._score_band(band, prob, history_manager, current_time)
                    for band, prob in predictions.items()
                }
                chosen = max(scores, key=lambda b: scores[b])

            self._update_run_tracking(chosen)
            self._consecutive_active_scans = 0
            return chosen

        # Standard selection logic (outside forced discovery)
        if self._rng.random() < self.epsilon:
            chosen = self._exploration_band(bands, history_manager)
            self._update_run_tracking(chosen)
            if chosen in self._active_memory:
                self._consecutive_active_scans += 1
            else:
                self._consecutive_active_scans = 0
            return chosen

        predictions = self.predictor.predict_all_bands(
            bands, history_manager, current_time
        )
        scores = {
            band: self._score_band(band, prob, history_manager, current_time)
            for band, prob in predictions.items()
        }
        chosen = max(scores, key=lambda b: scores[b])
        self._update_run_tracking(chosen)

        if chosen in self._active_memory:
            self._consecutive_active_scans += 1
        else:
            self._consecutive_active_scans = 0

        return chosen

    # ------------------------------------------------------------------
    # DIAGNOSTICS & REASONING
    # ------------------------------------------------------------------

    def explain_decision(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
        top_n: int = 5,
    ) -> None:
        """Print score breakdown for top N bands. Useful for debugging."""
        self._update_active_memory(bands, history_manager, current_time)
        predictions = self.predictor.predict_all_bands(
            bands, history_manager, current_time
        )
        scored = []
        for band, prob in predictions.items():
            score = self._score_band(band, prob, history_manager, current_time)
            t_last = history_manager.last_scan_time(band)
            gap = (current_time - t_last) if t_last is not None else self.stale_cap
            staleness = min(gap / self.stale_cap, 1.0)
            uncertainty = 0.5 - abs(prob - 0.5)

            gap_explore = (current_time - t_last) if t_last is not None else self.exploration_staleness_scale
            explore_bonus = self.exploration_bonus_weight * min(gap_explore / self.exploration_staleness_scale, 1.0)

            active_bonus = self.w_active if band in self._active_memory else 0.0

            repeat_penalty = 0.0
            cooldown_penalty = 0.0
            if band == self._last_scanned:
                if self._consecutive_scans > self.repeat_penalty_start:
                    excess = self._consecutive_scans - self.repeat_penalty_start
                    repeat_penalty = min(self.repeat_penalty_cap, self.repeat_penalty_weight * (excess / 10.0))
                if len(self._active_memory) >= 2 and self._tracking_dwell >= self.tracking_dwell_limit:
                    cooldown_penalty = self.tracking_cooldown_penalty

            scored.append({
                "band": band, "score": score, "prob": prob,
                "staleness": staleness, "uncertainty": uncertainty,
                "explore_bonus": explore_bonus, "active_bonus": active_bonus,
                "repeat_penalty": repeat_penalty + cooldown_penalty,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        active_list = sorted(list(self._active_memory.keys()))
        discovery_list = sorted(list(self._discovery_candidates.keys()))
        print(f"\nScheduler decision at t={current_time} (last={self._last_scanned}, dwell={self._tracking_dwell}, consec_active={self._consecutive_active_scans}, active_memory={active_list}, discovery_candidates={discovery_list}):")
        print(f"  {'Band':<6} {'Score':<8} {'P(act)':<8} {'Stale':<8} {'Uncert':<8} {'ExpBon':<8} {'ActBon':<8} {'Penalties':<8}")
        print(f"  {'-'*72}")
        for i, row in enumerate(scored[:top_n]):
            marker = " <- CHOSEN" if i == 0 else ""
            print(
                f"  {row['band']:<6} {row['score']:<8.3f} "
                f"{row['prob']:<8.3f} {row['staleness']:<8.3f} "
                f"{row['uncertainty']:<8.3f} {row['explore_bonus']:<8.3f} "
                f"{row['active_bonus']:<8.3f} {row['repeat_penalty']:<8.3f}{marker}"
            )
