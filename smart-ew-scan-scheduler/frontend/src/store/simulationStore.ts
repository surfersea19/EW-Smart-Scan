import { create } from "zustand";
import type { WSDelta, ScenarioConfig, Metrics, ActiveEmitter } from "../types/simulation";

export interface HistoryPoint {
  time: number;
  band: number | null;
  detected: boolean | null;
  power?: number | null;
  activeEmitters: ActiveEmitter[];
}

interface SimulationStore {
  connected: boolean;
  running: boolean;
  completed: boolean;
  scenario: ScenarioConfig;
  playbackSpeed: number;
  time: number;
  currentBand: number | null;
  detected: boolean | null;
  power: number | null;
  predictions: WSDelta["top_predictions"];
  nextBand: number | null;
  schedulerReason: string | null;
  predictedActivity: WSDelta["predicted_activity"];
  metrics: Metrics;
  history: HistoryPoint[];
  activeEmitters: ActiveEmitter[];

  setConnected: (c: boolean) => void;
  setRunning: (r: boolean) => void;
  setCompleted: (c: boolean) => void;
  setScenario: (s: ScenarioConfig) => void;
  setPlaybackSpeed: (speed: number) => void;
  applyDelta: (d: WSDelta) => void;
  resetHistory: () => void;
}

const HISTORY_LIMIT = 60;

const emptyMetrics: Metrics = {
  ticks_run: 0,
  hits: 0,
  misses: 0,
  detection_probability: 0,
  false_alarm_probability: 0,
  avg_intercept_time: 0,
  intercept_rate: 0,
  prediction_accuracy: 0,
};

export const useSimulationStore = create<SimulationStore>((set) => ({
  connected: false,
  running: false,
  completed: false,
  scenario: {
    num_bands: 180, // matches Person 1's real SpectrumConfig default; overwritten on reset regardless
    num_emitters: 5,
    duration: 300,
    noise_level: "medium",
    strategy: "smart_ml",
    scenario_seed: 0,
    scheduler_seed: 0,
    model_name: "random_forest",
    playback_speed: 5,
  },
  playbackSpeed: 5,
  time: 0,
  currentBand: null,
  detected: null,
  power: null,
  predictions: [],
  nextBand: null,
  schedulerReason: null,
  predictedActivity: [],
  metrics: emptyMetrics,
  history: [],
  activeEmitters: [],

  setConnected: (connected) => set({ connected }),
  setRunning: (running) => set({ running }),
  setCompleted: (completed) => set({ completed }),
  setScenario: (scenario) =>
    set((state) => ({
      scenario,
      playbackSpeed: scenario.playback_speed ?? state.playbackSpeed,
    })),
  setPlaybackSpeed: (playbackSpeed) =>
    set((state) => ({
      playbackSpeed,
      scenario: { ...state.scenario, playback_speed: playbackSpeed },
    })),

  applyDelta: (d) =>
    set((state) => ({
      time: d.time,
      currentBand: d.current_band,
      detected: d.detected,
      power: d.power ?? null,
      predictions: d.top_predictions,
      nextBand: d.next_band,
      schedulerReason: d.scheduler_reason ?? null,
      predictedActivity: d.predicted_activity,
      metrics: d.metrics,
      // Reconcile "running" and "completed" from backend delta
      running: d.running,
      completed: d.completed ?? (d.time >= state.scenario.duration),
      playbackSpeed: d.playback_speed ?? state.playbackSpeed,
      activeEmitters: d.active_emitters ?? [],
      history: [
        ...state.history,
        {
          time: d.time,
          band: d.current_band,
          detected: d.detected,
          power: d.power ?? null,
          activeEmitters: d.active_emitters ?? [],
        },
      ].slice(-HISTORY_LIMIT),
    })),

  resetHistory: () =>
    set({
      history: [],
      time: 0,
      completed: false,
      currentBand: null,
      detected: null,
      power: null,
      predictions: [],
      nextBand: null,
      schedulerReason: null,
      predictedActivity: [],
      metrics: emptyMetrics,
      activeEmitters: [],
    }),
}));
