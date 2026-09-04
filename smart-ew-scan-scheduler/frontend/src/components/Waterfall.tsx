import { useState } from "react";
import { useSimulationStore } from "../store/simulationStore";
import type { ActiveEmitter } from "../types/simulation";

interface TooltipInfo {
  x: number;
  y: number;
  time: number;
  band: number;
  activeEmitter?: ActiveEmitter;
  isScanned: boolean;
  detected?: boolean | null;
  measuredPower?: number | null;
}

export function Waterfall() {
  const history = useSimulationStore((s) => s.history);
  const numBands = useSimulationStore((s) => s.scenario.num_bands) || 180;
  const currentBand = useSimulationStore((s) => s.currentBand);
  const running = useSimulationStore((s) => s.running);

  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  // SVG coordinate dimensions
  const viewWidth = 760;
  const viewHeight = 290;
  const margin = { top: 15, right: 35, bottom: 42, left: 52 };
  const plotWidth = viewWidth - margin.left - margin.right;
  const plotHeight = viewHeight - margin.top - margin.bottom;

  // Maximum bands is numBands (0 to numBands - 1). Highest index is B(numBands - 1)
  const maxBandIndex = Math.max(0, numBands - 1);

  // Band Y-coordinate helper (B0 at bottom, B179 at top)
  const getYForBand = (band: number) => {
    const clamped = Math.max(0, Math.min(maxBandIndex, band));
    return margin.top + plotHeight * (1 - clamped / maxBandIndex);
  };

  // Y-axis tick values: B179, B160, B140, B120, B100, B80, B60, B40, B20, B0
  const yTicks: number[] = [];
  if (numBands > 0) {
    yTicks.push(maxBandIndex); // B179
    for (let b = 160; b > 0; b -= 20) {
      if (b < maxBandIndex) {
        yTicks.push(b);
      }
    }
    yTicks.push(0); // B0
  }

  // Display columns: up to last 45 time steps (or pad if history is short)
  const displayHistory = history.slice(-45);
  const minColumns = 30;
  const totalColumns = Math.max(displayHistory.length, minColumns);
  const colWidth = plotWidth / totalColumns;

  // X position helper
  const getXForIndex = (index: number) => margin.left + index * colWidth;

  const currentScanY = currentBand !== null ? getYForBand(currentBand) : null;

  return (
    <div className="bg-panel rounded-lg p-4 border border-slate-800 flex flex-col relative">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-mono text-slate-300 uppercase tracking-wide font-semibold">
            Live Spectrum / Waterfall
          </h3>
          {currentBand !== null && running && (
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent/15 text-accent border border-accent/30 animate-pulse">
              Scanning B{currentBand}
            </span>
          )}
        </div>
        <span className="text-xs text-slate-500 font-mono italic">
          simulated activity — not a physical spectrogram
        </span>
      </div>

      {/* Waterfall Visualization Area */}
      <div className="relative w-full overflow-hidden bg-slate-950/80 rounded border border-slate-800/80">
        <svg
          viewBox={`0 0 ${viewWidth} ${viewHeight}`}
          className="w-full h-auto select-none"
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Background Grid Area */}
          <rect
            x={margin.left}
            y={margin.top}
            width={plotWidth}
            height={plotHeight}
            fill="#060c18"
          />

          {/* Horizontal Grid Lines & Y-Axis Labels */}
          {yTicks.map((tickBand) => {
            const y = getYForBand(tickBand);
            return (
              <g key={`ytick-${tickBand}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={margin.left + plotWidth}
                  y2={y}
                  stroke="#1e293b"
                  strokeWidth="1"
                  strokeDasharray="2,3"
                />
                <text
                  x={margin.left - 6}
                  y={y + 3.5}
                  textAnchor="end"
                  fill="#94a3b8"
                  fontSize="10"
                  fontFamily="monospace"
                  fontWeight="600"
                >
                  B{tickBand}
                </text>
              </g>
            );
          })}

          {/* Vertical Column Separators & Time Labels */}
          {displayHistory.map((point, idx) => {
            const x = getXForIndex(idx);
            const isLatest = idx === displayHistory.length - 1;
            const showTimeTick = idx % 8 === 0 || isLatest;

            return (
              <g key={`col-grid-${point.time}-${idx}`}>
                <line
                  x1={x}
                  y1={margin.top}
                  x2={x}
                  y2={margin.top + plotHeight}
                  stroke={isLatest ? "#38bdf844" : "#0f172a"}
                  strokeWidth="1"
                />
                {showTimeTick && (
                  <text
                    x={x + colWidth / 2}
                    y={margin.top + plotHeight + 14}
                    textAnchor="middle"
                    fill="#64748b"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    t={point.time}
                  </text>
                )}
              </g>
            );
          })}

          {/* LAYER 1: Simulated RF Environment Emitter Activity Blocks */}
          {displayHistory.map((point, colIdx) => {
            const x = getXForIndex(colIdx);
            return point.activeEmitters?.map((emitter, emitIdx) => {
              const y = getYForBand(emitter.band);
              const blockHeight = Math.max(5, plotHeight / 36);

              return (
                <g key={`emit-${point.time}-${emitter.band}-${emitIdx}`}>
                  {/* Subtle emission glow */}
                  <rect
                    x={x + 1}
                    y={y - blockHeight / 2}
                    width={Math.max(2, colWidth - 2)}
                    height={blockHeight}
                    fill="#f59e0b"
                    opacity="0.3"
                    rx="1"
                  />
                  {/* Core emitter activity block */}
                  <rect
                    x={x + 1.5}
                    y={y - blockHeight / 2 + 0.5}
                    width={Math.max(1.5, colWidth - 3)}
                    height={blockHeight - 1}
                    fill="#fbbf24"
                    opacity="0.9"
                    rx="1"
                    className="cursor-pointer hover:fill-amber-300"
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setTooltip({
                        x: rect.left + rect.width / 2,
                        y: rect.top,
                        time: point.time,
                        band: emitter.band,
                        activeEmitter: emitter,
                        isScanned: point.band === emitter.band,
                        detected: point.band === emitter.band ? point.detected : undefined,
                        measuredPower: point.band === emitter.band ? point.power : undefined,
                      });
                    }}
                  />
                </g>
              );
            });
          })}

          {/* LAYER 2: Receiver Scan Indicator & Separate HIT/MISS Markers */}
          {displayHistory.map((point, colIdx) => {
            if (point.band === null) return null;
            const x = getXForIndex(colIdx);
            const y = getYForBand(point.band);
            const isLatest = colIdx === displayHistory.length - 1;
            const scanCellHeight = Math.max(8, plotHeight / 22);

            return (
              <g
                key={`scan-${point.time}-${point.band}-${colIdx}`}
                className="cursor-pointer"
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const matchingEmitter = point.activeEmitters?.find(
                    (em) => em.band === point.band
                  );
                  setTooltip({
                    x: rect.left + rect.width / 2,
                    y: rect.top,
                    time: point.time,
                    band: point.band!,
                    activeEmitter: matchingEmitter,
                    isScanned: true,
                    detected: point.detected,
                    measuredPower: point.power,
                  });
                }}
              >
                {/* Scanned band cell outline */}
                <rect
                  x={x + 0.5}
                  y={y - scanCellHeight / 2}
                  width={Math.max(3, colWidth - 1)}
                  height={scanCellHeight}
                  fill="none"
                  stroke={isLatest ? "#38bdf8" : "#64748b"}
                  strokeWidth={isLatest ? "1.5" : "1"}
                  strokeDasharray={isLatest ? "none" : "2,1"}
                  rx="1.5"
                />

                {/* Separate HIT (✓) or MISS (✕) Detection Marker */}
                {point.detected === true ? (
                  <g>
                    {/* HIT indicator: Green badge with checkmark */}
                    <circle
                      cx={x + colWidth / 2}
                      cy={y}
                      r={Math.min(5, colWidth / 2)}
                      fill="#166534"
                      stroke="#4ade80"
                      strokeWidth="1.2"
                    />
                    <text
                      x={x + colWidth / 2}
                      y={y + 3}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="8"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      ✓
                    </text>
                  </g>
                ) : point.detected === false ? (
                  <g>
                    {/* MISS indicator: Red cross marker */}
                    <circle
                      cx={x + colWidth / 2}
                      cy={y}
                      r={Math.min(4, colWidth / 2 - 1)}
                      fill="#7f1d1d"
                      stroke="#f87171"
                      strokeWidth="1"
                    />
                    <text
                      x={x + colWidth / 2}
                      y={y + 2.5}
                      textAnchor="middle"
                      fill="#fca5a5"
                      fontSize="7"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      ✕
                    </text>
                  </g>
                ) : null}
              </g>
            );
          })}

          {/* LAYER 3: Current Receiver Scan Line Reticle */}
          {currentScanY !== null && (
            <g>
              {/* Horizontal scan line across the waterfall */}
              <line
                x1={margin.left}
                y1={currentScanY}
                x2={margin.left + plotWidth}
                y2={currentScanY}
                stroke="#22d3ee"
                strokeWidth="1.2"
                strokeDasharray="4,3"
                opacity="0.75"
              />
              {/* Right-edge band indicator tag */}
              <rect
                x={margin.left + plotWidth + 2}
                y={currentScanY - 7}
                width="28"
                height="14"
                fill="#0f172a"
                stroke="#22d3ee"
                strokeWidth="1"
                rx="2"
              />
              <text
                x={margin.left + plotWidth + 16}
                y={currentScanY + 3.5}
                textAnchor="middle"
                fill="#22d3ee"
                fontSize="8.5"
                fontFamily="monospace"
                fontWeight="bold"
              >
                B{currentBand}
              </text>
            </g>
          )}

          {/* Bottom X-Axis Axis Line & Label */}
          <line
            x1={margin.left}
            y1={margin.top + plotHeight}
            x2={margin.left + plotWidth}
            y2={margin.top + plotHeight}
            stroke="#334155"
            strokeWidth="1"
          />
          <text
            x={margin.left + plotWidth / 2}
            y={margin.top + plotHeight + 30}
            textAnchor="middle"
            fill="#94a3b8"
            fontSize="10"
            fontFamily="monospace"
            fontWeight="600"
          >
            SIMULATION TIME (t) →
          </text>

          {/* Empty state message if no ticks yet */}
          {displayHistory.length === 0 && (
            <text
              x={margin.left + plotWidth / 2}
              y={margin.top + plotHeight / 2}
              textAnchor="middle"
              fill="#475569"
              fontSize="12"
              fontFamily="monospace"
            >
              Waiting for simulation start...
            </text>
          )}
        </svg>
      </div>

      {/* Explanatory Legend */}
      <div className="flex flex-wrap items-center justify-between text-xs font-mono text-slate-400 mt-3 pt-2 border-t border-slate-800/80 gap-2">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded bg-amber-400 border border-amber-300 inline-block" />
            <span className="text-slate-300">Simulated Emitter Activity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full bg-green-700 border border-green-400 text-white flex items-center justify-center text-[9px] font-bold">
              ✓
            </span>
            <span className="text-slate-300">Receiver HIT</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded-full bg-red-900 border border-red-400 text-red-300 flex items-center justify-center text-[8px] font-bold">
              ✕
            </span>
            <span className="text-slate-300">Receiver MISS</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-2 border border-cyan-400 border-dashed inline-block" />
            <span className="text-slate-300">Current Scan Cursor</span>
          </div>
        </div>
        <div className="text-slate-500 font-mono">
          Bands: <span className="text-slate-300 font-bold">B0 – B{maxBandIndex}</span> (180 bands)
        </div>
      </div>

      {/* Floating Hover Tooltip */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2 bg-slate-900/95 border border-slate-700 text-slate-100 p-2.5 rounded-md shadow-2xl text-xs font-mono min-w-[200px]"
          style={{
            left: `${tooltip.x}px`,
            top: `${tooltip.y - 8}px`,
          }}
        >
          <div className="flex items-center justify-between border-b border-slate-700 pb-1 mb-1.5 font-bold">
            <span className="text-accent">Band B{tooltip.band}</span>
            <span className="text-slate-400">t = {tooltip.time}</span>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-400">RF Activity:</span>
              {tooltip.activeEmitter ? (
                <span className="text-amber-400 font-semibold">
                  ACTIVE ({tooltip.activeEmitter.emitter_id || "Emitter"} ·{" "}
                  {tooltip.activeEmitter.power_db !== undefined && tooltip.activeEmitter.power_db !== null
                    ? `${tooltip.activeEmitter.power_db} dBm`
                    : tooltip.activeEmitter.emitter_type || "Signal"}
                  )
                </span>
              ) : (
                <span className="text-slate-500">Idle / Inactive</span>
              )}
            </div>

            <div className="flex justify-between">
              <span className="text-slate-400">Receiver:</span>
              {tooltip.isScanned ? (
                <span className="text-slate-200">Scanned</span>
              ) : (
                <span className="text-slate-500">Not Scanned</span>
              )}
            </div>

            {tooltip.isScanned && (
              <>
                <div className="flex justify-between">
                  <span className="text-slate-400">Detection:</span>
                  {tooltip.detected === true ? (
                    <span className="text-hit font-bold">HIT (Detected ✓)</span>
                  ) : tooltip.detected === false ? (
                    <span className="text-miss font-bold">MISS (No Signal ✕)</span>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </div>
                {tooltip.measuredPower !== undefined && tooltip.measuredPower !== null && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Measured Power:</span>
                    <span className="text-slate-200">{tooltip.measuredPower} dBm</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
