// "priority" removed: Person 2 does not implement a distinct
// priority-based scheduler (see ew_scheduler/backend/scheduler/) --
// keeping it here would let the UI request a strategy the backend
// cannot provide.
export type Strategy = "sequential" | "random" | "smart_ml";
export type NoiseLevel = "low" | "medium" | "high";

export interface ActiveEmitter {
  band: number;
  emitter_id?: string | null;
  emitter_type?: string | null;
  power_db?: number | null;
}

export interface ScenarioConfig {
  num_bands: number;
  num_emitters: number;
  duration: number;
  noise_level: NoiseLevel;
  strategy: Strategy;
  scenario_seed: number;
  scheduler_seed: number;
  model_name: "logistic" | "random_forest" | "xgboost";
  playback_speed?: number;
}

export interface BandPrediction {
  band: number;
  probability: number;
}

// Previously named TrackInfo. Renamed because Person 2's predictor does
// not perform persistent multi-target tracking -- it produces a fresh
// per-band probability every tick, with no track-ID continuity across
// ticks. `rank` is only this tick's ordinal position (1 = current top
// prediction), not a stable identifier for a followed entity, and the
// band it points to can change tick to tick.
export interface PredictedActivity {
  rank: number;
  band: number;
  probability: number;
}

export interface Metrics {
  ticks_run: number;
  hits: number;
  misses: number;
  detection_probability: number;
  false_alarm_probability: number;
  avg_intercept_time: number;
  intercept_rate: number;
  prediction_accuracy: number;
}

// Matches backend WSDelta exactly -- this IS the WebSocket contract.
//
// NOTE on next_band: Person 1's real SimulationEngine chooses a band and
// scans it in the same atomic call (see simulation_engine.py) -- there
// is no observable moment where a decision exists before its execution.
// `next_band` therefore reflects THIS tick's chosen band (== current_band),
// not a genuine look-ahead. See SchedulerDecision.tsx, relabeled to
// describe why this tick's band was picked rather than promising a
// preview of the future.
export interface WSDelta {
  time: number;
  current_band: number | null;
  detected: boolean | null;
  power?: number | null;
  top_predictions: BandPrediction[];
  next_band: number | null;
  scheduler_reason?: string | null;
  predicted_activity: PredictedActivity[];
  metrics: Metrics;
  running: boolean;
  completed?: boolean;
  playback_speed?: number;
  active_emitters?: ActiveEmitter[];
}

export interface SimulationState {
  running: boolean;
  completed: boolean;
  scenario: ScenarioConfig;
  simulation_time: number;
  current_band: number | null;
  metrics: Metrics;
  playback_speed: number;
}

export interface ComparisonResult {
  [strategy: string]: Metrics;
}
