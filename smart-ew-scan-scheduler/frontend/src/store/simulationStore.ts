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
  predictedActivity: WSDelta["predicted_activity"];
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
    num_bands: 180, // matches Person 1's real SpectrumConfig default; overwritten on reset regardless
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
  predictedActivity: [],
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
      predictedActivity: d.predicted_activity,
      metrics: d.metrics,
      // BUG FIX: reconcile "running" from the backend's own report on
      // every delta -- otherwise, when the backend auto-stops after
      // reaching ScenarioConfig.duration, the frontend's local flag
      // (only ever set by explicit start()/stop() button clicks) stays
      // stuck on true even though the simulation has actually stopped.
      running: d.running,
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
      predictedActivity: [],
      metrics: emptyMetrics,
    }),
}));
