import type { ScenarioConfig, ComparisonResult } from "../types/simulation";

const BASE_URL = "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export const api = {
  start: () => request("/simulation/start", { method: "POST" }),
  stop: () => request("/simulation/stop", { method: "POST" }),
  reset: (scenario?: ScenarioConfig) =>
    request("/simulation/reset", {
      method: "POST",
      body: scenario ? JSON.stringify(scenario) : undefined,
    }),
  setScenario: (scenario: ScenarioConfig) =>
    request("/simulation/scenario", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
  getState: () => request("/simulation/state"),
  runComparison: (scenario: ScenarioConfig) =>
    request<ComparisonResult>("/comparison", {
      method: "POST",
      body: JSON.stringify(scenario),
    }),
};
