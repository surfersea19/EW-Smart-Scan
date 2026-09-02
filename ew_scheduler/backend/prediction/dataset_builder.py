# backend/prediction/dataset_builder.py

import pandas as pd
from history_manager import BandHistoryManager
from feature_engineering import FeatureExtractor


class DatasetBuilder:
    """
    Converts a full observation log + ground truth into a
    supervised training dataset.

    Features: computed from receiver observations only (no leakage).
    Labels:   computed from ground truth activity windows.
    """

    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        horizon: int = 5,
        min_history: int = 3,
    ):
        self.fe          = feature_extractor
        self.horizon     = horizon
        self.min_history = min_history

    def _compute_label(
        self,
        band: int,
        current_time: int,
        ground_truth: dict[int, list[int]],
    ) -> int:
        """
        1 if band has ground truth activity in (current_time, current_time+horizon].
        0 otherwise.
        """
        active_times  = set(ground_truth.get(band, []))
        future_window = range(current_time + 1, current_time + self.horizon + 1)
        for t in future_window:
            if t in active_times:
                return 1
        return 0

    def build(
        self,
        observation_log: list[dict],
        ground_truth: dict[int, list[int]],
        all_bands: list[int],
    ) -> pd.DataFrame:
        """
        Replay observation log chronologically.
        At each scan event, extract features and compute label.

        Returns DataFrame with columns [band, time, *features, label].
        """
        hm   = BandHistoryManager(max_history_per_band=200)
        rows = []

        for obs in observation_log:
            current_time = obs["time"]
            band         = obs["band"]

            hm.ingest(obs)

            if hm.scan_count(band) < self.min_history:
                continue

            features = self.fe.extract(band, hm, current_time)
            label    = self._compute_label(band, current_time, ground_truth)

            row = {"band": band, "time": current_time}
            row.update(features)
            row["label"] = label
            rows.append(row)

        if not rows:
            raise ValueError(
                "No training rows created. "
                "Check observation_log and ground_truth are populated "
                "and min_history is not too high."
            )

        return pd.DataFrame(rows)

    def time_split(
        self,
        df: pd.DataFrame,
        train_frac: float = 0.70,
        val_frac: float   = 0.15,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Chronological train / val / test split.
        NEVER use random split on time-series data.
        """
        assert train_frac + val_frac < 1.0

        t_min   = df["time"].min()
        t_max   = df["time"].max()
        t_range = t_max - t_min

        t_train_end = t_min + int(t_range * train_frac)
        t_val_end   = t_min + int(t_range * (train_frac + val_frac))

        train = df[df["time"] <= t_train_end].copy()
        val   = df[(df["time"] > t_train_end) & (df["time"] <= t_val_end)].copy()
        test  = df[df["time"] > t_val_end].copy()

        print(f"Train: {len(train)} rows  (t={t_min} to t={t_train_end})")
        print(f"Val:   {len(val)} rows  (t={t_train_end+1} to t={t_val_end})")
        print(f"Test:  {len(test)} rows  (t={t_val_end+1} to t={t_max})")
        print(f"Label balance (train): {train['label'].mean():.3f} positive rate")

        return train, val, test
