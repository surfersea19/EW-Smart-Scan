import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import { api } from "../services/api";
import type { ComparisonResult, Metrics } from "../types/simulation";

const STRATEGY_LABELS: Record<string, string> = {
  sequential: "Sequential Scan (0→180)",
  random: "Random Uniform Scan",
  smart_ml: "Smart ML Scheduler",
};

export function ComparisonChart() {
  const scenario = useSimulationStore((s) => s.scenario);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(false);

  const runComparison = async () => {
    setLoading(true);
    try {
      const res = await api.runComparison(scenario);
      setResult(res);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const strategies = [
    { key: "sequential", label: "Sequential" },
    { key: "random", label: "Random" },
    { key: "smart_ml", label: "Smart ML" },
  ];

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
            Baseline vs Smart Comparison
          </h2>
          <span className="text-[11px] text-textSecondary">
            Comparative evaluation across identical scenario ({scenario.duration}s duration)
          </span>
        </div>

        <button
          type="button"
          onClick={runComparison}
          disabled={loading}
          className="text-xs font-mono font-medium px-3 py-1 rounded bg-[#0f1420] hover:bg-[#161d2e] border border-accent/40 text-textPrimary disabled:opacity-40 transition-colors shadow-sm"
        >
          {loading ? "Running benchmark..." : "Run Head-to-Head"}
        </button>
      </div>

      {!result && !loading && (
        <div className="text-xs font-mono text-textMuted py-3 bg-[#0b1220]/50 rounded p-3 border border-borderMuted/60">
          Click "Run Head-to-Head" to evaluate Sequential, Random, and Smart ML on the active scenario seed.
        </div>
      )}

      {loading && (
        <div className="text-xs font-mono text-accent py-3 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          <span>Executing 3-way comparative benchmark...</span>
        </div>
      )}

      {result && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs font-mono border-collapse border border-borderMuted rounded overflow-hidden">
            <thead>
              <tr className="bg-[#0b1220] border-b border-borderMuted text-[11px]">
                <th className="text-left py-2.5 px-3 text-textMuted font-semibold uppercase">
                  Strategy
                </th>
                <th className="text-right py-2.5 px-3 text-textMuted font-semibold uppercase">
                  Detection Pd
                </th>
                <th className="text-right py-2.5 px-3 text-textMuted font-semibold uppercase">
                  Intercept Rate
                </th>
                <th className="text-right py-2.5 px-3 text-textMuted font-semibold uppercase">
                  Avg Intercept Time
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-borderMuted/70 bg-surface">
              {strategies.map((strat) => {
                const m = result[strat.key];
                const isSmart = strat.key === "smart_ml";
                const pdVal = m ? `${(m.detection_probability * 100).toFixed(2)}%` : "—";
                const intVal = m ? `${(m.intercept_rate * 100).toFixed(2)}%` : "—";
                const mttiVal =
                  m && m.avg_intercept_time > 0
                    ? `${m.avg_intercept_time.toFixed(1)} s`
                    : "N/A";
                return (
                  <tr
                    key={strat.key}
                    className={`transition-colors ${
                      isSmart
                        ? "bg-accent/5 font-semibold hover:bg-accent/10"
                        : "hover:bg-surfaceHover/50"
                    }`}
                  >
                    <td
                      className={`py-2.5 px-3 ${
                        isSmart ? "text-accent font-bold" : "text-textPrimary"
                      }`}
                    >
                      {STRATEGY_LABELS[strat.key] || strat.label}
                    </td>
                    <td
                      className={`text-right py-2.5 px-3 ${
                        isSmart ? "text-accent font-bold" : "text-textSecondary"
                      }`}
                    >
                      {pdVal}
                    </td>
                    <td
                      className={`text-right py-2.5 px-3 ${
                        isSmart ? "text-success font-bold" : "text-textSecondary"
                      }`}
                    >
                      {intVal}
                    </td>
                    <td
                      className={`text-right py-2.5 px-3 ${
                        isSmart ? "text-accent font-bold" : "text-textSecondary"
                      }`}
                    >
                      {mttiVal}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
