import { useSimulationStore } from "../store/simulationStore";

export function SchedulerDecision() {
  const nextBand = useSimulationStore((s) => s.nextBand);
  const reason = useSimulationStore((s) => s.schedulerReason);

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide mb-3">
        Scheduler Decision
      </h3>
      <div className="font-mono">
        {/* Labeled "Band Chosen" rather than "Next Scan": Person 1's real
            SimulationEngine decides and scans a band in the same atomic
            step, so there's no separate "upcoming" band to preview --
            this is the band this tick's decision picked and just scanned. */}
        <div className="text-xs text-slate-500">Band Chosen</div>
        <div className="text-3xl text-accent font-bold">
          {nextBand !== null ? `B${nextBand}` : "—"}
        </div>
        {reason && (
          <div className="text-xs text-slate-400 mt-2 italic">{reason}</div>
        )}
      </div>
    </div>
  );
}
