import { useSimulationStore } from "../store/simulationStore";

export function SchedulerDecision() {
  const nextBand = useSimulationStore((s) => s.nextBand);
  const reason = useSimulationStore((s) => s.schedulerReason);
  const behavior = useSimulationStore((s) => s.behavior);
  const behaviorConfidence = useSimulationStore((s) => s.behaviorConfidence);
  const strategy = useSimulationStore((s) => s.scenario.strategy);

  const behaviorLabel = behavior
    ? behavior.toUpperCase()
    : "UNKNOWN";

  const confidencePercent = Math.round(
    Math.max(0, Math.min(1, behaviorConfidence)) * 100
  );

  return (
    <div className="space-y-4">
      {/* Section Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          AI Scan Decision
        </h2>
        <span className="text-[11px] font-mono text-textMuted">
          {strategy === "smart_ml" ? "Smart ML" : strategy.toUpperCase()}
        </span>
      </div>

      {/* Primary Target Decision Readout */}
      <div>
        <div className="text-[11px] font-mono text-textMuted uppercase">
          Selected Target
        </div>
        <div className="text-4xl font-mono font-bold text-accent tracking-tight mt-0.5">
          {nextBand !== null ? `B${nextBand}` : "—"}
        </div>
        <div className="text-xs text-textSecondary mt-0.5">
          Next frequency band scheduled for dwell
        </div>
      </div>

      {/* Behavior Intelligence Readout */}
      <div className="grid grid-cols-2 gap-4 pt-2 border-t border-borderMuted">
        <div>
          <div className="text-[11px] font-mono text-textMuted uppercase">
            Inferred Behavior
          </div>
          <div className="text-sm font-semibold text-textPrimary mt-0.5">
            {behaviorLabel}
          </div>
        </div>

        <div>
          <div className="text-[11px] font-mono text-textMuted uppercase">
            Confidence
          </div>
          <div className="text-sm font-semibold text-textPrimary mt-0.5">
            {confidencePercent}%
          </div>
        </div>
      </div>

      {/* Decision Rationale */}
      <div className="pt-2 border-t border-borderMuted">
        <div className="text-[11px] font-mono text-textMuted uppercase mb-1">
          Rationale
        </div>
        <p className="text-xs text-textSecondary leading-relaxed">
          {reason ? (
            reason
          ) : (
            <span className="text-textMuted italic">
              ML activity probability + temporal periodicity + staleness exploration
            </span>
          )}
        </p>
      </div>
    </div>
  );
}