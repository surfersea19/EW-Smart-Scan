from backend.prediction.behavior_detector import BehaviorDetector


def obs(t, band, detected=True):
    return {
        "time": t,
        "band": band,
        "detected": detected,
    }


def main():
    detector = BehaviorDetector()

    cases = {
        "FIXED": [
            obs(t, 10) for t in range(1, 11)
        ],

        "PERIODIC": [
            obs(t, 10) for t in [1, 4, 7, 10, 13, 16]
        ],

        "BURSTY": [
            obs(t, 10) for t in [1, 2, 7, 8, 15, 16]
        ],

        "SCANNING": [
            obs(t, band) for t, band in enumerate(
                [20, 21, 22, 23, 24, 25],
                start=1,
            )
        ],

        "AGILE": [
            obs(t, band) for t, band in enumerate(
                [10, 30, 12, 35, 11, 32],
                start=1,
            )
        ],
    }

    print("=" * 70)
    print("PHASE 7C — CONTROLLED BEHAVIOR VALIDATION")
    print("=" * 70)

    for expected, observations in cases.items():
        current_time = max(o["time"] for o in observations)

        result = detector.analyze(
            observations,
            current_time=current_time,
        )

        print(f"\nExpected : {expected}")
        print(f"Detected : {result.behavior.upper()}")
        print(f"Confidence: {result.confidence:.3f}")
        print(f"Features : {result.features}")
        print("Scores   :")

        for behavior, score in result.scores.items():
            print(f"  {behavior:8s}: {score:.3f}")


if __name__ == "__main__":
    main()
