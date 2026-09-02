# backend/evaluation/metrics.py

from dataclasses import dataclass, field


@dataclass
class SimulationResult:
    """
    All raw data and computed metrics from one scheduler run.
    """
    scheduler_name:     str
    total_steps:        int  = 0
    total_hits:         int  = 0
    total_misses:       int  = 0
    total_active_steps: int  = 0
    missed_bursts:      int  = 0

    # Raw log: list of {time, band, detected, ground_truth_active}
    decision_log:    list = field(default_factory=list)

    # Intercept time for each burst that was caught
    intercept_times: list = field(default_factory=list)

    # ----------------------------------------------------------------
    # COMPUTED METRICS (properties — never stored, always derived)
    # ----------------------------------------------------------------

    @property
    def pd(self) -> float:
        """Probability of Detection."""
        if self.total_active_steps == 0:
            return 0.0
        hits_on_active = sum(
            1 for d in self.decision_log
            if d["detected"] and d["ground_truth_active"]
        )
        return hits_on_active / self.total_active_steps

    @property
    def pfa(self) -> float:
        """Probability of False Alarm."""
        if self.total_steps == 0:
            return 0.0
        false_alarms = sum(
            1 for d in self.decision_log
            if d["detected"] and not d["ground_truth_active"]
        )
        return false_alarms / self.total_steps

    @property
    def intercept_rate(self) -> float:
        """Hits / total scans."""
        if self.total_steps == 0:
            return 0.0
        return self.total_hits / self.total_steps

    @property
    def avg_intercept_time(self) -> float:
        """Mean time steps from burst start to first detection."""
        if not self.intercept_times:
            return float("inf")
        return sum(self.intercept_times) / len(self.intercept_times)

    @property
    def scan_efficiency(self) -> float:
        """Fraction of scans that caught a real active transmission."""
        useful = sum(
            1 for d in self.decision_log
            if d["detected"] and d["ground_truth_active"]
        )
        if self.total_steps == 0:
            return 0.0
        return useful / self.total_steps

    @property
    def bursts_intercepted(self) -> int:
        return len(self.intercept_times)

    # ----------------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"Scheduler          : {self.scheduler_name}",
            f"Total steps        : {self.total_steps}",
            f"Total hits         : {self.total_hits}",
            f"Total active steps : {self.total_active_steps}",
            f"Pd                 : {self.pd:.3f}",
            f"Pfa                : {self.pfa:.4f}",
            f"Intercept rate     : {self.intercept_rate:.3f}",
            f"Avg intercept time : {self.avg_intercept_time:.2f} steps",
            f"Scan efficiency    : {self.scan_efficiency:.3f}",
            f"Bursts intercepted : {self.bursts_intercepted}",
            f"Missed bursts      : {self.missed_bursts}",
        ]
        return "\n".join(lines)
