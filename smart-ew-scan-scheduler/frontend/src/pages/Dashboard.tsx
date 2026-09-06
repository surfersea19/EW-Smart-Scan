import { Waterfall } from "../components/Waterfall";
import { ReceiverStatus } from "../components/ReceiverStatus";
import { SchedulerDecision } from "../components/SchedulerDecision";
import { SimulationControls } from "../components/SimulationControls";
import { PredictionPanel } from "../components/PredictionPanel";
import { PredictedActivityPanel } from "../components/PredictedActivityPanel";
import { ComparisonChart } from "../components/ComparisonChart";
import { MissionIdentity } from "../components/MissionIdentity";

export function Dashboard() {
  return (
    <div className="p-6 max-w-[1560px] mx-auto space-y-6 font-sans">
      {/* ========================================================================= */}
      {/* 1. TOP / MAIN AREA: WATERFALL (DOMINANT LEFT) + SIDEBAR CONTROLS (RIGHT)  */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left / Large Area (8 of 12 columns = ~67% width) */}
        <div className="lg:col-span-8 space-y-5">
          {/* Dominant Spectrum Waterfall */}
          <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
            <Waterfall />
          </div>

          {/* Directly Underneath Waterfall: Receiver Telemetry (Left) | AI Decision (Right) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
              <ReceiverStatus />
            </div>
            <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
              <SchedulerDecision />
            </div>
          </div>
        </div>

        {/* Right / Narrow Sidebar (4 of 12 columns = ~33% width) */}
        <div className="lg:col-span-4 space-y-4">
          {/* Scenario Controls */}
          <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
            <SimulationControls />
          </div>

          {/* ML Activity Probabilities (Restored) */}
          <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
            <PredictionPanel />
          </div>

          {/* Ranked Candidate Targets (Restored) */}
          <div className="bg-[#0b1220] p-4 rounded border border-[#1e2638]">
            <PredictedActivityPanel />
          </div>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* 2. BASELINE VS SMART COMPARISON (NUMERICAL TABLE)                         */}
      {/* ========================================================================= */}
      <div className="bg-[#0b1220] p-5 rounded border border-[#1e2638]">
        <ComparisonChart />
      </div>

      {/* ========================================================================= */}
      {/* 3. MINIMAL SMART SCAN BRANDING                                           */}
      {/* ========================================================================= */}
      <MissionIdentity />
    </div>
  );
}