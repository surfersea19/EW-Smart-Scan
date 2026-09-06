export function MissionIdentity() {
  return (
    <div className="py-4 text-center select-none">
      <div className="inline-flex items-center gap-3 px-4 py-1.5 rounded-full bg-[#0b1220]/50 border border-borderMuted/40">
        <span className="w-2 h-2 rounded-full bg-accent" />
        <span className="text-xs font-bold tracking-widest text-textPrimary font-mono">
          SMART SCAN
        </span>
        <span className="text-borderMuted font-mono">|</span>
        <span className="text-[10px] tracking-wider text-textSecondary font-mono uppercase">
          AI-Driven Adaptive Spectrum Surveillance
        </span>
      </div>
    </div>
  );
}
