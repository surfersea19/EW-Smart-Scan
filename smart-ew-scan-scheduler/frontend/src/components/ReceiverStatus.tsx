import { useSimulationStore } from "../store/simulationStore";

export function ReceiverStatus() {
  const currentBand = useSimulationStore((s) => s.currentBand);
  const detected = useSimulationStore((s) => s.detected);
  const power = useSimulationStore((s) => s.power);
  const running = useSimulationStore((s) => s.running);

  const status = running ? "SCANNING" : "IDLE";
  const result = detected === null ? "—" : detected ? "HIT" : "MISS";
  const resultColor =
    detected === null ? "text-slate-400" : detected ? "text-hit" : "text-miss";

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        Current Receiver
      </h3>
      <div className="grid grid-cols-2 gap-3 font-mono">
        <div>
          <div className="text-xs text-slate-500">Band</div>
          <div className="text-2xl text-accent">
            {currentBand !== null ? `B${currentBand}` : "—"}
          </div>
        </div>
        <div>
          <div className="text-xs text-slate-500">Status</div>
          <div className="text-lg">{status}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">Result</div>
          <div className={`text-2xl font-bold ${resultColor}`}>{result}</div>
        </div>
        <div>
          <div className="text-xs text-slate-500">Signal Strength</div>
          <div className="text-lg">{power !== null ? `${power} dBm` : "—"}</div>
        </div>
      </div>
    </div>
  );
}
