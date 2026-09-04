"""
scheduler_service.py -- REAL Person 2 integration.

Builds a SchedulerAdapter (integration/scheduler_adapter.py) wrapping a
real Person 2 scheduler, ready to be passed as P1's SimulationEngine's
`scheduler=` argument.
"""
from integration.repo_paths import register_p1_p2_on_path
from integration.scheduler_adapter import SchedulerAdapter
from services.prediction_service import get_predictor, PredictorNotAvailableError

register_p1_p2_on_path()

from sequential_scheduler import SequentialScheduler  # noqa: E402
from random_scheduler import RandomScheduler  # noqa: E402
from smart_scheduler import SmartScheduler  # noqa: E402

__all__ = ["build_scheduler_adapter", "PredictorNotAvailableError"]


def build_scheduler_adapter(strategy: str) -> SchedulerAdapter:
    """
    strategy: "sequential" | "random" | "smart_ml"

    Raises PredictorNotAvailableError (propagated from prediction_service)
    if "smart_ml" is requested and no trained model exists yet -- this is
    NOT caught/retrained here, per the "no silent retraining" requirement.
    """
    if strategy == "sequential":
        p2_scheduler = SequentialScheduler()
    elif strategy == "random":
        p2_scheduler = RandomScheduler()
    elif strategy == "smart_ml":
        predictor = get_predictor()  # raises PredictorNotAvailableError if untrained
        p2_scheduler = SmartScheduler(predictor)
    else:
        raise ValueError(f"Unknown strategy: {strategy!r}")

    return SchedulerAdapter(p2_scheduler)
