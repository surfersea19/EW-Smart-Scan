import { useSimulationStore } from "../store/simulationStore";

export function ReceiverStatus() {
  const currentBand = useSimulationStore((s) => s.currentBand);
  const detected = useSimulationStore((s) => s.detected);
  const power = useSimulationStore((s) => s.power);
  const running = useSimulationStore((s) => s.running);
  const completed = useSimulationStore((s) => s.completed);
  const metrics = useSimulationStore((s) => s.metrics);

  const status = running ? "Scanning" : completed ? "Complete" : "Idle";
  const result =
    detected === null ? "—" : detected ? "HIT" : "MISS";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          Receiver Telemetry
        </h2>
        <span className="text-[11px] font-mono text-textMuted">
          {status} · {metrics.ticks_run} Ticks
        </span>
      </div>

      {/* Grid of Readouts */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 font-mono text-xs">
        {/* Readout 1: Receiver Band */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Receiver Band
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-0.5">
            {currentBand !== null ? `B${currentBand}` : "—"}
          </div>
          <div className="text-[10px] text-textSecondary">{status}</div>
        </div>

        {/* Readout 2: Signal Power */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Measured Power
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-0.5">
            {power !== null ? `${power.toFixed(1)} dBm` : "— dBm"}
          </div>
          <div className="text-[10px] text-textSecondary">100 MHz BW</div>
        </div>

        {/* Readout 3: Detection Outcome */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Detection
          </div>
          <div
            className={`text-2xl font-bold mt-0.5 ${
              detected === true
                ? "text-success"
                : detected === false
                ? "text-danger"
                : "text-textMuted"
            }`}
          >
            {result}
          </div>
          <div className="text-[10px] text-textSecondary">
            {metrics.hits} Hits / {metrics.misses} Misses
          </div>
        </div>

        {/* Readout 4: Detection Probability */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Detection Prob (Pd)
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-0.5">
            {(metrics.detection_probability * 100).toFixed(2)}%
          </div>
          <div className="text-[10px] text-textSecondary">Cumulative Pd</div>
        </div>

        {/* Readout 5: Intercept Rate */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Intercept Rate
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-0.5">
            {(metrics.intercept_rate * 100).toFixed(2)}%
          </div>
          <div className="text-[10px] text-textSecondary">Burst Capture</div>
        </div>

        {/* Readout 6: MTTI */}
        <div>
          <div className="text-[10px] text-textMuted uppercase tracking-wider">
            Avg Intercept Time
          </div>
          <div className="text-2xl font-bold text-textPrimary mt-0.5">
            {metrics.avg_intercept_time.toFixed(1)}s
          </div>
          <div className="text-[10px] text-textSecondary">Mean Intercept Latency</div>
        </div>
      </div>
    </div>
  );
}
