import { useEffect } from "react";

interface PresentationViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentSlide: number;
  setCurrentSlide: (slide: number | ((prev: number) => number)) => void;
}

export function PresentationViewerModal({
  isOpen,
  onClose,
  currentSlide,
  setCurrentSlide,
}: PresentationViewerModalProps) {
  // Exact 6 slides extracted from frontend/public/presentation.pptx
  const slides = [
    {
      slideNum: 1,
      category: "SMART INDIA HACKATHON 2026",
      title: "TERRA-DELTA",
      subtitle: "Change Detection Due to Human Activities",
      content: (
        <div className="space-y-6 text-textPrimary font-mono">
          <div className="p-6 bg-[#080c16] rounded border border-borderMuted text-center space-y-3">
            <div className="text-2xl font-bold text-accent tracking-wider">
              TERRA-DELTA
            </div>
            <div className="text-sm font-semibold text-textSecondary uppercase tracking-widest">
              Smart India Hackathon 2026 · Problem Statement ID: SIH260009
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-1">
              <span className="text-[10px] text-textMuted uppercase block font-semibold">Problem Statement Title</span>
              <p className="text-textPrimary font-medium">Change detection due to human activities.</p>
            </div>
            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-1">
              <span className="text-[10px] text-textMuted uppercase block font-semibold">Theme & Category</span>
              <p className="text-textPrimary font-medium">Theme: Space Technology · Category: Software</p>
            </div>
            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-1">
              <span className="text-[10px] text-textMuted uppercase block font-semibold">Team ID & Portal Name</span>
              <p className="text-textPrimary font-medium">Team Name: Team Respawn</p>
            </div>
            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-1">
              <span className="text-[10px] text-textMuted uppercase block font-semibold">Live Prototype URL</span>
              <p className="text-accent font-medium">terradelta.vercel.app</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      slideNum: 2,
      category: "TEAM RESPAWN · PROPOSED SOLUTION",
      title: "TerraDelta MVP & Unique Value Proposition",
      subtitle: "Detect → Understand → Monitor → Decide",
      content: (
        <div className="space-y-4 text-xs text-textSecondary font-mono">
          <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-2">
            <div className="text-xs font-bold text-accent uppercase">TerraDelta MVP Pipeline</div>
            <ul className="space-y-1.5 list-disc list-inside text-textPrimary text-[11px] leading-relaxed">
              <li>No accessible, automated tool converts raw Sentinel-2 imagery into actionable human-change intelligence for non-GIS users.</li>
              <li>User selects location, draws AOI, picks two dates → AI pipeline returns change map, statistics, and PDF report in under 90 seconds.</li>
              <li><strong>Data:</strong> ESA Sentinel-2 L2A — 10 m resolution, free, global, 5-day revisit via Copernicus Data Space.</li>
              <li><strong>AI:</strong> Random Forest classifier on 42 spectral, texture and temporal features; Siamese ResNet-18 as comparison path.</li>
              <li><strong>Human-change filter:</strong> NDBI, NDVI, BSI rules isolate built-up signals and suppress floods, crop cycles and seasonal noise.</li>
              <li><strong>Outputs:</strong> Before/After imagery, RGBA change mask, GeoJSON polygons, changed area (ha), change %, cluster count, confidence score, PDF report.</li>
            </ul>
          </div>

          <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-2">
            <div className="text-xs font-bold text-success uppercase">Unique Value Proposition</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px] text-textSecondary">
              <div>
                <strong className="text-textPrimary block">DETECT:</strong>
                Automated human-activity change detection from free Sentinel-2; no GIS expertise or manual digitisation.
              </div>
              <div>
                <strong className="text-textPrimary block">UNDERSTAND:</strong>
                Change Explorer: development, vegetation and environmental shifts with real Before/After context.
              </div>
              <div>
                <strong className="text-textPrimary block">MONITOR:</strong>
                Protected Area Monitoring: save and password-protect AOIs for recurring, team-accessible monitoring without redrawing.
              </div>
              <div>
                <strong className="text-textPrimary block">DECIDE:</strong>
                Quantified outputs (area, %, confidence, clusters, PDF) feed directly into planning, compliance, insurance and infrastructure decisions.
              </div>
            </div>
          </div>
        </div>
      ),
    },
    {
      slideNum: 3,
      category: "TECHNICAL APPROACH",
      title: "Technological Stack & MVP Model",
      subtitle: "Frontend, Backend, AI/ML, Geospatial, and Deployment Stack",
      content: (
        <div className="space-y-4 text-xs text-textSecondary font-mono">
          <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-2">
            <div className="text-xs font-bold text-accent uppercase">Technological Stack</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
              <div>
                <strong className="text-textPrimary block">Frontend:</strong>
                React 18, Vite, Tailwind CSS, React-Leaflet: interactive map, AOI drawing, layer toggle, timeline chart.
              </div>
              <div>
                <strong className="text-textPrimary block">Backend / API:</strong>
                Python, FastAPI, SQLite, SQLAlchemy: async job queue, result persistence, static file serving.
              </div>
              <div>
                <strong className="text-textPrimary block">AI / ML:</strong>
                scikit-learn Random Forest, PyTorch Siamese ResNet-18 comparison, NumPy: change-probability inference.
              </div>
              <div>
                <strong className="text-textPrimary block">Geospatial / Image:</strong>
                Rasterio, OpenCV, scikit-image, SciPy, GeoPandas, Shapely: band prep, GLCM texture, morphology, vectorisation.
              </div>
              <div className="md:col-span-2">
                <strong className="text-textPrimary block">Reporting / Deploy:</strong>
                ReportLab, Docker, Render + Vercel: automated report generation and cloud deployment.
              </div>
            </div>
          </div>

          <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-1.5 text-[11px]">
            <div className="text-xs font-bold text-textPrimary uppercase">MVP Model Architecture</div>
            <p className="text-textSecondary leading-relaxed">
              <strong>Primary:</strong> Random Forest on 42 engineered features — CPU-only, interpretable feature importances, no GPU required, suitable for student-scale deployment.
            </p>
            <p className="text-textSecondary leading-relaxed">
              <strong>Comparison Path:</strong> Siamese ResNet-18 patch classifier — built, under evaluation; trained on synthetic data. Real-data training and F1 benchmarking against RF are validation work, not a deployed production model. Both models use synthetic Sentinel-2-like data for demo; OSCD real-data training is the next milestone.
            </p>
          </div>
        </div>
      ),
    },
    {
      slideNum: 4,
      category: "FEASIBILITY AND VIABILITY",
      title: "Feasibility, Viability & Operational Constraints",
      subtitle: "Pipeline Scalability, Data Economics, and Current Constraints",
      content: (
        <div className="space-y-4 text-xs text-textSecondary font-mono">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-2">
              <div className="text-xs font-bold text-success uppercase">Feasibility & Viability</div>
              <ol className="space-y-1.5 list-decimal list-inside text-[11px] text-textPrimary leading-relaxed">
                <li>End-to-end pipeline is built and tested;</li>
                <li>Free satellite data removes the largest scaling cost barrier;</li>
                <li>Protected Area Monitoring + PDF reporting encourage institutional repeat use;</li>
                <li>Modular design supports RF → U-Net upgrades;</li>
                <li>Aligns with the stated change-detection need.</li>
              </ol>
            </div>

            <div className="p-4 bg-[#080c16] rounded border border-borderMuted space-y-2">
              <div className="text-xs font-bold text-danger uppercase">Challenges / Current Constraints</div>
              <ul className="space-y-1.5 list-disc list-inside text-[11px] text-textSecondary leading-relaxed">
                <li>Sentinel-2 10 m resolution limits detection to objects ≥30 m.</li>
                <li>Spectrally ambiguous pixels can misclassify irrigated bare soil vs construction.</li>
                <li>Demo model uses synthetic data; real-world F1 not yet validated on held-out labelled scenes.</li>
                <li>CDSE free-tier download latency and persistent cloud cover can limit availability.</li>
                <li>Concurrent long jobs may queue; single background worker is a scale bottleneck.</li>
              </ul>
            </div>
          </div>
        </div>
      ),
    },
    {
      slideNum: 5,
      category: "IMPACT AND BENEFITS",
      title: "Working Product & Practical Demonstrations",
      subtitle: "Interactive Web Product & Analytical Change Mapping",
      content: (
        <div className="space-y-4 text-xs text-textSecondary font-mono">
          <div className="p-6 bg-[#080c16] rounded border border-borderMuted text-center space-y-4">
            <div className="text-sm font-bold text-textPrimary">
              Working Product Interface & Live Change Explorer
            </div>
            <div className="flex flex-wrap items-center justify-center gap-4 text-xs">
              <div className="p-4 bg-surface rounded border border-borderMuted flex-1 min-w-[240px]">
                <div className="text-accent font-bold mb-1">Live Web Application</div>
                <p className="text-[11px] text-textSecondary">Deployed on Vercel: interactive polygon selection, dual-date Sentinel-2 raster ingestion, and automatic classification.</p>
              </div>
              <div className="p-4 bg-surface rounded border border-borderMuted flex-1 min-w-[240px]">
                <div className="text-success font-bold mb-1">Instantaneous PDF Intelligence</div>
                <p className="text-[11px] text-textSecondary">Automated ReportLab generation producing audit-ready change statistics, cluster counts, and before/after overlays in under 90s.</p>
              </div>
            </div>
            <div className="text-[11px] text-textMuted pt-2 border-t border-borderMuted">
              Production Deployment URL: <span className="text-accent">terradelta.vercel.app</span>
            </div>
          </div>
        </div>
      ),
    },
    {
      slideNum: 6,
      category: "RESEARCH AND REFERENCES",
      title: "Research Base & Competitive Comparison",
      subtitle: "Grounding in Satellite Earth Observation Literature",
      content: (
        <div className="space-y-4 text-xs text-textSecondary font-mono">
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] font-mono border-collapse border border-borderMuted rounded overflow-hidden">
              <thead>
                <tr className="bg-[#0b1220] border-b border-borderMuted text-[10px] text-textMuted uppercase">
                  <th className="text-left py-2 px-2.5">Parameter</th>
                  <th className="text-left py-2 px-2.5 text-accent font-bold">TerraDelta</th>
                  <th className="text-left py-2 px-2.5">Google Earth Engine</th>
                  <th className="text-left py-2 px-2.5">ISRO Bhuvan</th>
                  <th className="text-left py-2 px-2.5">Planet Explorer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-borderMuted/60 bg-[#080c16] text-[10px]">
                <tr>
                  <td className="py-1.5 px-2.5 font-semibold text-textPrimary">Primary Focus</td>
                  <td className="py-1.5 px-2.5 text-accent font-semibold">Human change detection</td>
                  <td className="py-1.5 px-2.5">General geospatial platform</td>
                  <td className="py-1.5 px-2.5">Indian EO data portal</td>
                  <td className="py-1.5 px-2.5">Commercial high-res imagery</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-2.5 font-semibold text-textPrimary">AOI + Date Workflow</td>
                  <td className="py-1.5 px-2.5 text-accent font-semibold">Draw AOI → pick dates → auto</td>
                  <td className="py-1.5 px-2.5">Custom scripting required</td>
                  <td className="py-1.5 px-2.5">Manual visual exploration</td>
                  <td className="py-1.5 px-2.5">Manual or API (paid)</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-2.5 font-semibold text-textPrimary">Automated Change</td>
                  <td className="py-1.5 px-2.5 text-success font-semibold">✔ Built-in (RF + filter)</td>
                  <td className="py-1.5 px-2.5">Available via scripting</td>
                  <td className="py-1.5 px-2.5">Not automated</td>
                  <td className="py-1.5 px-2.5">Paid analytics add-on</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-2.5 font-semibold text-textPrimary">Area / % / Confidence</td>
                  <td className="py-1.5 px-2.5 text-success font-semibold">✔ Auto-computed PDF</td>
                  <td className="py-1.5 px-2.5">Requires custom script</td>
                  <td className="py-1.5 px-2.5">Not automated</td>
                  <td className="py-1.5 px-2.5">Available in paid tiers</td>
                </tr>
                <tr>
                  <td className="py-1.5 px-2.5 font-semibold text-textPrimary">Data Access Model</td>
                  <td className="py-1.5 px-2.5 text-accent font-semibold">Free Sentinel-2 + Freemium</td>
                  <td className="py-1.5 px-2.5">Free (quota-limited)</td>
                  <td className="py-1.5 px-2.5">Free (ISRO datasets)</td>
                  <td className="py-1.5 px-2.5">Paid subscription</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="p-3 bg-[#080c16] rounded border border-borderMuted text-[10.5px] text-textSecondary leading-relaxed">
            <strong className="text-textPrimary block mb-1">Final Positioning:</strong>
            TerraDelta is a focused, automated Earth-change decision-support layer built on freely available EO data; it is not a general-purpose GIS platform or a replacement for commercial high-resolution imagery. Its value is converting raw satellite data into quantified, human-change-specific intelligence for planners, insurers and developers without geospatial expertise.
          </div>
        </div>
      ),
    },
  ];

  const totalSlides = slides.length;
  const currentSlideData = slides[currentSlide];

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowRight") {
        setCurrentSlide((prev) => (prev < totalSlides - 1 ? prev + 1 : prev));
      } else if (e.key === "ArrowLeft") {
        setCurrentSlide((prev) => (prev > 0 ? prev - 1 : prev));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, setCurrentSlide, totalSlides]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-4xl bg-[#090d14] border border-[#1e2638] rounded-lg shadow-2xl flex flex-col max-h-[90vh] overflow-hidden">
        {/* Modal Top Bar */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-borderMuted bg-[#050816]">
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-mono text-accent font-bold">
              {currentSlideData.category}
            </span>
            <span className="text-textMuted text-xs font-mono">|</span>
            <span className="text-xs font-mono text-textSecondary">
              Slide {currentSlide + 1} / {totalSlides}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <a
              href="/presentation.pptx"
              download="presentation.pptx"
              className="text-[11px] font-mono text-textMuted hover:text-accent underline hidden sm:inline"
              title="Download original PPTX"
            >
              Download .pptx
            </a>
            <button
              type="button"
              onClick={onClose}
              className="p-1 rounded text-textSecondary hover:text-textPrimary hover:bg-surfaceHover transition-colors font-mono text-sm"
              title="Close Presentation"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Slide Body */}
        <div className="p-6 md:p-8 flex-1 overflow-y-auto space-y-5">
          <div>
            <div className="text-[11px] font-mono text-textMuted uppercase tracking-wider">
              Slide {currentSlideData.slideNum} of {totalSlides}
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-textPrimary tracking-tight mt-0.5">
              {currentSlideData.title}
            </h2>
            <p className="text-xs md:text-sm text-accent font-mono mt-0.5">
              {currentSlideData.subtitle}
            </p>
          </div>

          {currentSlideData.content}
        </div>

        {/* Modal Bottom Controls */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-borderMuted bg-[#050816] font-mono text-xs">
          <button
            type="button"
            onClick={() => setCurrentSlide((prev) => Math.max(0, prev - 1))}
            disabled={currentSlide === 0}
            className="px-3 py-1.5 rounded bg-surface border border-borderMuted text-textSecondary hover:text-textPrimary disabled:opacity-30 transition-colors"
          >
            ← Previous Slide
          </button>

          {/* Slide Indicator Dots */}
          <div className="flex items-center gap-1.5">
            {slides.map((s, idx) => (
              <button
                key={s.slideNum}
                type="button"
                onClick={() => setCurrentSlide(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${
                  currentSlide === idx ? "bg-accent" : "bg-[#1e2638] hover:bg-textMuted"
                }`}
                title={`Go to slide ${s.slideNum}`}
              />
            ))}
          </div>

          <button
            type="button"
            onClick={() =>
              setCurrentSlide((prev) => Math.min(totalSlides - 1, prev + 1))
            }
            disabled={currentSlide === totalSlides - 1}
            className="px-3 py-1.5 rounded bg-surface border border-borderMuted text-textPrimary hover:bg-surfaceHover disabled:opacity-30 transition-colors"
          >
            Next Slide →
          </button>
        </div>
      </div>
    </div>
  );
}
