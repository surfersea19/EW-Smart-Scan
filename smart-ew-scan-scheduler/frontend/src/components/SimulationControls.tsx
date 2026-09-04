import { useSimulationStore } from "../store/simulationStore";
import { api } from "../services/api";
import type { NoiseLevel, Strategy } from "../types/simulation";

export function SimulationControls() {
  const scenario = useSimulationStore((s) => s.scenario);
  const setScenario = useSimulationStore((s) => s.setScenario);
  const playbackSpeed = useSimulationStore((s) => s.playbackSpeed);
  const setPlaybackSpeed = useSimulationStore((s) => s.setPlaybackSpeed);
  const running = useSimulationStore((s) => s.running);
  const setRunning = useSimulationStore((s) => s.setRunning);
  const completed = useSimulationStore((s) => s.completed);
  const setCompleted = useSimulationStore((s) => s.setCompleted);
  const resetHistory = useSimulationStore((s) => s.resetHistory);
  const connected = useSimulationStore((s) => s.connected);

  const update = (patch: Partial<typeof scenario>) => {
    const next = { ...scenario, ...patch };
    setScenario(next);
    setRunning(false);
    setCompleted(false);
    // reset picks up the new scenario immediately
    api.reset(next).catch(console.error);
    resetHistory();
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    api.setSpeed(speed).catch(console.error);
  };

  const handleStart = async () => {
    try {
      const res = await api.start();
      setRunning(res.running);
      setCompleted(res.completed);
    } catch (err) {
      console.error("Failed to start simulation", err);
    }
  };

  const handlePause = async () => {
    try {
      const res = await api.stop();
      setRunning(res.running);
      setCompleted(res.completed);
    } catch (err) {
      console.error("Failed to pause simulation", err);
      setRunning(false);
    }
  };

  const handleReset = async () => {
    try {
      await api.reset(scenario);
      resetHistory();
      setRunning(false);
      setCompleted(false);
    } catch (err) {
      console.error("Failed to reset simulation", err);
    }
  };

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-mono text-slate-400 uppercase tracking-wide">
          Scenario Controls
        </h3>
        <div className="flex items-center gap-2">
          {completed && (
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-accent/20 text-accent font-semibold">
              COMPLETED
            </span>
          )}
          <span
            className={`text-xs font-mono px-2 py-0.5 rounded-full ${
              connected ? "bg-hit/20 text-hit" : "bg-miss/20 text-miss"
            }`}
          >
            {connected ? "connected" : "disconnected"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 font-mono text-sm mb-4">
        <label className="flex flex-col gap-1">
          Bands
          <input
            type="number"
            className="bg-slate-800 rounded px-2 py-1"
            value={scenario.num_bands}
            onChange={(e) => update({ num_bands: Number(e.target.value) })}
          />
        </label>
        <label className="flex flex-col gap-1">
          Emitters
          <input
            type="number"
            className="bg-slate-800 rounded px-2 py-1"
            value={scenario.num_emitters}
            onChange={(e) => update({ num_emitters: Number(e.target.value) })}
          />
        </label>
        <label className="flex flex-col gap-1">
          Noise
          <select
            className="bg-slate-800 rounded px-2 py-1"
            value={scenario.noise_level}
            onChange={(e) => update({ noise_level: e.target.value as NoiseLevel })}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          Strategy
          <select
            className="bg-slate-800 rounded px-2 py-1"
            value={scenario.strategy}
            onChange={(e) => update({ strategy: e.target.value as Strategy })}
          >
            <option value="smart_ml">Smart ML</option>
            <option value="sequential">Sequential</option>
            <option value="random">Random</option>
          </select>
        </label>
        <div className="flex flex-col gap-1 col-span-2">
          <span className="text-slate-300">Speed</span>
          <div className="flex gap-2">
            {[1, 5, 10].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => handleSpeedChange(s)}
                className={`flex-1 py-1 rounded font-mono text-sm font-semibold transition-all ${
                  playbackSpeed === s
                    ? "bg-accent text-slate-950 font-bold"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleStart}
          disabled={running || completed}
          className="flex-1 bg-hit/90 hover:bg-hit text-slate-950 font-mono font-bold py-2 rounded disabled:opacity-40"
        >
          START
        </button>
        <button
          onClick={handlePause}
          disabled={!running}
          className="flex-1 bg-slate-700 hover:bg-slate-600 font-mono font-bold py-2 rounded disabled:opacity-40"
        >
          PAUSE
        </button>
        <button
          onClick={handleReset}
          className="flex-1 bg-miss/90 hover:bg-miss text-slate-950 font-mono font-bold py-2 rounded"
        >
          RESET
        </button>
      </div>
    </div>
  );
}
