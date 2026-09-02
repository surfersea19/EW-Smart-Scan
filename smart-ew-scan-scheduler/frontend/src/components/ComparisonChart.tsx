import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import { api } from "../services/api";
import type { ComparisonResult } from "../types/simulation";

const STRATEGY_LABELS: Record<string, string> = {
  sequential: "Sequential",
  random: "Random",
  smart_ml: "Smart ML",
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

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide">
          Baseline vs Smart
        </h3>
        <button
          onClick={runComparison}
          disabled={loading}
          className="text-xs font-mono bg-accent/20 text-accent px-3 py-1 rounded hover:bg-accent/30 disabled:opacity-40"
        >
          {loading ? "running..." : "run comparison"}
        </button>
      </div>

      {!result && (
        <div className="text-slate-500 text-sm font-mono">
          Run the same scenario under each strategy to compare.
        </div>
      )}

      {result && (
        <table className="w-full font-mono text-sm">
          <thead>
            <tr className="text-slate-500 text-left">
              <th className="pb-2">Strategy</th>
              <th className="pb-2">Detection</th>
              <th className="pb-2">Avg Intercept</th>
              <th className="pb-2">Intercept Rate</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(result).map(([strategy, m]) => (
              <tr key={strategy} className="border-t border-slate-800">
                <td className="py-2 text-slate-200">
                  {STRATEGY_LABELS[strategy] ?? strategy}
                </td>
                <td className="py-2">{Math.round(m.detection_probability * 100)}%</td>
                <td className="py-2">{m.avg_intercept_time}s</td>
                <td className="py-2">{Math.round(m.intercept_rate * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
