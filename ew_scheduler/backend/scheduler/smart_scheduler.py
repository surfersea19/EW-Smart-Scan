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
    ML-driven scheduler.

    Combines predicted activity probability with:
      - staleness  (how long since last scan)
      - uncertainty (how unsure the model is)
      - recent scan penalty (avoid rescanning immediately)
      - epsilon-greedy exploration

    All weights are tunable.
    """

    def __init__(
        self,
        predictor: Predictor,
        w_prob:    float = 0.50,
        w_stale:   float = 0.25,
        w_unc:     float = 0.15,
        w_recent:  float = 0.10,
        epsilon:   float = 0.15,
        stale_cap: int   = 50,
        seed:      int   = None,
    ):
        self.predictor      = predictor
        self.w_prob         = w_prob
        self.w_stale        = w_stale
        self.w_unc          = w_unc
        self.w_recent       = w_recent
        self.epsilon        = epsilon
        self.stale_cap      = stale_cap
        self._rng           = random.Random(seed)
        self._last_scanned  = None

    def reset(self) -> None:
        self._last_scanned = None

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
        score = self.w_prob * prob

        t_last    = history_manager.last_scan_time(band)
        gap       = (current_time - t_last) if t_last is not None else self.stale_cap
        staleness = min(gap / self.stale_cap, 1.0)
        score    += self.w_stale * staleness

        uncertainty = 0.5 - abs(prob - 0.5)
        score      += self.w_unc * (uncertainty / 0.5)

        if band == self._last_scanned:
            score -= self.w_recent

        return score

    # ------------------------------------------------------------------
    # EXPLORATION
    # ------------------------------------------------------------------

    def _exploration_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
    ) -> int:
        """Pick the least-scanned band. Ties broken randomly."""
        counts    = {b: history_manager.scan_count(b) for b in bands}
        min_count = min(counts.values())
        candidates = [b for b, c in counts.items() if c == min_count]
        return self._rng.choice(candidates)

    # ------------------------------------------------------------------
    # MAIN DECISION
    # ------------------------------------------------------------------

    def select_band(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> int:
        if self._rng.random() < self.epsilon:
            chosen = self._exploration_band(bands, history_manager)
            self._last_scanned = chosen
            return chosen

        predictions = self.predictor.predict_all_bands(
            bands, history_manager, current_time
        )
        scores = {
            band: self._score_band(band, prob, history_manager, current_time)
            for band, prob in predictions.items()
        }
        chosen = max(scores, key=lambda b: scores[b])
        self._last_scanned = chosen
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
        """Print score breakdown for top N bands. Useful for debugging."""
        predictions = self.predictor.predict_all_bands(
            bands, history_manager, current_time
        )
        scored = []
        for band, prob in predictions.items():
            score = self._score_band(band, prob, history_manager, current_time)
            t_last    = history_manager.last_scan_time(band)
            gap       = (current_time - t_last) if t_last is not None else self.stale_cap
            staleness = min(gap / self.stale_cap, 1.0)
            uncertainty = 0.5 - abs(prob - 0.5)
            scored.append({
                "band": band, "score": score, "prob": prob,
                "staleness": staleness, "uncertainty": uncertainty,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        print(f"\nScheduler decision breakdown at t={current_time}:")
        print(f"  {'Band':<6} {'Score':<8} {'P(act)':<8} {'Stale':<8} {'Uncert':<8}")
        print(f"  {'-'*45}")
        for i, row in enumerate(scored[:top_n]):
            marker = " <- CHOSEN" if i == 0 else ""
            print(
                f"  {row['band']:<6} {row['score']:<8.3f} "
                f"{row['prob']:<8.3f} {row['staleness']:<8.3f} "
                f"{row['uncertainty']:<8.3f}{marker}"
            )
