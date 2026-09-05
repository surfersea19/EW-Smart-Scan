# backend/prediction/periodicity_detector.py
"""
Standalone, testable periodicity and temporal behavior analyzer.

Operates purely on receiver observation history (past detections up to time t).
Zero access to simulator state, ground truth, or future observations.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Sequence


UNKNOWN_TIME = 9999.0


@dataclass(frozen=True)
class PeriodicityResult:
    """Immutable result of temporal/periodicity analysis for a single band."""

    is_periodic: bool
    estimated_period: float
    period_regularity: float
    confidence: float
    last_hit_time: Optional[int]
    expected_next_time: Optional[int]
    time_to_next: float
    temporal_proximity: float
    recurrence_score: float

    @classmethod
    def default(cls, last_hit_time: Optional[int] = None) -> PeriodicityResult:
        return cls(
            is_periodic=False,
            estimated_period=0.0,
            period_regularity=0.0,
            confidence=0.0,
            last_hit_time=last_hit_time,
            expected_next_time=None,
            time_to_next=UNKNOWN_TIME,
            temporal_proximity=0.0,
            recurrence_score=0.0,
        )


class PeriodicityDetector:
    """
    Detects periodic recurrence and predicts activity timing from receiver hit history.

    Features & capabilities:
      1. Burst onset clustering (distinguishes dwell inside burst from inter-burst cycle).
      2. Fundamental period estimation using median interval and sub-harmonic consensus.
      3. Regularity / jitter scoring via normalized coefficient of variation.
      4. Safe handling of sparse scans and missed intermediate cycles.
      5. Smooth bell-shaped temporal proximity to expected active window.
      6. Robust cold-start / sparse data defaults (no NaNs, no division by zero).
    """

    def __init__(
        self,
        min_hits_for_period: int = 2,
        cluster_gap: int = 1,
        max_period: int = 250,
        min_period: float = 2.0,
        regularity_threshold: float = 0.70,
        min_confidence: float = 0.35,
    ):
        self.min_hits_for_period = min_hits_for_period
        self.cluster_gap = cluster_gap
        self.max_period = max_period
        self.min_period = min_period
        self.regularity_threshold = regularity_threshold
        self.min_confidence = min_confidence

    def _cluster_burst_onsets(self, hit_times: Sequence[int]) -> list[int]:
        """
        Group consecutive hit timestamps that are part of the same burst
        into a single burst onset timestamp.
        """
        if not hit_times:
            return []

        sorted_hits = sorted(dict.fromkeys(hit_times))
        onsets = [sorted_hits[0]]
        prev = sorted_hits[0]

        for t in sorted_hits[1:]:
            if t - prev > self.cluster_gap:
                onsets.append(t)
            prev = t

        return onsets

    def _estimate_fundamental_period(self, intervals: list[int]) -> tuple[float, float, float]:
        """
        Estimate fundamental period T, regularity R, and confidence C from inter-onset intervals.
        Returns: (estimated_period, regularity, confidence)
        """
        if not intervals:
            return 0.0, 0.0, 0.0

        n = len(intervals)

        if n == 1:
            raw_period = float(intervals[0])
            if self.min_period <= raw_period <= self.max_period:
                # Single interval: regularity is 1.0 (zero variance), but moderate confidence
                return raw_period, 1.0, 0.40
            return 0.0, 0.0, 0.0

        sorted_ints = sorted(intervals)
        min_interval = sorted_ints[0]
        candidate_t = float(min_interval)

        # Check harmonic consistency (in case intermediate scans were missed, e.g. [10, 20, 10])
        if candidate_t >= self.min_period:
            harmonics = [max(1, round(x / candidate_t)) for x in intervals]
            errors = [abs(x - k * candidate_t) / candidate_t for x, k in zip(intervals, harmonics)]
            all_harmonic = all(e <= 0.15 for e in errors)

            if all_harmonic:
                normalized = [x / k for x, k in zip(intervals, harmonics)]
                mean_t = sum(normalized) / len(normalized)
                variance = sum((x - mean_t) ** 2 for x in normalized) / len(normalized)
                std_dev = math.sqrt(variance)
                cv = std_dev / max(mean_t, 1.0)
                regularity = math.exp(-2.0 * min(cv, 2.0))
                total_cycles = sum(harmonics)
                confidence = min(1.0, total_cycles / 3.0) * (1.0 - (sum(errors) / len(errors)))
                return mean_t, regularity, confidence

        # Direct interval analysis (no harmonic assumption)
        mean_raw = sum(intervals) / n
        variance_raw = sum((x - mean_raw) ** 2 for x in intervals) / n
        std_dev_raw = math.sqrt(variance_raw)
        cv_raw = std_dev_raw / max(mean_raw, 1.0)
        regularity_raw = math.exp(-2.0 * min(cv_raw, 2.0))
        confidence_raw = min(1.0, n / 3.0) * regularity_raw

        med_interval = (
            float(sorted_ints[n // 2])
            if n % 2 == 1
            else float(sorted_ints[n // 2 - 1] + sorted_ints[n // 2]) / 2.0
        )

        if self.min_period <= med_interval <= self.max_period:
            return float(med_interval), regularity_raw, confidence_raw

        return 0.0, regularity_raw, 0.0

    def analyze_hits(self, hit_times: Sequence[int], current_time: int) -> PeriodicityResult:
        """
        Analyze a list of historical hit timestamps for a single band at current_time.
        Strictly filters out any timestamp > current_time to prevent future leakage.
        """
        valid_hits = [t for t in hit_times if t <= current_time]
        if not valid_hits:
            return PeriodicityResult.default(last_hit_time=None)

        last_hit = max(valid_hits)

        # 1. Cluster hits into distinct burst onsets
        onsets = self._cluster_burst_onsets(valid_hits)
        if len(onsets) < self.min_hits_for_period:
            return PeriodicityResult.default(last_hit_time=last_hit)

        last_onset = onsets[-1]

        # 2. Compute inter-onset intervals
        intervals = [onsets[i] - onsets[i - 1] for i in range(1, len(onsets))]
        period, regularity, confidence = self._estimate_fundamental_period(intervals)

        if period < self.min_period or period > self.max_period:
            return PeriodicityResult(
                is_periodic=False,
                estimated_period=0.0,
                period_regularity=float(round(regularity, 4)),
                confidence=float(round(confidence, 4)),
                last_hit_time=last_hit,
                expected_next_time=None,
                time_to_next=UNKNOWN_TIME,
                temporal_proximity=0.0,
                recurrence_score=float(round(regularity * confidence, 4)),
            )

        is_periodic = (
            regularity >= self.regularity_threshold
            and confidence >= self.min_confidence
        )

        # 3. Timing and Proximity calculation anchored to last burst onset
        elapsed = max(0, current_time - last_onset)
        phase_offset = elapsed % period

        # Distance to nearest periodic cycle point (past or future)
        dist_to_cycle = min(phase_offset, period - phase_offset)

        # Time remaining until next expected cycle onset
        time_to_next = (period - phase_offset) % period
        if phase_offset == 0 and elapsed > 0:
            time_to_next = 0.0

        expected_next_time = (
            current_time if time_to_next == 0.0
            else int(round(current_time + time_to_next))
        )

        # Smooth bell-shaped proximity in [0.0, 1.0]
        sigma = max(1.0, 0.15 * period)
        proximity = math.exp(-(dist_to_cycle ** 2) / (2.0 * (sigma ** 2)))

        recurrence_score = float(regularity * confidence)

        return PeriodicityResult(
            is_periodic=is_periodic,
            estimated_period=float(round(period, 2)),
            period_regularity=float(round(regularity, 4)),
            confidence=float(round(confidence, 4)),
            last_hit_time=last_hit,
            expected_next_time=expected_next_time,
            time_to_next=float(round(time_to_next, 2)),
            temporal_proximity=float(round(proximity, 4)),
            recurrence_score=float(round(recurrence_score, 4)),
        )

    def analyze_band(
        self,
        history_manager,
        band: int,
        current_time: int,
    ) -> PeriodicityResult:
        """Convenience method extracting past hits from BandHistoryManager."""
        all_obs = history_manager.get_band_history(band)
        hit_times = [
            obs["time"] for obs in all_obs
            if obs.get("detected") and obs.get("time") is not None and obs["time"] <= current_time
        ]
        return self.analyze_hits(hit_times, current_time)
