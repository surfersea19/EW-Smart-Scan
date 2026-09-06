import { useState, useEffect, useRef } from "react";
import { Dashboard } from "./pages/Dashboard";
import { SystemIntelligence } from "./pages/SystemIntelligence";
import { Header } from "./components/Header";
import { SimulationSocket } from "./services/websocket";
import { api } from "./services/api";
import { useSimulationStore } from "./store/simulationStore";

export default function App() {
  const [activeTab, setActiveTab] = useState<"live" | "intelligence">("intelligence");

  const applyDelta = useSimulationStore((s) => s.applyDelta);
  const setConnected = useSimulationStore((s) => s.setConnected);
  const setScenario = useSimulationStore((s) => s.setScenario);
  const setRunning = useSimulationStore((s) => s.setRunning);
  const setCompleted = useSimulationStore((s) => s.setCompleted);
  const setKnowledgeStatus = useSimulationStore((s) => s.setKnowledgeStatus);
  const socketRef = useRef<SimulationSocket | null>(null);

  // Maintain single WebSocket connection across both pages
  useEffect(() => {
    const socket = new SimulationSocket(applyDelta, setConnected);
    socket.connect();
    socketRef.current = socket;
    return () => socket.disconnect();
  }, [applyDelta, setConnected]);

  // Sync initial backend state on mount
  useEffect(() => {
    api
      .getState()
      .then((state) => {
        setScenario(state.scenario);
        setRunning(state.running);
        setCompleted(state.completed);
        setKnowledgeStatus(state.knowledge_status);
      })
      .catch((err) =>
        console.error("Failed to fetch initial backend state", err)
      );
  }, [setScenario, setRunning, setCompleted, setKnowledgeStatus]);

  return (
    <div className="min-h-screen bg-canvas text-textPrimary flex flex-col">
      {/* Engineering Header */}
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Page Viewport */}
      <main className="flex-1">
        {activeTab === "live" ? <Dashboard /> : <SystemIntelligence />}
      </main>

      {/* Engineering Footer */}
      <footer className="border-t border-borderMuted py-3 px-6 text-xs font-mono text-textMuted">
        <div className="max-w-[1520px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            <span>SMART SCAN — Cognitive Spectrum Surveillance</span>
            <span className="text-borderSubtle mx-2">|</span>
            <span className="text-textSecondary">EW Research Prototype</span>
          </div>
          <div>
            Observation-Only Decision Engine · Strict Ground-Truth Isolation
          </div>
        </div>
      </footer>
    </div>
  );
}
