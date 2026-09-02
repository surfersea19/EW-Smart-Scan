import { useEffect, useRef } from "react";
import { Waterfall } from "../components/Waterfall";
import { ReceiverStatus } from "../components/ReceiverStatus";
import { PredictionPanel } from "../components/PredictionPanel";
import { SchedulerDecision } from "../components/SchedulerDecision";
import { EmitterPanel } from "../components/EmitterPanel";
import { MetricsPanel } from "../components/MetricsPanel";
import { ComparisonChart } from "../components/ComparisonChart";
import { SimulationControls } from "../components/SimulationControls";
import { SimulationSocket } from "../services/websocket";
import { useSimulationStore } from "../store/simulationStore";

export function Dashboard() {
  const applyDelta = useSimulationStore((s) => s.applyDelta);
  const setConnected = useSimulationStore((s) => s.setConnected);
  const socketRef = useRef<SimulationSocket | null>(null);

  useEffect(() => {
    const socket = new SimulationSocket(applyDelta, setConnected);
    socket.connect();
    socketRef.current = socket;
    return () => socket.disconnect();
  }, [applyDelta, setConnected]);

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
          <EmitterPanel />
          <MetricsPanel />
        </div>
      </div>
    </div>
  );
}
