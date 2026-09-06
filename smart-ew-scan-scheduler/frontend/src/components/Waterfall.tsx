import { useEffect, useRef, useState } from "react";
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
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (running && container) {
      container.scrollLeft = container.scrollWidth - container.clientWidth;
    }
  }, [history.length, running]);

  // Coordinate dimensions
  const viewWidth = 760;
  const viewHeight = 310;
  const margin = { top: 16, right: 36, bottom: 36, left: 48 };
  const basePlotWidth = viewWidth - margin.left - margin.right;
  const plotHeight = viewHeight - margin.top - margin.bottom;

  const maxBandIndex = Math.max(0, numBands - 1);

  const getYForBand = (band: number) => {
    const clamped = Math.max(0, Math.min(maxBandIndex, band));
    return margin.top + plotHeight * (1 - clamped / maxBandIndex);
  };

  // Y-axis tick values: B179, B160, B120, B80, B40, B0
  const yTicks: number[] = [];
  if (numBands > 0) {
    yTicks.push(maxBandIndex);
    for (let b = 140; b > 0; b -= 40) {
      if (b < maxBandIndex) {
        yTicks.push(b);
      }
    }
    yTicks.push(0);
  }

  const displayHistory = history;
  const minColumns = 36;
  const totalColumns = Math.max(displayHistory.length, minColumns);
  const visibleColumns = Math.min(totalColumns, 50);
  const colWidth = basePlotWidth / visibleColumns;
  const plotWidth = Math.max(basePlotWidth, totalColumns * colWidth);
  const timelineWidth = margin.left + plotWidth + margin.right;

  const getXForIndex = (index: number) => margin.left + index * colWidth;
  const currentScanY = currentBand !== null ? getYForBand(currentBand) : null;

  return (
    <div className="flex flex-col space-y-2">
      {/* Title & Status Strip */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-textPrimary">
            Spectrum Activity Waterfall
          </h2>
          <span className="text-[11px] font-mono text-textMuted">
            0–18 GHz · 180 Bands (100 MHz / Band)
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-textSecondary">
          <span>{displayHistory.length} Ticks</span>
        </div>
      </div>

      {/* Plot Canvas */}
      <div
        ref={scrollContainerRef}
        className="relative w-full overflow-x-auto overflow-y-hidden bg-[#070b12] rounded border border-borderMuted"
      >
        <svg
          viewBox={`0 0 ${timelineWidth} ${viewHeight}`}
          width={timelineWidth}
          height={viewHeight}
          className="block select-none"
          onMouseLeave={() => setTooltip(null)}
        >
          {/* Plot Background — Very Light Grey (#f1f3f5) */}
          <rect
            x={margin.left}
            y={margin.top}
            width={plotWidth}
            height={plotHeight}
            fill="#f1f3f5"
            rx="1"
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
                  stroke="#cbd5e1"
                  strokeWidth="1"
                />
                <text
                  x={margin.left - 6}
                  y={y + 3.5}
                  textAnchor="end"
                  fill="#8892b0"
                  fontSize="9.5"
                  fontFamily="monospace"
                >
                  B{tickBand}
                </text>
              </g>
            );
          })}

          {/* Vertical Grid Columns & Time Ticks */}
          {displayHistory.map((point, idx) => {
            const x = getXForIndex(idx);
            const isLatest = idx === displayHistory.length - 1;
            const showTimeTick = idx % 10 === 0 || isLatest;

            return (
              <g key={`col-${point.time}-${idx}`}>
                <line
                  x1={x}
                  y1={margin.top}
                  x2={x}
                  y2={margin.top + plotHeight}
                  stroke={isLatest ? "#64748b" : "#e2e8f0"}
                  strokeWidth="1"
                />
                {showTimeTick && (
                  <text
                    x={x + colWidth / 2}
                    y={margin.top + plotHeight + 14}
                    textAnchor="middle"
                    fill="#8892b0"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {point.time}s
                  </text>
                )}
              </g>
            );
          })}

          {/* LAYER 1: Simulated RF Emitter Blocks (Dark Green Activity) */}
          {displayHistory.map((point, colIdx) => {
            const x = getXForIndex(colIdx);
            return point.activeEmitters?.map((emitter, emitIdx) => {
              const y = getYForBand(emitter.band);
              const blockHeight = Math.max(5, plotHeight / 36);

              return (
                <rect
                  key={`emit-${point.time}-${emitter.band}-${emitIdx}`}
                  x={x + 0.5}
                  y={y - blockHeight / 2}
                  width={Math.max(2, colWidth - 1)}
                  height={blockHeight}
                  fill="#15803d"
                  opacity="0.95"
                  rx="0.5"
                  className="cursor-pointer hover:opacity-100"
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
              );
            });
          })}

          {/* LAYER 2: Receiver Scan Dwell Cell & HIT/MISS Indicators */}
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
                {/* Dwell outline */}
                <rect
                  x={x + 0.5}
                  y={y - scanCellHeight / 2}
                  width={Math.max(3, colWidth - 1)}
                  height={scanCellHeight}
                  fill="none"
                  stroke={isLatest ? "#0284c7" : "#475569"}
                  strokeWidth={isLatest ? "1.5" : "1"}
                  rx="1"
                />

                {/* HIT (✓) Indicator — Sky Blue */}
                {point.detected === true ? (
                  <g>
                    <circle
                      cx={x + colWidth / 2}
                      cy={y}
                      r={Math.min(4.5, colWidth / 2)}
                      fill="#0284c7"
                      stroke="#0369a1"
                      strokeWidth="1"
                    />
                    <text
                      x={x + colWidth / 2}
                      y={y + 2.5}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="7.5"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      ✓
                    </text>
                  </g>
                ) : point.detected === false ? (
                  /* MISS (✕) Indicator — Red */
                  <g>
                    <circle
                      cx={x + colWidth / 2}
                      cy={y}
                      r={Math.min(3.5, colWidth / 2 - 0.5)}
                      fill="#dc2626"
                      stroke="#991b1b"
                      strokeWidth="1"
                    />
                    <text
                      x={x + colWidth / 2}
                      y={y + 2}
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="6.5"
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
              <line
                x1={margin.left}
                y1={currentScanY}
                x2={margin.left + plotWidth}
                y2={currentScanY}
                stroke="#0284c7"
                strokeWidth="1"
                strokeDasharray="3,3"
                opacity="0.8"
              />
              <text
                x={margin.left + plotWidth + 4}
                y={currentScanY + 3}
                fill="#0284c7"
                fontSize="8.5"
                fontFamily="monospace"
                fontWeight="bold"
              >
                B{currentBand}
              </text>
            </g>
          )}

          {/* Bottom Time Axis Line */}
          <line
            x1={margin.left}
            y1={margin.top + plotHeight}
            x2={margin.left + plotWidth}
            y2={margin.top + plotHeight}
            stroke="#94a3b8"
            strokeWidth="1"
          />

          {/* Empty state message */}
          {displayHistory.length === 0 && (
            <text
              x={margin.left + plotWidth / 2}
              y={margin.top + plotHeight / 2}
              textAnchor="middle"
              fill="#64748b"
              fontSize="11"
              fontFamily="monospace"
            >
              Waiting for simulation start...
            </text>
          )}
        </svg>
      </div>

      {/* Clean Bottom Legend */}
      <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-textSecondary pt-1">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-sm bg-[#15803d] inline-block" />
            <span>RF Emission (Dark Green)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#0284c7] border border-[#0369a1] inline-block" />
            <span>Detection HIT (Sky Blue ✓)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#dc2626] border border-[#991b1b] inline-block" />
            <span>Detection MISS (Red ✕)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 border-t border-[#0284c7] border-dashed inline-block" />
            <span>Receiver Tune</span>
          </div>
        </div>
        <div className="text-textMuted">
          Axis: Frequency (B0–B{maxBandIndex}) vs Time (t)
        </div>
      </div>

      {/* Tooltip HUD */}
      {tooltip && (
        <div
          className="fixed z-50 pointer-events-none transform -translate-x-1/2 -translate-y-full mb-2 bg-[#0e1420] border border-borderSubtle text-textPrimary p-2.5 rounded shadow-xl text-xs font-mono min-w-[200px]"
          style={{
            left: `${tooltip.x}px`,
            top: `${tooltip.y - 6}px`,
          }}
        >
          <div className="flex items-center justify-between border-b border-borderMuted pb-1 mb-1.5 font-bold">
            <span className="text-accent">Band B{tooltip.band}</span>
            <span className="text-textMuted">t = {tooltip.time}s</span>
          </div>

          <div className="space-y-1 text-[11px]">
            <div className="flex justify-between">
              <span className="text-textMuted">Signal:</span>
              {tooltip.activeEmitter ? (
                <span className="text-green-400 font-medium">
                  {tooltip.activeEmitter.emitter_id || "Active"} ·{" "}
                  {tooltip.activeEmitter.power_db !== undefined && tooltip.activeEmitter.power_db !== null
                    ? `${tooltip.activeEmitter.power_db} dBm`
                    : "Pulse"}
                </span>
              ) : (
                <span className="text-textMuted">Inactive</span>
              )}
            </div>

            <div className="flex justify-between">
              <span className="text-textMuted">Receiver:</span>
              <span className="text-textPrimary">{tooltip.isScanned ? "Dwelt" : "Unmonitored"}</span>
            </div>

            {tooltip.isScanned && (
              <>
                <div className="flex justify-between">
                  <span className="text-textMuted">Detection:</span>
                  {tooltip.detected === true ? (
                    <span className="text-success font-semibold">HIT (Intercepted)</span>
                  ) : tooltip.detected === false ? (
                    <span className="text-danger font-semibold">MISS</span>
                  ) : (
                    <span className="text-textMuted">—</span>
                  )}
                </div>
                {tooltip.measuredPower !== undefined && tooltip.measuredPower !== null && (
                  <div className="flex justify-between">
                    <span className="text-textMuted">Power:</span>
                    <span className="text-textPrimary">{tooltip.measuredPower} dBm</span>
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
