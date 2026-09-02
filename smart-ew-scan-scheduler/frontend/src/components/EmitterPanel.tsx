import { useSimulationStore } from "../store/simulationStore";

export function EmitterPanel() {
  const tracks = useSimulationStore((s) => s.tracks);

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        Emitter Tracks
      </h3>
      {tracks.length === 0 && (
        <div className="text-slate-500 text-sm font-mono">No active tracks</div>
      )}
      <div className="space-y-2">
        {tracks.map((t) => (
          <div
            key={t.track_id}
            className="flex justify-between items-center bg-slate-800/50 rounded px-3 py-2 font-mono text-sm"
          >
            <div>
              <div className="text-slate-200">{t.track_id}</div>
              <div className="text-xs text-slate-500">
                {t.emitter_type} · {t.current_band !== null ? `B${t.current_band}` : "—"}
              </div>
            </div>
            <div className="text-accent">{Math.round(t.confidence * 100)}%</div>
          </div>
        ))}
      </div>
    </div>
  );
}
