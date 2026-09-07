export function SystemIntelligence() {
  return (
    <div className="p-6 md:p-12 max-w-[1320px] mx-auto space-y-14 text-textPrimary font-sans">
      {/* ========================================================================= */}
      {/* HERO SECTION — FIRST SUMMARY BOX (APPROVED DESIGN)                        */}
      {/* ========================================================================= */}
      <section className="space-y-6">
        <div className="space-y-1.5">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            Cognitive Electronic Warfare Technical Briefing
          </div>
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-textPrimary">
            SMART SCAN
          </h1>
          <p className="text-sm text-textSecondary font-mono">
            AI-Driven Adaptive Spectrum Surveillance & Scan Scheduling
          </p>
        </div>

        {/* First Summary / Hero Box */}
        <div className="p-6 bg-surface rounded border border-borderMuted font-mono text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-center items-center">
            <div className="space-y-1">
              <div className="text-[10px] text-textMuted uppercase">1. Operating Spectrum</div>
              <div className="text-base font-bold text-textPrimary">WIDE SPECTRUM</div>
              <div className="text-[11px] text-textSecondary">0–18 GHz (180 Sub-Bands)</div>
            </div>

            <div className="space-y-1 border-t sm:border-t-0 sm:border-l border-borderMuted pt-3 sm:pt-0 sm:pl-6">
              <div className="text-[10px] text-textMuted uppercase">2. Receiver Constraint</div>
              <div className="text-base font-bold text-textPrimary">LIMITED BANDWIDTH</div>
              <div className="text-[11px] text-textSecondary">100 MHz Instantaneous Window</div>
            </div>

            <div className="space-y-1 border-t lg:border-t-0 lg:border-l border-borderMuted pt-3 lg:pt-0 lg:pl-6">
              <div className="text-[10px] text-textMuted uppercase">3. Cognitive Engine</div>
              <div className="text-base font-bold text-accent">SMART BAND SELECTION</div>
              <div className="text-[11px] text-textSecondary">ML + Temporal + Doctrine Detection</div>
            </div>

            <div className="space-y-1 border-t sm:border-t-0 lg:border-l border-borderMuted pt-3 sm:pt-0 lg:pl-6">
              <div className="text-[10px] text-textMuted uppercase">4. Operational Impact</div>
              <div className="text-base font-bold text-success">INFORMED INTERCEPTION</div>
              <div className="text-[11px] text-textSecondary">Superior Pd · Faster MTTI</div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 01 // THE SURVEILLANCE CHALLENGE                                         */}
      {/* ========================================================================= */}
      <section className="space-y-5 border-t border-[#1e2638] pt-10">
        <div className="space-y-1.5">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            01 // THE SURVEILLANCE CHALLENGE
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            Wide Spectrum. Narrow Window. One Decision.
          </h2>
        </div>

        <div className="space-y-3.5 text-sm text-textSecondary font-mono leading-relaxed max-w-4xl">
          <p>
            Electronic Warfare receivers must monitor a wide frequency spectrum where hostile radars and communication emitters may appear briefly, repeatedly, or change frequency over time.
          </p>
          <p>
            Our simulated operational spectrum spans 0–18 GHz, divided into 180 contiguous 100 MHz bands. However, the receiver can observe only one 100 MHz band at a time.
          </p>
          <p>
            At every timestep, therefore, the receiver sees only a tiny fraction of the spectrum while the remaining 179 bands remain unobserved.
          </p>
          <p className="text-textPrimary font-semibold">
            The fundamental problem is not simply scanning the spectrum.
          </p>
          <div className="p-3 bg-[#070b12] rounded border-l-2 border-accent text-accent font-semibold">
            “Which frequency band should the receiver observe next to maximize the probability of interception?”
          </div>
          <p>
            A sequential receiver treats every band equally. Smart Scan treats the spectrum as a continuously changing environment and uses previous observations to decide where attention should move next.
          </p>
        </div>

        {/* Visual Spectrum Ruler & 100 MHz Window Illustration */}
        <div className="space-y-2.5 font-mono text-xs pt-3">
          <div className="flex items-center justify-between text-[11px] text-textSecondary">
            <span>0.0 GHz (Band B0)</span>
            <span className="text-textPrimary font-semibold">18.0 GHz Operational Range (180 Channels · 100 MHz / Band)</span>
            <span>18.0 GHz (Band B179)</span>
          </div>

          <div className="p-4 bg-[#070b12] rounded border border-[#1e2638]">
            <svg viewBox="0 0 720 65" className="w-full h-16 select-none">
              {/* Frequency grid */}
              {Array.from({ length: 19 }).map((_, i) => (
                <line
                  key={i}
                  x1={i * 40}
                  y1="0"
                  x2={i * 40}
                  y2="42"
                  stroke="#131c2c"
                  strokeWidth="1"
                />
              ))}

              {/* Distributed Emitter Pulses */}
              <rect x="56" y="16" width="8" height="26" fill="#15803d" rx="1" />
              <text x="60" y="12" textAnchor="middle" fill="#34d399" fontSize="8">Radar</text>

              <rect x="144" y="8" width="12" height="34" fill="#15803d" rx="1" />
              <text x="150" y="6" textAnchor="middle" fill="#38bdf8" fontSize="8" fontWeight="bold">Target (B36)</text>

              <rect x="336" y="18" width="8" height="24" fill="#15803d" rx="1" />
              <text x="340" y="14" textAnchor="middle" fill="#34d399" fontSize="8">Burst</text>

              <rect x="448" y="12" width="8" height="30" fill="#15803d" rx="1" />
              <text x="452" y="8" textAnchor="middle" fill="#34d399" fontSize="8">Chirp</text>

              <rect x="624" y="20" width="8" height="22" fill="#15803d" rx="1" />
              <text x="628" y="16" textAnchor="middle" fill="#34d399" fontSize="8">Hop</text>

              {/* 100 MHz Instantaneous Receiver Window Reticle */}
              <rect
                x="140"
                y="2"
                width="20"
                height="44"
                fill="none"
                stroke="#38bdf8"
                strokeWidth="2"
                strokeDasharray="2,2"
                rx="2"
              />
              <text x="150" y="58" textAnchor="middle" fill="#38bdf8" fontSize="8.5" fontWeight="bold">
                Instantaneous Dwell Window (100 MHz)
              </text>

              {/* Unmonitored Blind Zone Brackets */}
              <line x1="0" y1="46" x2="138" y2="46" stroke="#475569" strokeWidth="1" />
              <line x1="162" y1="46" x2="720" y2="46" stroke="#475569" strokeWidth="1" />
            </svg>
          </div>

          <div className="flex flex-wrap items-center justify-between text-[11px] text-textSecondary pt-0.5">
            <span>Instantaneous Receiver Window: <strong className="text-accent">1 Band (100 MHz)</strong></span>
            <span>Unobserved Spectrum: <strong className="text-danger">179 Bands (17.9 GHz / 99.4%)</strong></span>
            <span>Constraint: <strong className="text-textPrimary">1 Dwell per Timestep</strong></span>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 02 // FROM SCANNING TO COGNITIVE SEARCH                                   */}
      {/* ========================================================================= */}
      <section className="space-y-5 border-t border-[#1e2638] pt-10 font-mono text-sm">
        <div className="space-y-1.5 font-sans">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            02 // FROM SCANNING TO COGNITIVE SEARCH
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            Why Sequential Scanning Is Not Enough
          </h2>
        </div>

        <div className="space-y-3.5 text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
          <p>
            A conventional sequential strategy follows a predictable trajectory:
          </p>
          <div className="p-2.5 bg-[#070b12] rounded text-textMuted text-xs font-mono">
            B0 → B1 → B2 → … → B179
          </div>
          <p>
            This guarantees coverage, but creates long revisit intervals. A short radar burst or frequency-agile emitter can become active while its band is outside the receiver's instantaneous observation window.
          </p>
          <p>
            Smart Scan replaces this fixed trajectory with an adaptive search strategy.
          </p>
          <p className="text-textPrimary font-semibold">
            Instead of asking “Which band comes next?”, the scheduler asks:
          </p>
          <div className="p-3 bg-[#070b12] rounded border-l-2 border-accent text-accent font-semibold">
            “Given everything observed so far, which band is most valuable to observe now?”
          </div>
          <p>
            The system combines machine-learning activity prediction, temporal recurrence, emitter behavior, recent activity, uncertainty, and exploration needs to dynamically rank candidate bands.
          </p>
          <p>
            The resulting scan path can move non-sequentially toward bands where activity is more likely while still maintaining exploration of less-observed regions.
          </p>
        </div>

        {/* Cognitive Closed-Loop Banner */}
        <div className="p-4 bg-[#070b12] rounded border border-[#1e2638] text-xs">
          <div className="text-[10px] text-textMuted uppercase mb-2">Cognitive Closed-Loop Sequence</div>
          <div className="flex flex-wrap items-center justify-between gap-2 text-center text-[11px] font-bold">
            <span className="text-textPrimary">OBSERVE</span>
            <span className="text-textMuted">→</span>
            <span className="text-textPrimary">EXTRACT</span>
            <span className="text-textMuted">→</span>
            <span className="text-accent">PREDICT</span>
            <span className="text-textMuted">→</span>
            <span className="text-accent">ANALYZE</span>
            <span className="text-textMuted">→</span>
            <span className="text-accent">INFER</span>
            <span className="text-textMuted">→</span>
            <span className="text-success">SCORE</span>
            <span className="text-textMuted">→</span>
            <span className="text-success">SELECT</span>
            <span className="text-textMuted">→</span>
            <span className="text-textPrimary">DETECT</span>
            <span className="text-textMuted">→</span>
            <span className="text-textPrimary">LEARN</span>
          </div>
        </div>

        <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
          This creates a closed-loop cognitive surveillance process rather than a predetermined sweep.
        </p>
      </section>

      {/* ========================================================================= */}
      {/* 03 // THE SMART SCAN DECISION ENGINE                                      */}
      {/* ========================================================================= */}
      <section className="space-y-6 border-t border-[#1e2638] pt-10 font-mono text-xs md:text-sm">
        <div className="space-y-1.5 font-sans">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            03 // THE SMART SCAN DECISION ENGINE
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            Turning Receiver Observations into the Next Scan
          </h2>
        </div>

        <p className="text-textSecondary leading-relaxed max-w-4xl">
          Smart Scan makes decisions using receiver observations only. Ground-truth emitter information is isolated from the operational decision pipeline.
        </p>

        <div className="space-y-6 pt-2">
          {/* Point 1 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-accent font-sans">
              1. Observation & Feature Extraction
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Every receiver dwell produces measurable observations such as detection status, received power, pulse characteristics, and timing. Historical observations are transformed into features describing activity, recency, repetition, staleness, and temporal behavior.
            </p>
          </div>

          {/* Point 2 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-accent font-sans">
              2. Machine-Learning Activity Prediction
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Supervised ML models evaluate the observation-derived features for candidate bands and estimate:
            </p>
            <div className="p-2.5 bg-[#070b12] rounded text-accent font-semibold max-w-md">
              P(active | observed history)
            </div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              The project supports models including Random Forest, XGBoost, and Logistic Regression, allowing different predictive approaches to be evaluated under identical scenarios.
            </p>
          </div>

          {/* Point 3 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-accent font-sans">
              3. Temporal Intelligence
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              A periodic emitter cannot be effectively handled by probability alone.
            </p>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              The temporal analysis detects recurring burst intervals, estimates periodicity, measures regularity, and determines how close the current time is to an expected future activity window.
            </p>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              This allows the scheduler to exploit when an emitter is likely to appear, not only where it is likely to appear.
            </p>
          </div>

          {/* Point 4 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-accent font-sans">
              4. Behavior Intelligence
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              The system infers emitter behavior directly from observations.
            </p>
            <p className="text-textPrimary font-semibold text-xs md:text-sm">
              It distinguishes patterns such as: Fixed · Periodic · Bursty · Agile · Scanning · Unknown
            </p>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Frequency transitions, adjacency, directional movement, repetition, and timing irregularity provide evidence about the emitter's operational behavior.
            </p>
          </div>

          {/* Point 5 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-accent font-sans">
              5. Multi-Objective Scheduling
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              The scheduler combines these intelligence sources into a single candidate score.
            </p>
            <div className="p-2.5 bg-[#070b12] rounded text-accent font-semibold max-w-2xl">
              Score = Prediction + Temporal Intelligence + Behavior + Exploration − Repeat Penalties
            </div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              High-probability bands can be exploited, recently observed activity can be tracked, predictable emitters can be anticipated, while stale and unexplored regions continue receiving attention.
            </p>
          </div>

          {/* Point 6 */}
          <div className="space-y-1.5">
            <h3 className="text-base font-bold text-success font-sans">
              6. Persistent Knowledge
            </h3>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Completed runs can contribute empirical knowledge about previously observed activity.
            </p>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              This information can be retained as a warm-start prior for subsequent runs, allowing the scheduler to begin with useful historical knowledge instead of always starting completely cold.
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 04 // EMITTER BEHAVIOR INTELLIGENCE                                       */}
      {/* ========================================================================= */}
      <section className="space-y-6 border-t border-[#1e2638] pt-10 font-mono text-xs md:text-sm">
        <div className="space-y-1.5 font-sans">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            04 // EMITTER BEHAVIOR INTELLIGENCE
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            Different Emitters Require Different Search Strategies
          </h2>
        </div>

        <p className="text-textSecondary leading-relaxed max-w-4xl">
          Smart Scan does not assume every emitter behaves the same way.
        </p>

        <div className="space-y-5 pt-1">
          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Fixed-Frequency</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Persistent activity concentrated in one band. The scheduler can exploit strong historical evidence while periodically exploring elsewhere.
            </p>
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Periodic Radar</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Recurring pulses with identifiable timing structure. Temporal intelligence estimates recurrence and helps position the receiver near future pulse windows.
            </p>
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Bursty Transmitter</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Intermittent and irregular activity. Active-band memory allows the scheduler to revisit recently detected bands before the burst opportunity disappears.
            </p>
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Frequency-Agile Emitter</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Activity moves across separated frequency bands. Cross-band transitions provide evidence about the emitter's changing location and help maintain an active candidate pool.
            </p>
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Frequency-Scanning Emitter</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              Activity moves progressively across adjacent bands. Directional transition patterns allow the scheduler to anticipate the next portion of the sweep.
            </p>
          </div>

          <div className="space-y-1">
            <div className="text-sm font-bold text-textPrimary font-sans">Unknown</div>
            <p className="text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
              When evidence is insufficient, the system does not force a classification. It remains uncertain and continues collecting observations.
            </p>
            <p className="text-textPrimary text-xs md:text-sm font-semibold pt-1">
              This is important because uncertainty itself becomes part of the decision process.
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 05 // VERIFIED RESULTS & OPERATIONAL VALUE                                 */}
      {/* ========================================================================= */}
      <section className="space-y-6 border-t border-[#1e2638] pt-10 font-mono text-xs md:text-sm">
        <div className="space-y-1.5 font-sans">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            05 // VERIFIED RESULTS & OPERATIONAL VALUE
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            Measuring Whether Intelligence Actually Helps
          </h2>
        </div>

        <div className="space-y-3.5 text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
          <p>
            Smart Scan is evaluated against deterministic baselines under identical simulated scenarios.
          </p>
          <p>
            In the verified five-seed temporal-intelligence experiment, the sequential baseline achieved approximately <strong>10.4%</strong> detection probability, while the Smart Scan system achieved approximately <strong>17.4%</strong>.
          </p>
          <p>
            Intercept rate increased from approximately <strong>7.4%</strong> to <strong>12.4%</strong>.
          </p>
          <p>
            These results demonstrate the value of combining prediction with temporal intelligence, while also showing that performance depends strongly on emitter behavior, scenario composition, and available observations.
          </p>
          <p className="text-textPrimary font-semibold">
            The system therefore reports measurable operational metrics rather than relying only on visual demonstrations:
          </p>
        </div>

        <div className="space-y-4 pt-1 max-w-4xl">
          <div className="space-y-0.5">
            <div className="font-bold text-textPrimary font-sans text-sm">Detection Probability (Pd)</div>
            <p className="text-textSecondary text-xs md:text-sm">How often active emissions are successfully detected.</p>
          </div>

          <div className="space-y-0.5">
            <div className="font-bold text-textPrimary font-sans text-sm">Intercept Rate</div>
            <p className="text-textSecondary text-xs md:text-sm">How effectively fleeting emission opportunities are captured.</p>
          </div>

          <div className="space-y-0.5">
            <div className="font-bold text-textPrimary font-sans text-sm">Mean Time to Intercept (MTTI)</div>
            <p className="text-textSecondary text-xs md:text-sm">How quickly the receiver reaches an active emitter.</p>
          </div>
        </div>

        <div className="p-3 bg-[#070b12] rounded border-l-2 border-accent text-accent font-semibold max-w-3xl">
          “Spend limited receiver observation time where it has the greatest probability of producing an intercept.”
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 06 // THE COGNITIVE EW LOOP                                               */}
      {/* ========================================================================= */}
      <section className="space-y-5 border-t border-[#1e2638] pt-10 font-mono text-xs md:text-sm">
        <div className="space-y-1.5 font-sans">
          <div className="text-xs font-mono text-accent uppercase tracking-wider font-semibold">
            06 // THE COGNITIVE EW LOOP
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-textPrimary">
            From Passive Scanning to Adaptive Surveillance
          </h2>
        </div>

        <div className="space-y-3.5 text-textSecondary text-xs md:text-sm leading-relaxed max-w-4xl">
          <p>
            Smart Scan transforms a constrained receiver into an observation-driven decision system.
          </p>
          <p>
            The receiver observes one small portion of a wide spectrum. Those observations become features. Machine learning estimates future activity. Temporal analysis identifies recurrence. Behavior intelligence interprets emitter movement. The scheduler combines these signals and selects the next band.
          </p>
          <p>
            The receiver then observes again, producing new evidence that updates the next decision.
          </p>
          <div className="p-3 bg-[#070b12] rounded text-accent font-bold text-sm tracking-wide">
            Observe → Understand → Predict → Decide → Intercept → Learn
          </div>
          <p>
            The system does not attempt to observe everything simultaneously.
          </p>
          <p className="text-textPrimary font-semibold">
            It makes the next observation more intelligent.
          </p>
        </div>

        <div className="pt-4 text-xs font-mono text-textMuted">
          <strong className="text-textPrimary">SMART SCAN</strong> · AI-Driven Adaptive Spectrum Surveillance
        </div>
      </section>
    </div>
  );
}

