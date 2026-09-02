# backend/evaluation/comparison.py

import pandas as pd
from metrics import SimulationResult


def compare_results(results: list[SimulationResult]) -> pd.DataFrame:
    """
    Build a comparison table from multiple SimulationResult objects.
    Each row is one scheduler. Columns are key metrics.
    """
    rows = []
    for r in results:
        rows.append({
            "Scheduler":          r.scheduler_name,
            "Pd":                 round(r.pd, 3),
            "Pfa":                round(r.pfa, 4),
            "Intercept Rate":     round(r.intercept_rate, 3),
            "Avg Intercept Time": round(r.avg_intercept_time, 2),
            "Scan Efficiency":    round(r.scan_efficiency, 3),
            "Bursts Intercepted": r.bursts_intercepted,
            "Missed Bursts":      r.missed_bursts,
            "Total Hits":         r.total_hits,
        })

    df = pd.DataFrame(rows).set_index("Scheduler")
    return df


def print_comparison(df: pd.DataFrame) -> None:
    print("\n" + "=" * 65)
    print("SCHEDULER COMPARISON")
    print("=" * 65)
    print(df.to_string())
    print("=" * 65)

    # Higher is better
    for col in ["Pd", "Intercept Rate", "Scan Efficiency", "Bursts Intercepted"]:
        if col in df.columns:
            best = df[col].idxmax()
            print(f"  Best {col:<22}: {best}  ({df.loc[best, col]})")

    # Lower is better
    for col in ["Avg Intercept Time", "Missed Bursts", "Pfa"]:
        if col in df.columns and not df[col].isnull().all():
            best = df[col].idxmin()
            print(f"  Best {col:<22}: {best}  ({df.loc[best, col]})")
