# backend/prediction/feature_engineering.py

from history_manager import BandHistoryManager

UNKNOWN_TIME     = 9999.0
UNKNOWN_POWER    = 0.0
UNKNOWN_ACTIVITY = 0.0


class FeatureExtractor:
    """
    Converts per-band observation history into a flat feature vector.
    All features computed from receiver observations only.
    No ground truth. No emitter IDs. No future information.
    """

    def __init__(self, window_size: int = 10, n_lags: int = 3):
        self.window_size = window_size
        self.n_lags = n_lags

    def extract(
        self,
        band: int,
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> dict[str, float]:
        """
        Extract features for a single band at current_time.
        Returns dict of feature_name -> float. No None values.
        """
        features = {}
        recent = history_manager.get_band_history(band, n=self.window_size)

        # --- Group 1: Aggregate activity statistics ---
        hits   = [obs for obs in recent if obs["detected"]]
        misses = [obs for obs in recent if not obs["detected"]]
        total  = len(recent)

        features["recent_hit_count"]  = float(len(hits))
        features["recent_miss_count"] = float(len(misses))
        features["hit_ratio"]         = float(len(hits) / total) if total > 0 else 0.0

        # --- Group 2: Recency ---
        t_last_hit  = history_manager.last_hit_time(band)
        t_last_scan = history_manager.last_scan_time(band)

        features["time_since_last_hit"] = (
            float(current_time - t_last_hit)
            if t_last_hit is not None else UNKNOWN_TIME
        )
        features["time_since_last_scan"] = (
            float(current_time - t_last_scan)
            if t_last_scan is not None else UNKNOWN_TIME
        )

        # --- Group 3: Confidence ---
        features["scan_count"] = float(history_manager.scan_count(band))

        # --- Group 4: Signal quality ---
        all_history = history_manager.get_band_history(band)
        last_power  = UNKNOWN_POWER
        for obs in reversed(all_history):
            if obs["detected"] and "power" in obs:
                last_power = float(obs["power"])
                break
        features["last_power"] = last_power

        # --- Group 5: Lag features ---
        for lag_index in range(1, self.n_lags + 1):
            feature_name = f"lag_{lag_index}"
            position     = -lag_index
            if len(all_history) >= lag_index:
                obs = all_history[position]
                features[feature_name] = 1.0 if obs["detected"] else 0.0
            else:
                features[feature_name] = UNKNOWN_ACTIVITY

        return features

    def feature_names(self) -> list[str]:
        """Ordered list of feature names produced by extract()."""
        base = [
            "recent_hit_count",
            "recent_miss_count",
            "hit_ratio",
            "time_since_last_hit",
            "time_since_last_scan",
            "scan_count",
            "last_power",
        ]
        lags = [f"lag_{i}" for i in range(1, self.n_lags + 1)]
        return base + lags

    def extract_all_bands(
        self,
        bands: list[int],
        history_manager: BandHistoryManager,
        current_time: int,
    ) -> dict[int, dict[str, float]]:
        """Extract features for multiple bands at once. Returns {band: features}."""
        return {
            band: self.extract(band, history_manager, current_time)
            for band in bands
        }
