import { useSimulationStore } from "../store/simulationStore";

export function PredictedActivityPanel() {
  const predictedActivity = useSimulationStore((s) => s.predictedActivity);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          Ranked Candidate Targets
        </h2>
        <span className="text-[11px] font-mono text-textMuted">Per-Tick Top</span>
      </div>

      {predictedActivity.length === 0 ? (
        <div className="text-xs font-mono text-textMuted py-2">
          No targets ranked yet
        </div>
      ) : (
        <div className="space-y-1.5 font-mono text-xs">
          {predictedActivity.map((p) => {
            const probPct = Math.round(p.probability * 100);
            return (
              <div
                key={p.rank}
                className="flex items-center justify-between py-1 px-2 rounded bg-surface border border-borderMuted text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-textMuted">#{p.rank}</span>
                  <span className="font-semibold text-textPrimary">Band B{p.band}</span>
                </div>
                <span className="text-accent text-[11px] font-semibold">
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
