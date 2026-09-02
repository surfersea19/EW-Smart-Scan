export type Strategy = "sequential" | "random" | "priority" | "smart_ml";
export type NoiseLevel = "low" | "medium" | "high";

export interface ScenarioConfig {
  num_bands: number;
  num_emitters: number;
  duration: number;
  noise_level: NoiseLevel;
  strategy: Strategy;
}

export interface BandPrediction {
  band: number;
  probability: number;
}

export interface TrackInfo {
  track_id: string;
  emitter_type: string;
  current_band: number | null;
  confidence: number;
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
export interface WSDelta {
  time: number;
  current_band: number | null;
  detected: boolean | null;
  power?: number | null;
  top_predictions: BandPrediction[];
  next_band: number | null;
  scheduler_reason?: string | null;
  tracks: TrackInfo[];
  metrics: Metrics;
}

export interface ComparisonResult {
  [strategy: string]: Metrics;
}
