import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import { api } from "../services/api";
import type { NoiseLevel, Strategy, ScenarioConfig } from "../types/simulation";

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
  const setKnowledgeStatus = useSimulationStore((s) => s.setKnowledgeStatus);

  const [isBusy, setIsBusy] = useState(false);

  const syncBackendState = async () => {
    try {
      const state = await api.getState();
      setScenario(state.scenario);
      setRunning(state.running);
      setCompleted(state.completed);
      setKnowledgeStatus(state.knowledge_status);
    } catch (err) {
      console.error("Failed to sync backend state", err);
    }
  };

  const update = async (patch: Partial<ScenarioConfig>) => {
    const next = { ...scenario, ...patch };

    setScenario(next);
    setRunning(false);
    setCompleted(false);

    try {
      setIsBusy(true);
      await api.reset(next);
      resetHistory();
      await syncBackendState();
    } catch (err) {
      console.error("Failed to update simulation scenario", err);
    } finally {
      setIsBusy(false);
    }
  };

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed);
    api.setSpeed(speed).catch(console.error);
  };

  const handleStart = async () => {
    try {
      setIsBusy(true);
      const res = await api.start();
      setRunning(res.running);
      setCompleted(res.completed);
    } catch (err) {
      console.error("Failed to start simulation", err);
    } finally {
      setIsBusy(false);
    }
  };

  const handlePause = async () => {
    try {
      setIsBusy(true);
      const res = await api.stop();
      setRunning(res.running);
      setCompleted(res.completed);
    } catch (err) {
      console.error("Failed to pause simulation", err);
      setRunning(false);
    } finally {
      setIsBusy(false);
    }
  };

  const handleReset = async () => {
    try {
      setIsBusy(true);
      await api.reset(scenario);
      resetHistory();
      setRunning(false);
      setCompleted(false);
      await syncBackendState();
    } catch (err) {
      console.error("Failed to reset simulation", err);
    } finally {
      setIsBusy(false);
    }
  };

  // Reusable input and select style classes guaranteeing high contrast in dark mode
  const fieldClass =
    "w-full bg-[#0b1220] text-[#e5e7eb] border border-[#334155] rounded px-2.5 py-1 text-xs outline-none focus:border-accent disabled:bg-[#0f172a] disabled:text-[#94a3b8] disabled:border-[#334155] disabled:opacity-100 disabled:cursor-not-allowed";

  const optionStyle = {
    backgroundColor: "#0b1220",
    color: "#e5e7eb",
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-borderMuted pb-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
          Scenario Controls
        </h2>
        <span className="text-[11px] font-mono text-textMuted">
          100 MHz / Band · 0–18 GHz
        </span>
      </div>

      {/* Action Trigger Buttons */}
      <div className="grid grid-cols-3 gap-2">
        <button
          type="button"
          onClick={handleStart}
          disabled={running || completed || isBusy || !connected}
          className="py-1.5 px-3 rounded text-xs font-semibold bg-success/20 text-success border border-success/40 hover:bg-success/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          START
        </button>

        <button
          type="button"
          onClick={handlePause}
          disabled={!running || isBusy}
          className="py-1.5 px-3 rounded text-xs font-semibold bg-warning/20 text-warning border border-warning/40 hover:bg-warning/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          PAUSE
        </button>

        <button
          type="button"
          onClick={handleReset}
          disabled={isBusy}
          className="py-1.5 px-3 rounded text-xs font-semibold bg-surface hover:bg-surfaceHover text-textPrimary border border-borderMuted disabled:opacity-30 transition-colors"
        >
          RESET
        </button>
      </div>

      {/* Technical Form Controls Grid */}
      <div className="grid grid-cols-2 gap-3 text-xs font-mono">
        {/* Strategy */}
        <div className="col-span-2 space-y-1">
          <label className="text-[11px] text-textMuted block">Strategy</label>
          <select
            value={scenario.strategy}
            disabled={running}
            onChange={(e) => update({ strategy: e.target.value as Strategy })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          >
            <option value="smart_ml" style={optionStyle}>
              Smart ML (Active Memory + Periodic + Behavior)
            </option>
            <option value="sequential" style={optionStyle}>
              Sequential Scan (Baseline)
            </option>
            <option value="random" style={optionStyle}>
              Random Scan (Baseline)
            </option>
          </select>
        </div>

        {/* Bands & Emitters */}
        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Bands</label>
          <input
            type="number"
            min={10}
            max={500}
            disabled={running}
            value={scenario.num_bands}
            onChange={(e) => update({ num_bands: Number(e.target.value) })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          />
        </div>

        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Emitters</label>
          <input
            type="number"
            min={1}
            max={50}
            disabled={running}
            value={scenario.num_emitters}
            onChange={(e) => update({ num_emitters: Number(e.target.value) })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          />
        </div>

        {/* Noise & Model */}
        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Noise Level</label>
          <select
            value={scenario.noise_level}
            disabled={running}
            onChange={(e) => update({ noise_level: e.target.value as NoiseLevel })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          >
            <option value="low" style={optionStyle}>
              Low (High SNR)
            </option>
            <option value="medium" style={optionStyle}>
              Medium
            </option>
            <option value="high" style={optionStyle}>
              High
            </option>
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Model</label>
          <select
            value={scenario.model_name}
            disabled={running}
            onChange={(e) =>
              update({
                model_name: e.target.value as ScenarioConfig["model_name"],
              })
            }
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          >
            <option value="random_forest" style={optionStyle}>
              Random Forest
            </option>
            <option value="xgboost" style={optionStyle}>
              XGBoost
            </option>
            <option value="logistic" style={optionStyle}>
              Logistic Regression
            </option>
          </select>
        </div>

        {/* Seeds */}
        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Scenario Seed</label>
          <input
            type="number"
            disabled={running}
            value={scenario.scenario_seed}
            onChange={(e) => update({ scenario_seed: Number(e.target.value) })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          />
        </div>

        <div className="space-y-1">
          <label className="text-[11px] text-textMuted block">Scheduler Seed</label>
          <input
            type="number"
            disabled={running}
            value={scenario.scheduler_seed}
            onChange={(e) => update({ scheduler_seed: Number(e.target.value) })}
            className={fieldClass}
            style={{
              backgroundColor: running ? "#0f172a" : "#0b1220",
              color: running ? "#94a3b8" : "#e5e7eb",
              colorScheme: "dark",
            }}
          />
        </div>

        {/* Execution Speed */}
        <div className="col-span-2 space-y-1 pt-1">
          <div className="flex items-center justify-between text-[11px] text-textMuted">
            <span>Execution Speed</span>
            <span>{playbackSpeed}x</span>
          </div>
          <div className="flex gap-2">
            {[1, 5, 10].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => handleSpeedChange(s)}
                className={`flex-1 py-1 rounded text-xs transition-colors border ${
                  playbackSpeed === s
                    ? "bg-surfaceHover text-textPrimary border-accent font-semibold"
                    : "bg-surface text-textSecondary border-borderMuted hover:text-textPrimary"
                }`}
              >
                {s}x
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}