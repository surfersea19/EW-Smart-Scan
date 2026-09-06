# backend/prediction/behavior_detector.py

from dataclasses import dataclass, field
from statistics import mean, pstdev


@dataclass
class BehaviorFeatures:
    """Behavior evidence extracted only from receiver observations."""

    hit_count: int = 0
    hit_ratio: float = 0.0
    time_since_hit: float = 0.0
    mean_inter_hit: float = 0.0
    inter_hit_cv: float = 0.0
    recent_hit_density: float = 0.0

    unique_hit_bands: int = 0
    transition_count: int = 0
    mean_jump: float = 0.0
    adjacent_ratio: float = 0.0
    direction_consistency: float = 0.0
    band_span: int = 0


@dataclass
class BehaviorResult:
    """Classification plus confidence and numerical evidence."""

    behavior: str
    confidence: float
    features: BehaviorFeatures = field(default_factory=BehaviorFeatures)
    scores: dict[str, float] = field(default_factory=dict)


class BehaviorDetector:
    """
    Infer emitter behavior from receiver observations only.

    No ground truth, emitter identity, emitter type, or future information
    is used.
    """

    BEHAVIORS = (
        "fixed",
        "periodic",
        "bursty",
        "agile",
        "scanning",
        "unknown",
    )

    def __init__(
        self,
        recent_window: int = 20,
        min_hits: int = 4,
        periodic_cv_threshold: float = 0.25,
        scanning_adjacent_threshold: float = 0.70,
        scanning_direction_threshold: float = 0.70,
        agile_jump_threshold: float = 2.0,
    ):
        self.recent_window = max(1, recent_window)
        self.min_hits = max(2, min_hits)
        self.periodic_cv_threshold = periodic_cv_threshold
        self.scanning_adjacent_threshold = scanning_adjacent_threshold
        self.scanning_direction_threshold = scanning_direction_threshold
        self.agile_jump_threshold = agile_jump_threshold

    def extract_features(
        self,
        observations: list[dict],
        current_time: int | None = None,
    ) -> BehaviorFeatures:
        """
        Extract numerical behavior evidence.

        Required observation fields:
            time, band, detected

        Misses contribute to hit_ratio.

        Movement features use detected observations only because a miss
        does not tell us where an emitter actually was.
        """
        if not observations:
            return BehaviorFeatures()

        ordered = sorted(observations, key=lambda o: o["time"])

        if current_time is None:
            current_time = max(o["time"] for o in ordered)

        # Never use observations from the future.
        ordered = [
            o for o in ordered
            if o["time"] <= current_time
        ]

        if not ordered:
            return BehaviorFeatures()

        hits = [
            o for o in ordered
            if o.get("detected", False)
        ]

        hit_count = len(hits)
        hit_ratio = hit_count / len(ordered)

        hit_times = [o["time"] for o in hits]

        intervals = [
            b - a
            for a, b in zip(hit_times, hit_times[1:])
            if b > a
        ]

        mean_inter = mean(intervals) if intervals else 0.0

        if len(intervals) >= 2 and mean_inter > 0:
            inter_cv = pstdev(intervals) / mean_inter
        else:
            inter_cv = 0.0

        time_since_hit = (
            current_time - hit_times[-1]
            if hit_times
            else float("inf")
        )

        recent_start = current_time - self.recent_window + 1

        recent_hits = sum(
            1 for t in hit_times
            if t >= recent_start
        )

        recent_density = recent_hits / self.recent_window

        hit_bands = [o["band"] for o in hits]
        unique_bands = len(set(hit_bands))

        transitions = list(zip(hit_bands, hit_bands[1:]))

        transition_count = len(transitions)

        jumps = [
            abs(b - a)
            for a, b in transitions
        ]

        mean_jump = mean(jumps) if jumps else 0.0

        adjacent_ratio = (
            sum(j == 1 for j in jumps) / len(jumps)
            if jumps
            else 0.0
        )

        directions = [
            1 if b > a else -1 if b < a else 0
            for a, b in transitions
        ]

        nonzero_dirs = [
            d for d in directions
            if d != 0
        ]

        if nonzero_dirs:
            positive = sum(d == 1 for d in nonzero_dirs)
            negative = sum(d == -1 for d in nonzero_dirs)

            direction_consistency = (
                max(positive, negative) / len(nonzero_dirs)
            )
        else:
            direction_consistency = 0.0

        band_span = (
            max(hit_bands) - min(hit_bands)
            if hit_bands
            else 0
        )

        return BehaviorFeatures(
            hit_count=hit_count,
            hit_ratio=hit_ratio,
            time_since_hit=time_since_hit,
            mean_inter_hit=mean_inter,
            inter_hit_cv=inter_cv,
            recent_hit_density=recent_density,
            unique_hit_bands=unique_bands,
            transition_count=transition_count,
            mean_jump=mean_jump,
            adjacent_ratio=adjacent_ratio,
            direction_consistency=direction_consistency,
            band_span=band_span,
        )

    def analyze(
        self,
        observations: list[dict],
        current_time: int | None = None,
    ) -> BehaviorResult:

        features = self.extract_features(
            observations,
            current_time,
        )

        if features.hit_count < self.min_hits:
            unknown_confidence = max(
                0.0,
                1.0 - (
                    features.hit_count / self.min_hits
                ),
            )

            return BehaviorResult(
                behavior="unknown",
                confidence=unknown_confidence,
                features=features,
                scores={"unknown": unknown_confidence},
            )

        scores = {
            "fixed": 0.0,
            "periodic": 0.0,
            "bursty": 0.0,
            "agile": 0.0,
            "scanning": 0.0,
        }

        # --------------------------------------------------------------
        # Same-band behavior
        # --------------------------------------------------------------
        if features.unique_hit_bands == 1:

            scores["fixed"] = features.hit_ratio

            # Mean interval > 1 distinguishes temporal ON/OFF behavior
            # from a continuously active fixed emitter.
            if features.mean_inter_hit > 1:

                regularity = max(
                    0.0,
                    1.0 - min(
                        features.inter_hit_cv
                        / self.periodic_cv_threshold,
                        1.0,
                    ),
                )

                # Periodicity needs repeated intervals.
                detected_hit_count = len([
                    o for o in observations
                    if (
                        o.get("detected", False)
                        and (
                            current_time is None
                            or o["time"] <= current_time
                        )
                    )
                ])

                if detected_hit_count >= 3:

                    scores["periodic"] = (
                        regularity
                        * (1.0 - features.hit_ratio * 0.25)
                    )

                    scores["bursty"] = (
                        (1.0 - regularity)
                        * min(features.hit_ratio * 1.25, 1.0)
                    )

            # A continuously detected fixed emitter should remain fixed,
            # rather than being mislabeled periodic.
            if (
                features.hit_ratio >= 0.75
                and features.inter_hit_cv == 0.0
            ):
                scores["fixed"] = max(
                    scores["fixed"],
                    0.8,
                )

        
        # --------------------------------------------------------------
        # Cross-band behavior
        # --------------------------------------------------------------
        if (
            features.transition_count >= 2
            and features.unique_hit_bands >= 2
        ):

            hits = [
                o
                for o in sorted(
                    observations,
                    key=lambda o: o["time"],
                )
                if (
                    o.get("detected", False)
                    and (
                        current_time is None
                        or o["time"] <= current_time
                    )
                )
            ]

            transitions = list(zip(hits, hits[1:]))

            jumps = [
                abs(b["band"] - a["band"])
                for a, b in transitions
            ]

            if jumps:

                # ----------------------------------------------------------
                # Direction structure
                #
                # A scanner is locally ordered. It can either continue in
                # one direction or reverse direction in a ping-pong pattern.
                # Frequent reversals are therefore evidence against scanning.
                # ----------------------------------------------------------
                direction_changes = 0
                previous_direction = None

                for a, b in transitions:
                    delta = b["band"] - a["band"]

                    if delta == 0:
                        continue

                    direction = 1 if delta > 0 else -1

                    if (
                        previous_direction is not None
                        and direction != previous_direction
                    ):
                        direction_changes += 1

                    previous_direction = direction

                nonzero_transitions = sum(
                    a["band"] != b["band"]
                    for a, b in transitions
                )

                if nonzero_transitions >= 2:
                    reversal_rate = (
                        direction_changes
                        / (nonzero_transitions - 1)
                    )
                else:
                    reversal_rate = 0.0

                directional_structure = 1.0 - reversal_rate

                # ----------------------------------------------------------
                # Scanning
                #
                # Scanning requires mostly adjacent movement and a
                # reasonably structured direction. This supports both
                # forward scans and ping-pong scans.
                # ----------------------------------------------------------
                adjacent_ratio = (
                    sum(j == 1 for j in jumps)
                    / len(jumps)
                )

                scanning_score = (
                    adjacent_ratio
                    * directional_structure
                )

                if (
                    adjacent_ratio
                    >= self.scanning_adjacent_threshold
                    and directional_structure
                    >= self.scanning_direction_threshold
                ):
                    scores["scanning"] = scanning_score

                # ----------------------------------------------------------
                # Agile
                #
                # Agile behavior is characterized by substantial
                # non-local movement combined with frequent direction
                # changes. Confidence is also limited by the amount of
                # movement evidence available.
                # ----------------------------------------------------------
                large_jump_ratio = (
                    sum(
                        j >= self.agile_jump_threshold
                        for j in jumps
                    )
                    / len(jumps)
                )

                diversity = min(
                    features.unique_hit_bands / 3.0,
                    1.0,
                )

                non_adjacent_ratio = 1.0 - adjacent_ratio

                directional_irregularity = reversal_rate

                evidence_strength = min(
                    features.transition_count / 8.0,
                    1.0,
                )

                agile_score = (
                    large_jump_ratio
                    * diversity
                    * non_adjacent_ratio
                    * directional_irregularity
                    * max(evidence_strength, 0.5)
                )

                scores["agile"] = min(
                    max(agile_score, 0.0),
                    1.0,
                )
        # --------------------------------------------------------------
        # Classification
        # --------------------------------------------------------------
        # Strong temporal evidence takes precedence over generic
        # fixed activity.
        if scores["periodic"] >= 0.50:
            best_behavior = "periodic"
        elif scores["bursty"] >= 0.50:
            best_behavior = "bursty"
        else:
            best_behavior = max(
                scores,
                key=scores.get,
            )

        best_score = scores[best_behavior]

        # No sufficiently strong evidence.
        if best_score < 0.50:
            return BehaviorResult(
                behavior="unknown",
                confidence=max(
                    0.0,
                    1.0 - best_score,
                ),
                features=features,
                scores={
                    **scores,
                    "unknown": 1.0 - best_score,
                },
            )

        return BehaviorResult(
            behavior=best_behavior,
            confidence=min(
                max(best_score, 0.0),
                1.0,
            ),
            features=features,
            scores={
                **scores,
                "unknown": max(
                    0.0,
                    1.0 - best_score,
                ),
            },
        )