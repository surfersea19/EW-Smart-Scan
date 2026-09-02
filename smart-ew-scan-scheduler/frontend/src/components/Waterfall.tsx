import { useSimulationStore } from "../store/simulationStore";

/**
 * Simulated waterfall: each column is one tick, each row bucket is a band
 * range. This is NOT a physical spectrum analyzer -- it's a visualization
 * of simulated receiver activity, labeled as such.
 */
export function Waterfall() {
  const history = useSimulationStore((s) => s.history);
  const numBands = useSimulationStore((s) => s.scenario.num_bands);
  const nextBand = useSimulationStore((s) => s.nextBand);

  const rowCount = 20;
  const bandToRow = (band: number) =>
    Math.min(rowCount - 1, Math.floor((band / numBands) * rowCount));

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide">
          Live Spectrum / Waterfall
        </h3>
        <span className="text-xs text-slate-500 font-mono">
          simulated activity — not a physical spectrogram
        </span>
      </div>
      <div className="flex flex-col-reverse gap-[2px]" style={{ height: 260 }}>
        {Array.from({ length: rowCount }).map((_, row) => (
          <div key={row} className="flex gap-[2px] flex-1">
            {history.length === 0 && (
              <div className="flex-1 bg-slate-900/40 rounded-sm" />
            )}
            {history.map((point, i) => {
              const isActiveRow = point.band !== null && bandToRow(point.band) === row;
              const isNextRow = nextBand !== null && bandToRow(nextBand) === row;
              let cls = "flex-1 rounded-sm bg-slate-900/40";
              if (isActiveRow) {
                cls = point.detected
                  ? "flex-1 rounded-sm bg-hit"
                  : "flex-1 rounded-sm bg-slate-600";
              } else if (isNextRow && i === history.length - 1) {
                cls = "flex-1 rounded-sm bg-accent/40 animate-pulse";
              }
              return <div key={i} className={cls} />;
            })}
          </div>
        ))}
      </div>
      <div className="flex justify-between text-xs text-slate-500 font-mono mt-2">
        <span>B0</span>
        <span>time →</span>
        <span>B{numBands}</span>
      </div>
    </div>
  );
}
