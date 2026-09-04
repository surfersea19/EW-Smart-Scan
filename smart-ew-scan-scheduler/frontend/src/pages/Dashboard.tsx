import { useEffect, useRef } from "react";
import { Waterfall } from "../components/Waterfall";
import { ReceiverStatus } from "../components/ReceiverStatus";
import { PredictionPanel } from "../components/PredictionPanel";
import { SchedulerDecision } from "../components/SchedulerDecision";
import { PredictedActivityPanel } from "../components/PredictedActivityPanel";
import { MetricsPanel } from "../components/MetricsPanel";
import { ComparisonChart } from "../components/ComparisonChart";
import { SimulationControls } from "../components/SimulationControls";
import { SimulationSocket } from "../services/websocket";
import { api } from "../services/api";
import { useSimulationStore } from "../store/simulationStore";

export function Dashboard() {
  const applyDelta = useSimulationStore((s) => s.applyDelta);
  const setConnected = useSimulationStore((s) => s.setConnected);
  const setScenario = useSimulationStore((s) => s.setScenario);
  const setRunning = useSimulationStore((s) => s.setRunning);
  const setCompleted = useSimulationStore((s) => s.setCompleted);
  const socketRef = useRef<SimulationSocket | null>(null);

  useEffect(() => {
    const socket = new SimulationSocket(applyDelta, setConnected);
    socket.connect();
    socketRef.current = socket;
    return () => socket.disconnect();
  }, [applyDelta, setConnected]);

  useEffect(() => {
    // BUG FIX: the store's default scenario.strategy ("smart_ml") is
    // just a local assumption -- it can differ from what the backend
    // actually initialized with (e.g. it falls back to "sequential" for
    // this process if no trained model exists yet; see
    // services/orchestrator.py get_orchestrator()). Fetching the real
    // state once on mount means the two can never silently disagree:
    // the UI always reflects what's actually running, not a guess.
    api
      .getState()
      .then((state) => {
        setScenario(state.scenario);
        setRunning(state.running);
        setCompleted(state.completed);
      })
      .catch((err) => console.error("Failed to fetch initial backend state", err));
  }, [setScenario, setRunning, setCompleted]);

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto">
      <header className="mb-6">
        <h1 className="text-2xl font-mono font-bold text-slate-100">
          SMART EW SCAN SCHEDULER
        </h1>
        <p className="text-sm text-slate-500 font-mono">
          ML-based Electronic Support receiver scheduler — live simulation
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <Waterfall />
          <div className="grid grid-cols-2 gap-4">
            <ReceiverStatus />
            <SchedulerDecision />
          </div>
          <ComparisonChart />
        </div>

        <div className="space-y-4">
          <SimulationControls />
          <PredictionPanel />
          <PredictedActivityPanel />
          <MetricsPanel />
        </div>
      </div>
    </div>
  );
}
