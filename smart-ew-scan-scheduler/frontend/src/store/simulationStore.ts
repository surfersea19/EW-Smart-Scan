import { create } from "zustand";
import type { WSDelta, ScenarioConfig, Metrics } from "../types/simulation";

interface HistoryPoint {
  time: number;
  band: number | null;
  detected: boolean | null;
}

interface SimulationStore {
  connected: boolean;
  running: boolean;
  scenario: ScenarioConfig;
  time: number;
  currentBand: number | null;
  detected: boolean | null;
  power: number | null;
  predictions: WSDelta["top_predictions"];
  nextBand: number | null;
  schedulerReason: string | null;
  tracks: WSDelta["tracks"];
  metrics: Metrics;
  history: HistoryPoint[];

  setConnected: (c: boolean) => void;
  setRunning: (r: boolean) => void;
  setScenario: (s: ScenarioConfig) => void;
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
  scenario: {
    num_bands: 100,
    num_emitters: 5,
    duration: 300,
    noise_level: "medium",
    strategy: "smart_ml",
  },
  time: 0,
  currentBand: null,
  detected: null,
  power: null,
  predictions: [],
  nextBand: null,
  schedulerReason: null,
  tracks: [],
  metrics: emptyMetrics,
  history: [],

  setConnected: (connected) => set({ connected }),
  setRunning: (running) => set({ running }),
  setScenario: (scenario) => set({ scenario }),

  applyDelta: (d) =>
    set((state) => ({
      time: d.time,
      currentBand: d.current_band,
      detected: d.detected,
      power: d.power ?? null,
      predictions: d.top_predictions,
      nextBand: d.next_band,
      schedulerReason: d.scheduler_reason ?? null,
      tracks: d.tracks,
      metrics: d.metrics,
      history: [
        ...state.history,
        { time: d.time, band: d.current_band, detected: d.detected },
      ].slice(-HISTORY_LIMIT),
    })),

  resetHistory: () =>
    set({
      history: [],
      time: 0,
      currentBand: null,
      detected: null,
      predictions: [],
      nextBand: null,
      schedulerReason: null,
      tracks: [],
      metrics: emptyMetrics,
    }),
}));
