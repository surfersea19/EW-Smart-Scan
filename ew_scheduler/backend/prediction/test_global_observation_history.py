from global_history import get_global_observations
from history_manager import BandHistoryManager


def test_global_observation_reconstruction_is_chronological():
    hm = BandHistoryManager()

    observations = [
        {"time": 1, "band": 10, "detected": True},
        {"time": 2, "band": 12, "detected": True},
        {"time": 3, "band": 14, "detected": True},
        {"time": 4, "band": 12, "detected": False},
    ]

    for observation in observations:
        hm.ingest(observation)

    reconstructed = [
        (o["time"], o["band"], o["detected"])
        for o in get_global_observations(hm)
    ]

    assert reconstructed == [
        (1, 10, True),
        (2, 12, True),
        (3, 14, True),
        (4, 12, False),
    ]
