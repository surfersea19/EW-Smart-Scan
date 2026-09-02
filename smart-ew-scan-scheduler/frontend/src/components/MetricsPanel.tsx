import { useSimulationStore } from "../store/simulationStore";

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-800/50 rounded px-3 py-2">
      <div className="text-xs text-slate-500 font-mono">{label}</div>
      <div className="text-xl font-mono text-slate-100">{value}</div>
    </div>
  );
}

export function MetricsPanel() {
  const m = useSimulationStore((s) => s.metrics);

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        Performance
      </h3>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Detection Prob." value={`${Math.round(m.detection_probability * 100)}%`} />
        <Stat label="False Alarm Prob." value={`${Math.round(m.false_alarm_probability * 100)}%`} />
        <Stat label="Avg Intercept Time" value={`${m.avg_intercept_time}s`} />
        <Stat label="Intercept Rate" value={`${Math.round(m.intercept_rate * 100)}%`} />
      </div>
    </div>
  );
}
