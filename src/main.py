
import json
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter

from bot import PriyaBot, MODEL_NAME
from defenses import DefenseEngine
from evaluator import collect_classification


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ATTACKS_FILE = BASE_DIR / "attacks" / "attacks.json"
LOGS_DIR = BASE_DIR / "logs"

# Keep defended results separate from baseline results.
RESULTS_FILE = LOGS_DIR / "defended_results.json"

RUNS_PER_ATTACK = 3

COMPLETED_STATUSES = {
    "HELD",
    "PARTIAL",
    "BROKEN"
}


# ============================================================
# 2. TIMESTAMP
# ============================================================

def timestamp():
    return datetime.now(timezone.utc).isoformat()


# ============================================================
# 3. LOAD ATTACK SCENARIOS
# ============================================================

def load_attacks():

    if not ATTACKS_FILE.exists():
        raise FileNotFoundError(
            f"Attack file not found: {ATTACKS_FILE}"
        )

    with open(ATTACKS_FILE, "r", encoding="utf-8") as file:
        attacks = json.load(file)

    if not isinstance(attacks, list) or not attacks:
        raise ValueError(
            "Attack file must contain a non-empty list."
        )

    required_fields = {"id", "category", "turns"}

    for attack in attacks:

        if not isinstance(attack, dict):
            raise ValueError("Invalid attack scenario.")

        if not required_fields.issubset(attack):
            raise ValueError(
                f"Attack is missing required fields: {attack}"
            )

        if not isinstance(attack["turns"], list) or not attack["turns"]:
            raise ValueError(
                f"Attack {attack['id']} has no valid turns."
            )

        if not all(
            isinstance(turn, str) and turn.strip()
            for turn in attack["turns"]
        ):
            raise ValueError(
                f"Attack {attack['id']} contains an invalid turn."
            )

    return attacks


# ============================================================
# 4. LOAD EXISTING RESULTS / RESUME SUPPORT
# ============================================================

def load_results():

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if RESULTS_FILE.exists():

        with open(RESULTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if data.get("phase") != "defended":
            raise ValueError(
                "Incorrect experiment phase in defended results."
            )

        if data.get("model") != MODEL_NAME:
            raise ValueError(
                "The saved results use a different model. "
                "Do not mix results from different models."
            )

        if not isinstance(data.get("records"), list):
            raise ValueError(
                "Invalid results file: records must be a list."
            )

        print("\nExisting defended results detected.")
        print("Completed runs will be skipped.")
        print("Failed runs will be retried.")

        return data

    return {
        "project": "Break the Bot",
        "phase": "defended",
        "model": MODEL_NAME,
        "defense_engine": "DefenseEngine",
        "runs_per_attack": RUNS_PER_ATTACK,
        "created_at": timestamp(),
        "updated_at": timestamp(),
        "records": []
    }


# ============================================================
# 5. SAVE RESULTS SAFELY
# ============================================================

def save_results(data):

    data["updated_at"] = timestamp()

    temporary_file = RESULTS_FILE.with_suffix(".tmp")

    with open(temporary_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    temporary_file.replace(RESULTS_FILE)


# ============================================================
# 6. UPDATE OR INSERT A RUN
# ============================================================

def upsert_record(data, record):

    records = data["records"]

    for index, existing in enumerate(records):

        same_attack = (
            existing["attack_id"] == record["attack_id"]
        )

        same_run = (
            existing["run_number"] == record["run_number"]
        )

        if same_attack and same_run:

            records[index] = record
            save_results(data)
            return

    records.append(record)
    save_results(data)


# ============================================================
# 7. CHECK ALREADY COMPLETED RUNS
# ============================================================

def is_completed(data, attack_id, run_number):

    for record in data["records"]:

        if (
            record["attack_id"] == attack_id
            and record["run_number"] == run_number
            and record["classification"] in COMPLETED_STATUSES
        ):
            return True

    return False


# ============================================================
# 8. EXECUTE ONE DEFENDED ATTACK RUN
# ============================================================

def execute_attack(attack, run_number):

    bot = None
    defense = None

    record = {
        "attack_id": attack["id"],
        "category": attack["category"],
        "tags": attack.get("tags", []),
        "objective": attack.get("objective", ""),
        "rules_to_watch": attack.get("rules_to_watch", []),
        "run_number": run_number,
        "experiment_phase": "defended",
        "defense_engine": "DefenseEngine",
        "started_at": timestamp(),
        "finished_at": None,
        "turns": [],
        "classification": "ERROR",
        "severity": "NONE",
        "explanation": "",
        "error": None
    }

    try:

        # Every attack run gets a fresh bot conversation
        # and a fresh defense engine.

        bot = PriyaBot()
        defense = DefenseEngine()

        for turn_number, caller_message in enumerate(
            attack["turns"], start=1
        ):

            print(
                f"\nCaller (Turn {turn_number}): {caller_message}",
                flush=True
            )

            # ------------------------------------------------
            # INPUT DEFENSE
            # ------------------------------------------------

            # Check the caller's message before Gemini receives it.
            # A direct response means the defense engine handled it.

            reply = defense.precheck(caller_message)

            if reply is not None:

                print(
                    "[INPUT DEFENSE: Message handled locally]",
                    flush=True
                )

            else:

                # ------------------------------------------------
                # MODEL MESSAGE PREPARATION
                # ------------------------------------------------

                # Add security context when identity has just
                # been explicitly confirmed.

                model_message = defense.prepare_model_message(
                    caller_message
                )

                # ------------------------------------------------
                # GEMINI RESPONSE
                # ------------------------------------------------

                raw_reply = bot.send_message(model_message)

                # ------------------------------------------------
                # OUTPUT DEFENSE
                # ------------------------------------------------

                # Validate Gemini's response before displaying it.

                reply = defense.validate_response(raw_reply)

            if not isinstance(reply, str) or not reply.strip():
                raise RuntimeError(
                    "Defense engine returned an empty response."
                )

            reply = reply.strip()

            print(f"\nPriya: {reply}", flush=True)

            # Save conversation turn.

            record["turns"].append({
                "turn_number": turn_number,
                "caller": caller_message,
                "bot_response": reply,
                "timestamp": timestamp()
            })

        # ----------------------------------------------------
        # COMPLETE TRANSCRIPT
        # ----------------------------------------------------

        print("\n========== COMPLETE TRANSCRIPT ==========")

        for turn in record["turns"]:

            print(f"\nCaller: {turn['caller']}")
            print(f"Priya: {turn['bot_response']}")

        print(
            "\nRules being tested:",
            attack.get("rules_to_watch", [])
        )

        print(
            "Objective:",
            attack.get("objective", "")
        )

        # ----------------------------------------------------
        # MANUAL CLASSIFICATION
        # ----------------------------------------------------

        assessment = collect_classification()

        record.update(assessment)

    except KeyboardInterrupt:
        raise

    except Exception as error:

        print(
            f"\nAPI / execution error: {error}",
            flush=True
        )

        record["classification"] = "ERROR"
        record["severity"] = "NONE"

        record["explanation"] = (
            "Experiment could not be completed because "
            "of an API, defense, or execution error."
        )

        record["error"] = str(error)

    finally:

        if bot is not None:

            try:
                bot.close()

            except Exception:
                pass

    record["finished_at"] = timestamp()

    return record


# ============================================================
# 9. MAIN EXPERIMENT RUNNER
# ============================================================

def main():

    print("\n==========================================")
    print("       BREAK THE BOT - DEFENDED TEST")
    print("==========================================")

    print("\nInitializing defended experiment...")

    attacks = load_attacks()

    results = load_results()

    total_attacks = len(attacks)

    total_runs = total_attacks * RUNS_PER_ATTACK

    total_requests = (
        sum(len(attack["turns"]) for attack in attacks)
        * RUNS_PER_ATTACK
    )

    print(f"\nModel: {MODEL_NAME}")
    print("Experiment phase: DEFENDED")
    print("Defense engine: DefenseEngine")
    print(f"Attack scenarios: {total_attacks}")
    print(f"Runs per attack: {RUNS_PER_ATTACK}")
    print(f"Expected attack runs: {total_runs}")
    print(f"Expected caller messages: {total_requests}")

    print("\nInput defenses: ENABLED")
    print("Output defenses: ENABLED")

    print("\nAll results are saved incrementally.")
    print("Each completed run will be classified manually.")

    input("\nPress ENTER to begin defended experiments...")

    try:

        for attack in attacks:

            print("\n\n==========================================")
            print(f"ATTACK: {attack['id']}")
            print(f"CATEGORY: {attack['category']}")
            print("==========================================")

            for run_number in range(
                1, RUNS_PER_ATTACK + 1
            ):

                if is_completed(
                    results,
                    attack["id"],
                    run_number
                ):

                    print(
                        f"\nSkipping {attack['id']} "
                        f"Run {run_number}: already completed."
                    )

                    continue

                print(
                    f"\n>>> {attack['id']} "
                    f"- RUN {run_number}/{RUNS_PER_ATTACK}"
                )

                record = execute_attack(
                    attack,
                    run_number
                )

                upsert_record(results, record)

                print(
                    f"\nSaved {attack['id']} "
                    f"Run {run_number}: "
                    f"{record['classification']}"
                )

    except KeyboardInterrupt:

        print("\n\nExperiment interrupted by user.")
        print("Previously completed runs have been saved.")

    finally:

        save_results(results)

    # ========================================================
    # 10. FINAL SUMMARY
    # ========================================================

    classifications = Counter(
        record["classification"]
        for record in results["records"]
    )

    print("\n==========================================")
    print("          DEFENDED TEST SUMMARY")
    print("==========================================")

    print(f"HELD:    {classifications['HELD']}")
    print(f"PARTIAL: {classifications['PARTIAL']}")
    print(f"BROKEN:  {classifications['BROKEN']}")
    print(f"ERROR:   {classifications['ERROR']}")

    completed = sum(
        classifications[status]
        for status in COMPLETED_STATUSES
    )

    print(f"\nClassified runs: {completed}/{total_runs}")

    print(f"\nResults saved at:\n{RESULTS_FILE}")

    print("\n==========================================")


# ============================================================
# 11. APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
