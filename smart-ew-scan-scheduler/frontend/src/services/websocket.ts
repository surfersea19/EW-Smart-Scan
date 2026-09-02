import type { WSDelta } from "../types/simulation";

const WS_URL = "ws://localhost:8000/ws/simulation";

type DeltaHandler = (delta: WSDelta) => void;
type StatusHandler = (connected: boolean) => void;

export class SimulationSocket {
  private ws: WebSocket | null = null;
  private onDelta: DeltaHandler;
  private onStatus: StatusHandler;
  private reconnectTimer: number | null = null;

  constructor(onDelta: DeltaHandler, onStatus: StatusHandler) {
    this.onDelta = onDelta;
    this.onStatus = onStatus;
  }

  connect() {
    this.ws = new WebSocket(WS_URL);

    this.ws.onopen = () => this.onStatus(true);

    this.ws.onmessage = (event) => {
      try {
        const delta = JSON.parse(event.data) as WSDelta;
        this.onDelta(delta);
      } catch (err) {
        console.error("Failed to parse WS delta", err);
      }
    };

    this.ws.onclose = () => {
      this.onStatus(false);
      // simple auto-reconnect for demo resilience
      this.reconnectTimer = window.setTimeout(() => this.connect(), 1500);
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  disconnect() {
    if (this.reconnectTimer) window.clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }
}
