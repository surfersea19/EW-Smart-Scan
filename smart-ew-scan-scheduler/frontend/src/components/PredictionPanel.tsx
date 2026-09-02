import { useSimulationStore } from "../store/simulationStore";

export function PredictionPanel() {
  const predictions = useSimulationStore((s) => s.predictions);

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        AI Prediction
      </h3>
      {predictions.length === 0 && (
        <div className="text-slate-500 text-sm font-mono">No predictions yet</div>
      )}
      <div className="space-y-2">
        {predictions.map((p) => (
          <div key={p.band} className="flex items-center gap-2 font-mono text-sm">
            <span className="w-10 text-slate-300">B{p.band}</span>
            <div className="flex-1 bg-slate-800 rounded-full h-3 overflow-hidden">
              <div
                className="bg-accent h-3 rounded-full transition-all duration-300"
                style={{ width: `${Math.round(p.probability * 100)}%` }}
              />
            </div>
            <span className="w-10 text-right text-slate-400">
              {Math.round(p.probability * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
