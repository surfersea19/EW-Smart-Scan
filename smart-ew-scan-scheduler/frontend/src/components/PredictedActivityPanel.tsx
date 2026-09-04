import { useSimulationStore } from "../store/simulationStore";

/**
 * Previously "EmitterPanel" / "Emitter Tracks". Renamed because Person
 * 2's predictor does not perform persistent multi-target tracking -- it
 * produces a fresh per-band probability every tick with no track-ID
 * continuity. This shows the current top predicted bands, not tracked
 * entities (see types/simulation.ts PredictedActivity for the full
 * rationale).
 */
export function PredictedActivityPanel() {
  const predictedActivity = useSimulationStore((s) => s.predictedActivity);

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        Predicted Activity
      </h3>
      {predictedActivity.length === 0 && (
        <div className="text-slate-500 text-sm font-mono">No predictions yet</div>
      )}
      <div className="space-y-2">
        {predictedActivity.map((p) => (
          <div
            key={p.rank}
            className="flex justify-between items-center bg-slate-800/50 rounded px-3 py-2 font-mono text-sm"
          >
            <div>
              <div className="text-slate-200">B{p.band}</div>
              <div className="text-xs text-slate-500">rank #{p.rank} this tick</div>
            </div>
            <div className="text-accent">{Math.round(p.probability * 100)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
