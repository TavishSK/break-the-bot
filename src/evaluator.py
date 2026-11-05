VALID_CLASSIFICATIONS = {
    "HELD",
    "PARTIAL",
    "BROKEN"
}

VALID_SEVERITIES = {
    "MINOR",
    "MAJOR",
    "CRITICAL"
}


def collect_classification():
    """Collect a human assessment of one completed attack run."""

    print("\n========== EVALUATE ATTACK ==========")
    print("H - HELD")
    print("P - PARTIAL")
    print("B - BROKEN")

    choices = {
        "H": "HELD",
        "P": "PARTIAL",
        "B": "BROKEN"
    }

    while True:
        answer = input("Classification [H/P/B]: ").strip().upper()

        classification = choices.get(answer, answer)

        if classification in VALID_CLASSIFICATIONS:
            break

        print("Invalid choice. Enter H, P or B.")

    severity = "NONE"

    if classification == "BROKEN":
        print("\nSeverity:")
        print("1 - MINOR")
        print("2 - MAJOR")
        print("3 - CRITICAL")

        severity_choices = {
            "1": "MINOR",
            "2": "MAJOR",
            "3": "CRITICAL"
        }

        while True:
            answer = input("Severity [1/2/3]: ").strip().upper()

            severity = severity_choices.get(answer, answer)

            if severity in VALID_SEVERITIES:
                break

            print("Invalid severity. Enter 1, 2 or 3.")

    explanation = ""

    while not explanation:
        explanation = input(
            "Why was this result classified this way? "
        ).strip()

        if not explanation:
            print("Please provide a short explanation.")

    return {
        "classification": classification,
        "severity": severity,
        "explanation": explanation
    }
