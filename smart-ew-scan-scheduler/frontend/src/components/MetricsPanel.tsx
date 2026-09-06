import { useSimulationStore } from "../store/simulationStore";

export function MetricsPanel() {
  const m = useSimulationStore((s) => s.metrics);

  const pdPct = Math.round(m.detection_probability * 100);
  const pfaPct = Math.round(m.false_alarm_probability * 100);
  const intPct = Math.round(m.intercept_rate * 100);

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          Performance Summary
        </h2>
        <span className="text-[11px] font-mono text-textMuted">
          {m.ticks_run} Ticks
        </span>
      </div>

      {/* Numerical Telemetry Grid */}
      <div className="grid grid-cols-2 gap-3 font-mono text-xs">
        <div>
          <div className="text-[10px] text-textMuted uppercase">
            Detection Prob (Pd)
          </div>
          <div className="text-lg font-bold text-textPrimary mt-0.5">
            {pdPct}%
          </div>
        </div>

        <div>
          <div className="text-[10px] text-textMuted uppercase">
            Intercept Rate
          </div>
          <div className="text-lg font-bold text-textPrimary mt-0.5">
            {intPct}%
          </div>
        </div>

        <div>
          <div className="text-[10px] text-textMuted uppercase">
            Avg Intercept Time
          </div>
          <div className="text-lg font-bold text-textPrimary mt-0.5">
            {m.avg_intercept_time.toFixed(1)}s
          </div>
        </div>

        <div>
          <div className="text-[10px] text-textMuted uppercase">
            False Alarm Prob
          </div>
          <div className="text-lg font-bold text-textPrimary mt-0.5">
            {pfaPct}%
          </div>
        </div>
      </div>

      <div className="pt-2 border-t border-borderMuted flex items-center justify-between text-[11px] font-mono text-textSecondary">
        <span>Hits: <strong className="text-success">{m.hits}</strong></span>
        <span>Misses: <strong className="text-danger">{m.misses}</strong></span>
        <span>Total: <strong className="text-textPrimary">{m.hits + m.misses}</strong></span>
      </div>
    </div>
  );
}
