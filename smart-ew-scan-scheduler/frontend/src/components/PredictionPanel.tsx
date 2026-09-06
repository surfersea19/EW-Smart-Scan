import { useSimulationStore } from "../store/simulationStore";

export function PredictionPanel() {
  const predictions = useSimulationStore((s) => s.predictions);
  const modelName = useSimulationStore((s) => s.scenario.model_name);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          ML Activity Probabilities
        </h2>
        <span className="text-[11px] font-mono text-textMuted capitalize">
          {modelName.replace("_", " ")}
        </span>
      </div>

      {predictions.length === 0 ? (
        <div className="text-xs font-mono text-textMuted py-2">
          Awaiting observation history...
        </div>
      ) : (
        <div className="space-y-2 font-mono text-xs">
          {predictions.map((p, idx) => {
            const probPct = Math.round(p.probability * 100);
            return (
              <div key={p.band} className="flex items-center gap-2">
                <span className="w-5 text-[11px] text-textMuted font-medium">
                  #{idx + 1}
                </span>
                <span className="w-10 font-semibold text-textPrimary">
                  B{p.band}
                </span>
                <div className="flex-1 bg-surface rounded h-1.5 overflow-hidden border border-borderMuted">
                  <div
                    className="bg-accent h-1.5 rounded transition-all duration-300"
                    style={{ width: `${probPct}%` }}
                  />
                </div>
                <span className="w-10 text-right text-textSecondary text-[11px]">
                  {probPct}%
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
