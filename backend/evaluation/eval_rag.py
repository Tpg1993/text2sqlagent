"""
RAG Evaluation Script — RAGAS
================================
Evaluates the RAG pipeline (retriever + generator) using the RAGAS framework.
RAGAS uses an LLM-as-a-judge internally to compute semantic quality metrics
without requiring exact-match answers.

Usage:
    # Full run (20 cases) — used in CI
    python evaluation/eval_rag.py

    # Quick dev run — first 5 cases only, thresholds skipped
    python evaluation/eval_rag.py --limit 5

    # Run only one category
    python evaluation/eval_rag.py --category return_policy

    # Via pytest (CI mode, full run)
    pytest evaluation/eval_rag.py -v

Available categories:
    return_policy | support_contact | shipping_policy | refund_policy | order_management

RAGAS Metrics:
    faithfulness      — Is the answer grounded in retrieved docs? (0-1)
    answer_relevancy  — Does the answer address the question? (0-1)
    context_precision — Are retrieved chunks relevant to the question? (0-1)
    context_recall    — Were all necessary facts retrieved? (0-1, needs ground_truth)

Security:
    - No hardcoded secrets. All config loaded from .env via python-dotenv.
    - Calls retriever and rag_gen_node directly (no HTTP requests).
    - Eval results written locally only (no external transmission).
    - Dataset must not contain real user PII.

CI Integration:
    Exit code 0 = all thresholds met (pass)
    Exit code 1 = one or more thresholds failed (fail)
    Note: --limit / --category flags disable threshold gates (dev mode only).
"""

import argparse
import csv
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path Bootstrap
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# ---------------------------------------------------------------------------
# Load .env BEFORE importing app modules
# ---------------------------------------------------------------------------
from dotenv import load_dotenv

ENV_FILE = BACKEND_ROOT / ".env"
if not ENV_FILE.exists():
    print(f"[WARN] .env not found at {ENV_FILE}. Falling back to OS environment.")
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
logger = logging.getLogger("eval.rag")

# ---------------------------------------------------------------------------
# RAGAS availability check — give a clear install message if missing
# ---------------------------------------------------------------------------
try:
    from ragas import evaluate as ragas_evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
    from ragas.llms import LangchainLLMWrapper
    from datasets import Dataset as HFDataset
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASET_PATH = SCRIPT_DIR / "datasets" / "rag_golden.csv"
REPORTS_DIR  = SCRIPT_DIR / "reports"
VALID_CATEGORIES = {
    "return_policy", "support_contact", "shipping_policy",
    "refund_policy", "order_management",
}

# CI Thresholds — adjust these as your RAG pipeline matures
THRESHOLDS = {
    "faithfulness":       0.80,
    "answer_relevancy":   0.75,
    "context_precision":  0.70,
    "context_recall":     0.70,
}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_golden_dataset(path: Path) -> list[dict]:
    """
    Load and validate the RAG golden dataset from CSV.

    Required columns: query, ground_truth, category, notes

    Args:
        path: Absolute path to the CSV file.

    Returns:
        List of validated rows as dicts.

    Raises:
        FileNotFoundError: If CSV does not exist.
        ValueError: If required columns are missing.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"RAG golden dataset not found at: {path}\n"
            "Ensure the file exists before running evaluation."
        )

    required_columns = {"query", "ground_truth", "category", "notes"}
    rows = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError("CSV appears to be empty.")

        actual_columns = {col.strip().lower() for col in reader.fieldnames}
        missing = required_columns - actual_columns
        if missing:
            raise ValueError(
                f"CSV missing required columns: {missing}. Found: {actual_columns}"
            )

        for i, row in enumerate(reader, start=2):
            query        = row.get("query", "").strip().strip('"')
            ground_truth = row.get("ground_truth", "").strip().strip('"')
            category     = row.get("category", "unknown").strip()
            notes        = row.get("notes", "").strip()

            if not query or not ground_truth:
                logger.warning("Row %d: Empty query or ground_truth, skipping.", i)
                continue

            rows.append({
                "query":        query,
                "ground_truth": ground_truth,
                "category":     category,
                "notes":        notes,
            })

    logger.info("Loaded %d valid RAG test cases.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# RAG Pipeline Invocation
# ---------------------------------------------------------------------------

def run_rag_pipeline(query: str) -> tuple[str, list[str], Optional[str]]:
    """
    Run the production RAG pipeline for a single query.

    Calls get_retriever() and rag_gen_node() directly — same functions
    used by the running application, without any HTTP requests.

    Args:
        query: Natural language question to answer via RAG.

    Returns:
        Tuple of (answer: str, contexts: list[str], error: str | None).
        On error, answer is empty string and error is the exception message.
    """
    try:
        from app.rag.retriever import get_retriever
        from app.agents.rag_generate import rag_gen_node

        # Step 1: Retrieve relevant document chunks
        retriever = get_retriever()
        docs = retriever.invoke(query)
        contexts = [doc.page_content for doc in docs]

        if not contexts:
            return "", [], "Retriever returned no documents. Check FAISS index."

        # Step 2: Generate answer from retrieved context
        state = {
            "question":         query,
            "documents":        docs,
            "session_id":       "eval-rag",
            # Minimal required state fields
            "messages":         [],
            "intent":           "rag",
            "retry_count":      0,
            "step_count":       0,
            "sql_valid":        False,
            "error":            None,
            "rag_answer":       None,
            "schema":           None,
            "plan":             None,
            "sql_query":        None,
            "sql_result":       None,
            "visualization_spec": None,
            "requires_approval":  False,
            "approval_status":    None,
            "approval_request_id": None,
            "sensitive_tables":   None,
            "agent_identity":     {},
            "security_context":   {},
        }

        result = rag_gen_node(state)
        answer = result.get("rag_answer", "").strip()

        if not answer:
            return "", contexts, "rag_gen_node returned empty answer."

        return answer, contexts, None

    except Exception as exc:
        logger.error("RAG pipeline error: %s", exc, exc_info=True)
        return "", [], str(exc)


# ---------------------------------------------------------------------------
# RAGAS Evaluation
# ---------------------------------------------------------------------------

def run_ragas_evaluation(cases: list[dict]) -> tuple[dict, list[dict]]:
    """
    Run RAGAS evaluation over a list of RAG pipeline results.

    Builds a HuggingFace Dataset and runs RAGAS evaluate() with
    four metrics: faithfulness, answer_relevancy, context_precision,
    context_recall.

    Args:
        cases: List of dicts with keys:
               query, ground_truth, category, answer, contexts

    Returns:
        Tuple of (aggregated_metrics: dict, per_case_results: list[dict])
    """
    from app.config import settings
    from langchain_google_genai import ChatGoogleGenerativeAI

    # Use Gemini as the RAGAS judge LLM
    judge_llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,  # Deterministic scoring
    )
    ragas_llm = LangchainLLMWrapper(judge_llm)

    # Wire judge LLM into each metric
    metrics = [faithfulness, answer_relevancy, context_precision, context_recall]
    for metric in metrics:
        metric.llm = ragas_llm

    logger.info("Running RAGAS with judge LLM: %s", settings.GEMINI_MODEL)

    # Build HuggingFace Dataset expected by RAGAS
    hf_data = {
        "question":   [c["query"] for c in cases],
        "answer":     [c["answer"] for c in cases],
        "contexts":   [c["contexts"] for c in cases],
        "ground_truth": [c["ground_truth"] for c in cases],
    }

    dataset = HFDataset.from_dict(hf_data)

    # Run RAGAS evaluation
    result = ragas_evaluate(dataset, metrics=metrics)
    result_df = result.to_pandas()

    # Build per-case results
    per_case = []
    for i, case in enumerate(cases):
        row = result_df.iloc[i]
        per_case.append({
            "query":             case["query"],
            "category":          case["category"],
            "answer":            case["answer"],
            "contexts_count":    len(case["contexts"]),
            "faithfulness":      round(float(row.get("faithfulness",  0)), 4),
            "answer_relevancy":  round(float(row.get("answer_relevancy", 0)), 4),
            "context_precision": round(float(row.get("context_precision", 0)), 4),
            "context_recall":    round(float(row.get("context_recall", 0)), 4),
            "error":             case.get("error"),
        })

    # Aggregate means
    agg = {
        metric_name: round(
            sum(c[metric_name] for c in per_case) / len(per_case), 4
        )
        for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
    }
    agg["total_cases"] = len(per_case)

    return agg, per_case


# ---------------------------------------------------------------------------
# Threshold Check
# ---------------------------------------------------------------------------

def check_thresholds(agg: dict) -> tuple[bool, list[str]]:
    """
    Check aggregated RAGAS metrics against CI thresholds.

    Args:
        agg: Aggregated metrics from run_ragas_evaluation().

    Returns:
        Tuple of (passed: bool, failure_reasons: list[str])
    """
    failures = []
    for metric, threshold in THRESHOLDS.items():
        score = agg.get(metric, 0.0)
        if score < threshold:
            failures.append(
                f"{metric}: {score:.4f} < threshold {threshold:.2f}"
            )
    return len(failures) == 0, failures


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def save_report(agg: dict, per_case: list[dict], failures: list[str]) -> Path:
    """Save full JSON evaluation report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"rag_report_{timestamp}.json"

    report = {
        "evaluation":        "rag_ragas",
        "timestamp":         datetime.now().isoformat(),
        "dataset":           str(DATASET_PATH),
        "thresholds":        THRESHOLDS,
        "aggregated_metrics": agg,
        "passed_thresholds": len(failures) == 0,
        "threshold_failures": failures,
        "per_case_results":  per_case,
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_path


def print_report(agg: dict, per_case: list[dict], failures: list[str]) -> None:
    """Print a human-readable summary to stdout."""
    sep = "=" * 52
    print(f"\n{sep}")
    print(" RAG EVALUATION REPORT (RAGAS)")
    print(sep)
    print(f"  Cases Evaluated : {agg['total_cases']}")

    print(f"\n--- RAGAS Metrics (avg across all cases) ---")
    for metric, threshold in THRESHOLDS.items():
        score = agg.get(metric, 0.0)
        status = "✅" if score >= threshold else "❌"
        print(
            f"  {metric:<22}: {score:.4f}  {status}  (threshold: {threshold:.2f})"
        )

    # Per-category breakdown
    categories: dict[str, list] = {}
    for c in per_case:
        categories.setdefault(c["category"], []).append(c)

    if categories:
        print(f"\n--- Per-Category Breakdown ---")
        for cat, cases in categories.items():
            avg_faith = sum(c["faithfulness"] for c in cases) / len(cases)
            avg_rel   = sum(c["answer_relevancy"] for c in cases) / len(cases)
            print(
                f"  {cat:<22}: faithfulness={avg_faith:.2f}  "
                f"answer_relevancy={avg_rel:.2f}  ({len(cases)} cases)"
            )

    # Low-scoring cases
    low_quality = [
        c for c in per_case
        if c["faithfulness"] < THRESHOLDS["faithfulness"]
        or c["answer_relevancy"] < THRESHOLDS["answer_relevancy"]
    ]
    if low_quality:
        print(f"\n--- Low-Quality Cases ({len(low_quality)}) ---")
        for i, c in enumerate(low_quality, 1):
            print(f"\n  [{i}] Query      : {c['query'][:80]}")
            print(f"       Faithfulness: {c['faithfulness']:.4f}")
            print(f"       Relevancy   : {c['answer_relevancy']:.4f}")
            if c.get("error"):
                print(f"       Error       : {c['error']}")

    if failures:
        print(f"\n--- ⚠️  THRESHOLD FAILURES ---")
        for f in failures:
            print(f"  ✗ {f}")
        print(f"\n  Result: EVAL FAILED (exit code 1)")
    else:
        print(f"\n  Result: ✅ EVAL PASSED (all thresholds met)")


# ---------------------------------------------------------------------------
# Pytest-compatible test (CI integration)
# ---------------------------------------------------------------------------

def test_rag_pipeline_quality():
    """
    Pytest entry point. Asserts RAG pipeline meets RAGAS quality thresholds.
    Run with: pytest evaluation/eval_rag.py -v
    """
    if not RAGAS_AVAILABLE:
        raise ImportError(
            "RAGAS is not installed. Run: pip install ragas\n"
            "Then re-run: pytest evaluation/eval_rag.py -v"
        )

    dataset = load_golden_dataset(DATASET_PATH)
    pipeline_results = []

    for case in dataset:
        answer, contexts, error = run_rag_pipeline(case["query"])
        pipeline_results.append({**case, "answer": answer, "contexts": contexts, "error": error})

    agg, per_case = run_ragas_evaluation(pipeline_results)
    passed, failures = check_thresholds(agg)
    print_report(agg, per_case, failures)

    assert passed, (
        "RAG eval FAILED. Threshold violations:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="RAG Pipeline Evaluation using RAGAS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python eval_rag.py                             # Full CI run\n"
            "  python eval_rag.py --limit 5                  # Quick dev run\n"
            "  python eval_rag.py --category return_policy   # One category\n"
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Run only the first N test cases (dev mode). Disables CI thresholds.",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=list(VALID_CATEGORIES),
        help="Run only cases from a specific category. Disables CI thresholds.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main — standalone execution
# ---------------------------------------------------------------------------

def main() -> int:
    """
    Main entry point.

    Returns:
        0 = pass, 1 = fail or error.
    """
    # RAGAS must be installed
    if not RAGAS_AVAILABLE:
        print(
            "\n[ERROR] RAGAS is not installed.\n"
            "Install it with:\n\n"
            "    pip install ragas\n\n"
            "Then re-run this script."
        )
        return 1

    args = parse_args()
    is_dev_mode = args.limit is not None or args.category is not None

    logger.info("Starting RAG Evaluation (RAGAS)")
    if is_dev_mode:
        logger.info(
            "⚡ DEV MODE — limit=%s  category=%s  (CI thresholds disabled)",
            args.limit,
            args.category,
        )

    # Load dataset
    try:
        dataset = load_golden_dataset(DATASET_PATH)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load dataset: %s", e)
        return 1

    # Category filter
    if args.category:
        dataset = [r for r in dataset if r["category"] == args.category]
        if not dataset:
            logger.error("No cases found for category '%s'.", args.category)
            return 1
        logger.info("Filtered to category '%s': %d cases", args.category, len(dataset))

    # Limit filter
    if args.limit is not None:
        if args.limit < 1:
            logger.error("--limit must be a positive integer.")
            return 1
        dataset = dataset[: args.limit]
        logger.info("Limited to first %d cases", len(dataset))

    # Run RAG pipeline for each case
    logger.info("Running RAG pipeline for %d queries...", len(dataset))
    pipeline_results = []

    for i, case in enumerate(dataset, 1):
        logger.info("[%d/%d] %s", i, len(dataset), case["query"][:70])
        answer, contexts, error = run_rag_pipeline(case["query"])
        if error:
            logger.warning("  ⚠️  Pipeline error: %s", error)
        pipeline_results.append({
            **case,
            "answer":   answer,
            "contexts": contexts,
            "error":    error,
        })

    # Filter out cases that errored (can't evaluate without answer/contexts)
    valid_results = [r for r in pipeline_results if r["answer"] and r["contexts"]]
    skipped = len(pipeline_results) - len(valid_results)
    if skipped > 0:
        logger.warning("%d case(s) skipped due to pipeline errors.", skipped)

    if not valid_results:
        logger.error("All cases failed. Check FAISS index and API key.")
        return 1

    # RAGAS evaluation
    logger.info("Running RAGAS evaluation on %d valid cases...", len(valid_results))
    try:
        agg, per_case = run_ragas_evaluation(valid_results)
    except Exception as e:
        logger.error("RAGAS evaluation failed: %s", e, exc_info=True)
        return 1

    # Report
    if is_dev_mode:
        print_report(agg, per_case, [])
        print(
            "\n  ℹ️  Dev mode — CI thresholds skipped. "
            "Run without --limit/--category for full CI check."
        )
        report_path = save_report(agg, per_case, [])
        print(f"  Report saved to: {report_path}")
        return 0

    passed, failures = check_thresholds(agg)
    print_report(agg, per_case, failures)
    report_path = save_report(agg, per_case, failures)
    print(f"\n  Full JSON report saved to: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
