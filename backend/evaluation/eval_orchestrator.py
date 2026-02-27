"""
Orchestrator Evaluation Script
================================
Evaluates the routing accuracy of the orchestrator_node by running
it against a curated golden dataset of labelled queries.

Usage:
    # Full run (70 cases) — used in CI
    python evaluation/eval_orchestrator.py

    # Quick dev run — first 10 cases only, thresholds skipped
    python evaluation/eval_orchestrator.py --limit 10

    # Run only one category
    python evaluation/eval_orchestrator.py --category clear_sql

    # Combine: first 5 cases from adversarial category
    python evaluation/eval_orchestrator.py --category adversarial --limit 5

    # Via pytest (CI mode, full run)
    pytest evaluation/eval_orchestrator.py -v

Available categories:
    clear_sql | clear_rag | clear_general | ambiguous_sql_rag | adversarial

Security:
    - No hardcoded secrets. All config loaded from .env via python-dotenv.
    - Calls orchestrator_node directly (no HTTP requests, no auth bypass).
    - Eval results written locally only (no external transmission).
    - Dataset path validated before reading.

CI Integration:
    Exit code 0 = all thresholds met (pass)
    Exit code 1 = one or more thresholds failed (fail)
    Note: --limit / --category flags disable threshold gates (dev mode only).
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path Bootstrap — ensure backend root is on sys.path when run directly
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Load environment variables BEFORE importing app modules
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

ENV_FILE = BACKEND_ROOT / ".env"
if not ENV_FILE.exists():
    print(f"[WARN] .env file not found at {ENV_FILE}. Falling back to OS environment.")
else:
    load_dotenv(dotenv_path=ENV_FILE)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("eval.orchestrator")

# ---------------------------------------------------------------------------
# Constants — thresholds for CI gate
# ---------------------------------------------------------------------------
ACCURACY_THRESHOLD: float = 0.95          # 95% overall accuracy required
PER_CLASS_RECALL_THRESHOLD: float = 0.85  # 85% recall per intent class required
DATASET_PATH = SCRIPT_DIR / "datasets" / "routing_golden.csv"
REPORTS_DIR = SCRIPT_DIR / "reports"
VALID_INTENTS = {"sql", "rag", "general"}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_golden_dataset(path: Path) -> list[dict]:
    """
    Load and validate the golden routing dataset from CSV.

    Each row must have: query, expected_intent, category, notes
    Rows with invalid intents are skipped with a warning.

    Args:
        path: Absolute path to the CSV file.

    Returns:
        List of validated dataset rows as dicts.

    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If the CSV is missing required columns.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Golden dataset not found at: {path}\n"
            "Ensure the file exists before running evaluation."
        )

    required_columns = {"query", "expected_intent", "category", "notes"}
    rows = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError("CSV file appears to be empty.")

        actual_columns = {col.strip().lower() for col in reader.fieldnames}
        missing = required_columns - actual_columns
        if missing:
            raise ValueError(
                f"CSV is missing required columns: {missing}. "
                f"Found: {actual_columns}"
            )

        for i, row in enumerate(reader, start=2):  # start=2 (row 1 = header)
            query = row.get("query", "").strip().strip('"')
            expected = row.get("expected_intent", "").strip().lower()
            category = row.get("category", "unknown").strip()
            notes = row.get("notes", "").strip()

            if not query:
                logger.warning("Row %d: Empty query, skipping.", i)
                continue

            if expected not in VALID_INTENTS:
                logger.warning(
                    "Row %d: Invalid expected_intent '%s', skipping.", i, expected
                )
                continue

            rows.append({
                "query": query,
                "expected_intent": expected,
                "category": category,
                "notes": notes,
            })

    logger.info("Loaded %d valid test cases from dataset.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Orchestrator Invocation
# ---------------------------------------------------------------------------

def run_orchestrator(query: str) -> tuple[str, Optional[str]]:
    """
    Invoke the production orchestrator_node with a minimal AgentState.

    Imports are deferred here so that app modules (and their config) load
    AFTER dotenv has been applied.

    Args:
        query: The natural language query to classify.

    Returns:
        Tuple of (predicted_intent, error_message).
        error_message is None on success, a string on failure.
    """
    try:
        # Deferred import — app config reads env vars at import time
        from app.agents.orchestrator import orchestrator_node

        # Minimal state — orchestrator only reads 'question' and 'session_id'
        state = {
            "question": query,
            "session_id": "eval-orchestrator",
            "messages": [],
            "intent": None,
            "retry_count": 0,
            "step_count": 0,
            "sql_valid": False,
            "error": None,
            "documents": None,
            "rag_answer": None,
            "schema": None,
            "plan": None,
            "sql_query": None,
            "sql_result": None,
            "visualization_spec": None,
            "requires_approval": False,
            "approval_status": None,
            "approval_request_id": None,
            "sensitive_tables": None,
            "agent_identity": {},
            "security_context": {},
        }

        result = orchestrator_node(state)
        predicted = result.get("intent", "").strip().lower()

        if predicted not in VALID_INTENTS:
            return "general", f"Unexpected intent value: '{predicted}', defaulted to 'general'"

        return predicted, None

    except Exception as exc:
        logger.error("orchestrator_node raised exception: %s", exc, exc_info=True)
        return "general", str(exc)


# ---------------------------------------------------------------------------
# Metrics Computation
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict]) -> dict:
    """
    Compute accuracy, per-class precision/recall/F1, and ambiguity subset accuracy.

    Args:
        results: List of result dicts from running the evaluation.

    Returns:
        Dictionary of computed metrics.
    """
    total = len(results)
    correct = sum(1 for r in results if r["passed"])

    # Per-class TP, FP, FN
    classes = list(VALID_INTENTS)
    stats = {cls: {"tp": 0, "fp": 0, "fn": 0} for cls in classes}

    for r in results:
        expected = r["expected_intent"]
        predicted = r["predicted_intent"]
        for cls in classes:
            if expected == cls and predicted == cls:
                stats[cls]["tp"] += 1
            elif expected != cls and predicted == cls:
                stats[cls]["fp"] += 1
            elif expected == cls and predicted != cls:
                stats[cls]["fn"] += 1

    per_class = {}
    for cls in classes:
        tp = stats[cls]["tp"]
        fp = stats[cls]["fp"]
        fn = stats[cls]["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        support = tp + fn  # total actual positives for this class
        per_class[cls] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "correct": tp,
            "total": support,
        }

    # Ambiguity subset
    ambiguous = [r for r in results if "ambiguous" in r.get("category", "")]
    ambiguity_accuracy = (
        sum(1 for r in ambiguous if r["passed"]) / len(ambiguous)
        if ambiguous
        else None
    )

    # Adversarial subset
    adversarial = [r for r in results if "adversarial" in r.get("category", "")]
    adversarial_accuracy = (
        sum(1 for r in adversarial if r["passed"]) / len(adversarial)
        if adversarial
        else None
    )

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total > 0 else 0.0,
        "per_class": per_class,
        "ambiguity_accuracy": round(ambiguity_accuracy, 4) if ambiguity_accuracy is not None else None,
        "adversarial_accuracy": round(adversarial_accuracy, 4) if adversarial_accuracy is not None else None,
    }


# ---------------------------------------------------------------------------
# Threshold Check (CI gate logic)
# ---------------------------------------------------------------------------

def check_thresholds(metrics: dict) -> tuple[bool, list[str]]:
    """
    Check computed metrics against defined CI thresholds.

    Args:
        metrics: Output from compute_metrics().

    Returns:
        Tuple of (passed: bool, failure_reasons: list[str])
    """
    failures = []

    if metrics["accuracy"] < ACCURACY_THRESHOLD:
        failures.append(
            f"Overall accuracy {metrics['accuracy']:.2%} is below threshold "
            f"{ACCURACY_THRESHOLD:.2%}"
        )

    for cls, data in metrics["per_class"].items():
        if data["recall"] < PER_CLASS_RECALL_THRESHOLD and data["total"] > 0:
            failures.append(
                f"Recall for '{cls}' is {data['recall']:.2%}, below threshold "
                f"{PER_CLASS_RECALL_THRESHOLD:.2%} (class has {data['total']} actual cases)"
            )

    return len(failures) == 0, failures


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def save_report(metrics: dict, results: list[dict], failures: list[str]) -> Path:
    """
    Save a full JSON evaluation report to the reports directory.

    Args:
        metrics: Computed metrics dictionary.
        results: Full list of per-case evaluation results.
        failures: List of threshold failure messages.

    Returns:
        Path to the saved report file.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"orchestrator_report_{timestamp}.json"

    report = {
        "evaluation": "orchestrator_routing",
        "timestamp": datetime.now().isoformat(),
        "dataset": str(DATASET_PATH),
        "thresholds": {
            "accuracy": ACCURACY_THRESHOLD,
            "per_class_recall": PER_CLASS_RECALL_THRESHOLD,
        },
        "metrics": metrics,
        "passed_thresholds": len(failures) == 0,
        "threshold_failures": failures,
        "failed_cases": [r for r in results if not r["passed"]],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_path


def print_report(metrics: dict, results: list[dict], failures: list[str]) -> None:
    """Print a human-readable summary to stdout."""
    sep = "=" * 50
    print(f"\n{sep}")
    print(" ORCHESTRATOR EVALUATION REPORT")
    print(sep)
    print(f"  Total Cases   : {metrics['total']}")
    print(f"  Passed        : {metrics['correct']}")
    print(f"  Failed        : {metrics['total'] - metrics['correct']}")
    print(f"  Accuracy      : {metrics['accuracy']:.2%}")
    print(f"\n--- Per-Intent Breakdown ---")
    for cls, data in metrics["per_class"].items():
        print(
            f"  {cls:<10}: Precision={data['precision']:.2f}  "
            f"Recall={data['recall']:.2f}  F1={data['f1']:.2f}  "
            f"({data['correct']}/{data['total']} correct)"
        )

    if metrics["ambiguity_accuracy"] is not None:
        print(f"\n--- Ambiguity Subset ---")
        print(f"  Accuracy: {metrics['ambiguity_accuracy']:.2%}")

    if metrics["adversarial_accuracy"] is not None:
        print(f"\n--- Adversarial Subset ---")
        print(f"  Accuracy: {metrics['adversarial_accuracy']:.2%}")

    failed_cases = [r for r in results if not r["passed"]]
    if failed_cases:
        print(f"\n--- Failed Cases ({len(failed_cases)}) ---")
        for i, r in enumerate(failed_cases, 1):
            print(f"\n  [{i}] Query    : {r['query'][:80]}")
            print(f"       Expected : {r['expected_intent']}")
            print(f"       Got      : {r['predicted_intent']}")
            print(f"       Category : {r['category']}")
            if r.get("error"):
                print(f"       Error    : {r['error']}")

    if failures:
        print(f"\n--- ⚠️  THRESHOLD FAILURES ---")
        for f in failures:
            print(f"  ✗ {f}")
        print(f"\n  Result: EVAL FAILED (exit code 1)")
    else:
        print(f"\n  Result: ✅ EVAL PASSED (all thresholds met)")


# ---------------------------------------------------------------------------
# Pytest-compatible test (for CI integration)
# ---------------------------------------------------------------------------

def test_orchestrator_routing_accuracy():
    """
    Pytest entry point. Asserts that orchestrator meets accuracy thresholds.
    Run with: pytest evaluation/eval_orchestrator.py -v
    """
    dataset = load_golden_dataset(DATASET_PATH)
    results = []

    for case in dataset:
        predicted, error = run_orchestrator(case["query"])
        results.append({
            **case,
            "predicted_intent": predicted,
            "passed": predicted == case["expected_intent"],
            "error": error,
        })

    metrics = compute_metrics(results)
    passed, failures = check_thresholds(metrics)

    # Print report even during pytest run for visibility
    print_report(metrics, results, failures)

    assert passed, (
        f"Orchestrator eval FAILED. Threshold violations:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# Main — run standalone
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments for standalone execution.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="Orchestrator Routing Evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python eval_orchestrator.py                          # Full run (CI)\n"
            "  python eval_orchestrator.py --limit 10              # Quick dev run\n"
            "  python eval_orchestrator.py --category adversarial  # One category\n"
            "  python eval_orchestrator.py --category clear_sql --limit 5"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Run only the first N test cases (dev mode). Disables CI threshold gates.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=["clear_sql", "clear_rag", "clear_general", "ambiguous_sql_rag", "adversarial"],
        help="Run only test cases from a specific category. Disables CI threshold gates.",
    )
    return parser.parse_args()


def main() -> int:
    """
    Main entry point for standalone execution.

    Args from CLI:
        --limit N         : Run only first N cases (dev mode)
        --category NAME   : Run only cases from one category (dev mode)

    Returns:
        0 if all thresholds pass (or dev mode), 1 if any threshold fails.
    """
    args = parse_args()
    is_dev_mode = args.limit is not None or args.category is not None

    logger.info("Starting Orchestrator Evaluation")
    logger.info("Dataset: %s", DATASET_PATH)

    if is_dev_mode:
        logger.info(
            "⚡ DEV MODE — limit=%s  category=%s  (CI thresholds disabled)",
            args.limit,
            args.category,
        )

    # Load data
    try:
        dataset = load_golden_dataset(DATASET_PATH)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load dataset: %s", e)
        return 1

    if not dataset:
        logger.error("Dataset is empty after validation. Aborting.")
        return 1

    # Apply --category filter
    if args.category:
        dataset = [row for row in dataset if row["category"] == args.category]
        if not dataset:
            logger.error(
                "No cases found for category '%s'. Check the CSV.", args.category
            )
            return 1
        logger.info("Filtered to category '%s': %d cases", args.category, len(dataset))

    # Apply --limit filter
    if args.limit is not None:
        if args.limit < 1:
            logger.error("--limit must be a positive integer. Got: %d", args.limit)
            return 1
        dataset = dataset[: args.limit]
        logger.info("Limited to first %d cases", len(dataset))

    # Run evaluation
    results = []
    logger.info("Running %d test cases...", len(dataset))

    for i, case in enumerate(dataset, 1):
        logger.info("[%d/%d] %s", i, len(dataset), case["query"][:70])
        predicted, error = run_orchestrator(case["query"])
        passed = predicted == case["expected_intent"]

        results.append({
            **case,
            "predicted_intent": predicted,
            "passed": passed,
            "error": error,
        })

        status = "✅" if passed else "❌"
        logger.info(
            "%s Expected=%-8s Got=%-8s", status, case["expected_intent"], predicted
        )

    # Compute metrics
    metrics = compute_metrics(results)

    if is_dev_mode:
        # Dev mode: skip threshold gate, just print results
        failures: list[str] = []
        print_report(metrics, results, failures)
        print("\n  ℹ️  Dev mode — CI thresholds skipped. Run without --limit/--category for full CI check.")
        report_path = save_report(metrics, results, failures)
        print(f"  Report saved to: {report_path}")
        return 0

    # Full CI mode: enforce thresholds
    passed_ci, failures = check_thresholds(metrics)
    print_report(metrics, results, failures)
    report_path = save_report(metrics, results, failures)
    print(f"\n  Full JSON report saved to: {report_path}")

    return 0 if passed_ci else 1


if __name__ == "__main__":
    sys.exit(main())
