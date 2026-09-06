def get_global_observations(history_manager) -> list[dict]:
    """Reconstruct all stored observations in chronological order."""
    observations = [
        observation
        for band in history_manager.observed_bands()
        for observation in history_manager.get_band_history(band)
    ]
    return sorted(observations, key=lambda observation: observation["time"])
