# backend/prediction/history_manager.py

from collections import defaultdict, deque


class BandHistoryManager:
    """
    Stores and retrieves per-band observation history.
    This is the memory of the ML system.
    Every observation from Person 1 flows through here first.
    """

    def __init__(self, max_history_per_band: int = 200):
        self.max_history = max_history_per_band
        self._history: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=self.max_history)
        )
        self.current_time: int = 0

    def ingest(self, observation: dict) -> None:
        """
        Receive one observation from Person 1 and store it.
        Required keys: time, band, detected
        Optional keys: power, pulse_width, pri
        """
        band = observation["band"]
        self._history[band].append(observation)
        self.current_time = max(self.current_time, observation["time"])

    def get_band_history(self, band: int, n: int = None) -> list[dict]:
        """Return last n observations for this band. All if n is None."""
        obs_list = list(self._history[band])
        if n is not None:
            obs_list = obs_list[-n:]
        return obs_list

    def last_hit_time(self, band: int) -> int | None:
        """Time of most recent HIT on this band. None if never hit."""
        for obs in reversed(list(self._history[band])):
            if obs["detected"]:
                return obs["time"]
        return None

    def last_scan_time(self, band: int) -> int | None:
        """Time of most recent scan (hit or miss). None if never scanned."""
        history = list(self._history[band])
        if not history:
            return None
        return history[-1]["time"]

    def hit_ratio(self, band: int, n: int = 10) -> float:
        """Hits / total scans over last n scans. 0.0 if never scanned."""
        recent = list(self._history[band])[-n:]
        if not recent:
            return 0.0
        hits = sum(1 for obs in recent if obs["detected"])
        return hits / len(recent)

    def scan_count(self, band: int) -> int:
        """Total scans of this band."""
        return len(self._history[band])

    def observed_bands(self) -> list[int]:
        """All bands scanned at least once."""
        return [band for band, hist in self._history.items() if len(hist) > 0]

    def time_since_last_hit(self, band: int) -> int | None:
        """Steps since last hit. None if never hit."""
        t = self.last_hit_time(band)
        if t is None:
            return None
        return self.current_time - t

    def time_since_last_scan(self, band: int) -> int | None:
        """Steps since last scan. None if never scanned."""
        t = self.last_scan_time(band)
        if t is None:
            return None
        return self.current_time - t
