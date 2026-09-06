import { useSimulationStore } from "../store/simulationStore";

interface HeaderProps {
  activeTab: "live" | "intelligence";
  setActiveTab: (tab: "live" | "intelligence") => void;
}

export function Header({ activeTab, setActiveTab }: HeaderProps) {
  const connected = useSimulationStore((s) => s.connected);
  const running = useSimulationStore((s) => s.running);
  const completed = useSimulationStore((s) => s.completed);
  const time = useSimulationStore((s) => s.time);
  const currentBand = useSimulationStore((s) => s.currentBand);
  const knowledgeStatus = useSimulationStore((s) => s.knowledgeStatus);

  return (
    <header
      className="border-b border-[#1e2638] bg-[#050816] px-6 py-3.5 sticky top-0 z-40 shadow-md"
      style={{ backgroundColor: "#050816" }}
    >
      <div className="max-w-[1520px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Left: System Title & Subtitle */}
        <div className="flex items-baseline gap-4">
          <h1 className="text-base font-bold text-textPrimary tracking-tight">
            SMART SCAN
          </h1>
          <span className="text-xs text-textSecondary hidden sm:inline">
            AI-Driven Adaptive Spectrum Surveillance
          </span>
        </div>

        {/* Center: Live Instrumentation State & High-Contrast Knowledge Badge */}
        <div className="flex flex-wrap items-center gap-5 text-xs text-textSecondary font-mono">
          {/* Status Indicator */}
          <div className="flex items-center gap-1.5">
            <span
              className={`w-2 h-2 rounded-full ${
                running
                  ? "bg-success"
                  : completed
                  ? "bg-accent"
                  : "bg-warning"
              }`}
            />
            <span className="text-textPrimary font-semibold">
              {running ? "LIVE" : completed ? "COMPLETE" : "PAUSED"}
            </span>
          </div>

          {/* Time Readout */}
          <div className="flex items-center gap-1">
            <span className="text-textMuted">t =</span>
            <span className="text-textPrimary font-semibold">{time}s</span>
          </div>

          {/* Band Readout */}
          <div className="flex items-center gap-1">
            <span className="text-textMuted">Band</span>
            <span className="text-textPrimary font-semibold">
              {currentBand !== null ? `B${currentBand}` : "—"}
            </span>
          </div>

          {/* High-Contrast Knowledge Status Badge */}
          <div className="flex items-center">
            {knowledgeStatus === "warm" ? (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#064e3b]/80 border border-emerald-500/80 text-emerald-300 font-mono text-[11px] font-bold shadow-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="tracking-wide">KNOWLEDGE: WARM START</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded bg-[#1e293b]/90 border border-slate-600 text-slate-300 font-mono text-[11px] font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
                <span className="tracking-wide text-slate-300">KNOWLEDGE: COLD START</span>
              </div>
            )}
          </div>

          {/* Connection */}
          {!connected && (
            <span className="text-danger text-[11px] font-semibold">
              FEED OFFLINE
            </span>
          )}
        </div>

        {/* Right: Navigation Switcher [ SYSTEM INTELLIGENCE ] [ LIVE OPERATIONS ] */}
        <nav className="flex items-center gap-1 bg-[#0b1220] p-1 rounded border border-[#1e2638]">
          <button
            type="button"
            onClick={() => setActiveTab("intelligence")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === "intelligence"
                ? "bg-[#161d2e] text-textPrimary font-semibold border border-accent/40"
                : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            SYSTEM INTELLIGENCE
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("live")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              activeTab === "live"
                ? "bg-[#161d2e] text-textPrimary font-semibold border border-accent/40"
                : "text-textSecondary hover:text-textPrimary"
            }`}
          >
            LIVE OPERATIONS
          </button>
        </nav>
      </div>
    </header>
  );
}
