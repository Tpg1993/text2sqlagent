"""
Text2SQL Evaluation Script — DeepEval + Structural Checks
===========================================================
Evaluates the Text2SQL pipeline using two complementary approaches:

  1. STRUCTURAL CHECKS (deterministic, no LLM needed):
       - SQL Execution Rate   : Did the SQL run without DB error?
       - Hallucination Rate   : Did validate_node catch bad tables/columns?
       - Empty Result Rate    : Did the query return non-empty rows?
       - Unsafe SQL Rate      : Did it ever generate DROP/DELETE/UPDATE?

  2. DEEPEVAL LLM CHECK (optional, --with-llm-check flag):
       - Answer Correctness   : Does the final answer correctly reflect the data?

Usage:
    # Structural only (fast, no LLM for judging — still uses LLM to generate SQL)
    python evaluation/eval_text2sql.py --limit 5

    # With DeepEval LLM answer correctness check
    python evaluation/eval_text2sql.py --limit 5 --with-llm-check

    # Run only hallucination bait cases
    python evaluation/eval_text2sql.py --category hallucination_bait

    # Full CI run (all 25, thresholds enforced)
    python evaluation/eval_text2sql.py

    # Via pytest
    pytest evaluation/eval_text2sql.py -v

Available categories:
    aggregate | filter | join | group_by | hallucination_bait

Security:
    - No hardcoded secrets. All config loaded from .env via python-dotenv.
    - Calls SQL generation and execution functions directly (no HTTP requests).
    - Eval runs only SELECT queries — the golden dataset contains no destructive SQL.
    - Results written locally to evaluation/reports/ only.

CI Integration:
    Exit code 0 = all thresholds met (pass)
    Exit code 1 = one or more thresholds failed (fail)
    Note: --limit / --category flags disable threshold gates (dev mode).
"""

import argparse
import csv
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Path Bootstrap
# ---------------------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).resolve().parent
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
logger = logging.getLogger("eval.text2sql")

# ---------------------------------------------------------------------------
# DeepEval availability check
# ---------------------------------------------------------------------------
try:
    from deepeval import evaluate as deepeval_evaluate
    from deepeval.test_case import LLMTestCase
    from deepeval.metrics import AnswerRelevancyMetric
    DEEPEVAL_AVAILABLE = True
except ImportError:
    DEEPEVAL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DATASET_PATH     = SCRIPT_DIR / "datasets" / "sql_golden.csv"
REPORTS_DIR      = SCRIPT_DIR / "eval_results"
VALID_CATEGORIES = {"aggregate", "filter", "join", "group_by", "hallucination_bait"}

# CI Thresholds
THRESHOLDS = {
    "sql_execution_rate":  0.90,   # ≥ 90% of valid queries must execute
    "hallucination_rate":  0.05,   # ≤ 5% hallucination allowed
    "unsafe_sql_rate":     0.00,   # 0% tolerance for DROP/DELETE/UPDATE
    "answer_correctness":  0.80,   # ≥ 0.80 when --with-llm-check used
}

# Unsafe SQL keywords — must never appear in generated queries
UNSAFE_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE"}

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_golden_dataset(path: Path) -> list[dict]:
    """
    Load and validate the SQL golden dataset from CSV.

    Required columns:
        question, expected_tables, expected_result_type,
        expected_valid, category, notes

    Args:
        path: Absolute path to the CSV file.

    Returns:
        List of validated rows as dicts.

    Raises:
        FileNotFoundError: If CSV doesn't exist.
        ValueError: If required columns are missing.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"SQL golden dataset not found at: {path}\n"
            "Ensure the file exists before running evaluation."
        )

    required_columns = {"question", "expected_tables", "expected_result_type",
                        "expected_valid", "category", "notes"}
    rows = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None:
            raise ValueError("CSV appears to be empty.")

        actual_columns = {col.strip().lower() for col in reader.fieldnames}
        missing = required_columns - actual_columns
        if missing:
            raise ValueError(f"CSV missing columns: {missing}. Found: {actual_columns}")

        for i, row in enumerate(reader, start=2):
            question       = row.get("question", "").strip().strip('"')
            expected_tables = row.get("expected_tables", "").strip()
            expected_valid  = row.get("expected_valid", "true").strip().lower() == "true"
            category        = row.get("category", "unknown").strip()
            notes           = row.get("notes", "").strip()

            if not question:
                logger.warning("Row %d: Empty question, skipping.", i)
                continue

            rows.append({
                "question":        question,
                "expected_tables": [t.strip().lower() for t in expected_tables.split("|") if t.strip()],
                "expected_valid":  expected_valid,
                "category":        category,
                "notes":           notes,
            })

    logger.info("Loaded %d SQL test cases.", len(rows))
    return rows


# ---------------------------------------------------------------------------
# SQL Pipeline Invocation
# ---------------------------------------------------------------------------

def run_sql_pipeline(question: str) -> dict:
    """
    Run the Text2SQL pipeline for a single question.

    Calls:
        1. get_schema_text()        → fetch DB schema
        2. generate_sql_query()     → LLM generates SQL
        3. validate_node()          → structural + schema validation
        4. execute SQL via SQLAlchemy (only if valid)

    Returns a dict with:
        sql_query     : The generated SQL string (or None)
        sql_result    : List of row dicts (or None)
        sql_valid     : bool — passed validation?
        error         : Error message (or None)
        hallucinated  : bool — validation rejected for hallucination?
        unsafe        : bool — contains unsafe keywords?
        pipeline_error: str — exception message if pipeline crashed
    """
    result = {
        "sql_query":      None,
        "sql_result":     None,
        "sql_valid":      False,
        "error":          None,
        "hallucinated":   False,
        "unsafe":         False,
        "pipeline_error": None,
    }

    try:
        from app.sql.schema import get_schema_text
        from app.sql.generator import generate_sql_query, generate_plan
        from app.agents.validate import validate_node
        from sqlalchemy import text as sa_text
        from app.db.session import engine

        # Step 1: Get schema
        schema = get_schema_text()

        # Step 2: Generate a plan, then SQL
        plan = generate_plan(
            schema=schema,
            question=question,
            tags=["eval", "sql", "planning"],
            metadata={"session_id": "eval-text2sql"},
        )

        sql = generate_sql_query(
            schema=schema,
            plan=plan,
            question=question,
            tags=["eval", "sql", "generation"],
            metadata={"session_id": "eval-text2sql"},
        )
        result["sql_query"] = sql

        # Step 3: Safety check — unsafe keywords
        sql_upper = sql.upper()
        if any(kw in sql_upper for kw in UNSAFE_KEYWORDS):
            result["unsafe"] = True
            result["error"] = f"Unsafe SQL generated containing restricted keywords."
            return result

        # Step 4: Validate (hallucination + destructive op check)
        minimal_state = {
            "sql_query": sql,
            "user_id":   "eval-text2sql",
            "session_id": "eval-text2sql",
            "question":   question,
        }
        validation = validate_node(minimal_state)  # type: ignore[arg-type]

        result["sql_valid"] = validation.get("sql_valid", False)
        result["error"]     = validation.get("error")

        # Check if rejection was due to hallucination
        if not result["sql_valid"] and result["error"]:
            if "hallucination" in result["error"].lower() or "does not exist" in result["error"].lower():
                result["hallucinated"] = True

        # Step 5: Execute only if valid (and not requiring HITL approval)
        if result["sql_valid"] and not validation.get("requires_approval", False):
            try:
                with engine.connect() as conn:
                    clean_sql = sql.replace("```sql", "").replace("```", "").strip().strip('"').strip("'")
                    db_result = conn.execute(sa_text(clean_sql))
                    rows = [dict(row._mapping) for row in db_result]
                    result["sql_result"] = rows
            except Exception as exec_err:
                result["sql_valid"] = False
                result["error"] = str(exec_err)

    except Exception as pipeline_err:
        logger.error("SQL pipeline exception: %s", pipeline_err, exc_info=True)
        result["pipeline_error"] = str(pipeline_err)

    return result


# ---------------------------------------------------------------------------
# DeepEval — Answer Correctness Check
# ---------------------------------------------------------------------------

def run_deepeval_check(question: str, sql_result: list[dict]) -> float:
    """
    Use DeepEval's AnswerRelevancyMetric to check whether the SQL result
    is a meaningful, correct answer to the original question.

    This uses your GOOGLE_API_KEY (Gemini) as the judge LLM.

    Args:
        question:   The original natural language question.
        sql_result: The rows returned by executing the SQL.

    Returns:
        Score from 0.0 to 1.0. Returns 0.0 if DeepEval not available or errors.
    """
    if not DEEPEVAL_AVAILABLE:
        logger.warning("DeepEval not installed — skipping LLM answer check.")
        return 0.0

    if not sql_result:
        return 0.0

    try:
        from app.config import settings
        from langchain_google_genai import ChatGoogleGenerativeAI
        from deepeval.models.base_model import DeepEvalBaseLLM

        # Wrap Gemini as a DeepEval-compatible judge
        class GeminiJudge(DeepEvalBaseLLM):
            def __init__(self):
                self._llm = ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GOOGLE_API_KEY,
                    temperature=0,
                )

            def load_model(self):
                return self._llm

            def generate(self, prompt: str) -> str:
                return self._llm.invoke(prompt).content

            async def a_generate(self, prompt: str) -> str:
                result = await self._llm.ainvoke(prompt)
                return result.content

            def get_model_name(self) -> str:
                return settings.GEMINI_MODEL

        # Format SQL result as readable context for the judge
        result_text = json.dumps(sql_result[:10], indent=2)  # Cap at 10 rows
        answer = f"The SQL query returned the following data:\n{result_text}"

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
        )

        metric = AnswerRelevancyMetric(
            threshold=THRESHOLDS["answer_correctness"],
            model=GeminiJudge(),
            include_reason=True,
        )
        metric.measure(test_case)
        return float(metric.score)

    except Exception as e:
        logger.warning("DeepEval check failed for '%s': %s", question[:50], e)
        return 0.0


# ---------------------------------------------------------------------------
# Metrics Computation
# ---------------------------------------------------------------------------

def compute_metrics(results: list[dict], with_llm_check: bool = False) -> dict:
    """
    Compute all structural metrics and optional DeepEval score average.

    Args:
        results:        Per-case evaluation results.
        with_llm_check: Whether DeepEval scores were computed.

    Returns:
        Dict of aggregated metrics.
    """
    total               = len(results)
    valid_cases         = [r for r in results if r["expected_valid"]]
    invalid_cases       = [r for r in results if not r["expected_valid"]]

    # Execution rate: among cases expected to be valid, how many executed OK?
    executed_ok = sum(
        1 for r in valid_cases
        if r["sql_result"] is not None and r["error"] is None
    )
    execution_rate = executed_ok / len(valid_cases) if valid_cases else 1.0

    # Hallucination rate: among ALL cases, how many hallucinated?
    hallucinated = sum(1 for r in results if r["hallucinated"])
    hallucination_rate = hallucinated / total if total else 0.0

    # Hallucination bait catch rate: among invalid cases, how many were CORRECTLY rejected?
    correctly_rejected = sum(1 for r in invalid_cases if not r["sql_valid"] or r["hallucinated"])
    bait_catch_rate = correctly_rejected / len(invalid_cases) if invalid_cases else 1.0

    # Unsafe SQL rate
    unsafe_count = sum(1 for r in results if r["unsafe"])
    unsafe_rate = unsafe_count / total if total else 0.0

    # Empty result rate (only for valid+executed cases)
    executed_cases = [r for r in valid_cases if r["sql_result"] is not None]
    empty_results = sum(1 for r in executed_cases if r["sql_result"] == [])
    empty_rate = empty_results / len(executed_cases) if executed_cases else 0.0

    # DeepEval answer correctness (optional)
    deepeval_scores = [r["deepeval_score"] for r in results if r.get("deepeval_score") is not None]
    avg_answer_correctness = (
        round(sum(deepeval_scores) / len(deepeval_scores), 4)
        if deepeval_scores else None
    )

    return {
        "total":                  total,
        "valid_cases":            len(valid_cases),
        "invalid_cases":          len(invalid_cases),
        "sql_execution_rate":     round(execution_rate, 4),
        "hallucination_rate":     round(hallucination_rate, 4),
        "bait_catch_rate":        round(bait_catch_rate, 4),
        "unsafe_sql_rate":        round(unsafe_rate, 4),
        "empty_result_rate":      round(empty_rate, 4),
        "avg_answer_correctness": avg_answer_correctness,
    }


# ---------------------------------------------------------------------------
# Threshold Check
# ---------------------------------------------------------------------------

def check_thresholds(metrics: dict, with_llm_check: bool = False) -> tuple[bool, list[str]]:
    """Check computed metrics against CI thresholds."""
    failures = []

    if metrics["sql_execution_rate"] < THRESHOLDS["sql_execution_rate"]:
        failures.append(
            f"SQL Execution Rate {metrics['sql_execution_rate']:.2%} < "
            f"threshold {THRESHOLDS['sql_execution_rate']:.2%}"
        )

    if metrics["hallucination_rate"] > THRESHOLDS["hallucination_rate"]:
        failures.append(
            f"Hallucination Rate {metrics['hallucination_rate']:.2%} > "
            f"threshold {THRESHOLDS['hallucination_rate']:.2%}"
        )

    if metrics["unsafe_sql_rate"] > THRESHOLDS["unsafe_sql_rate"]:
        failures.append(
            f"Unsafe SQL detected! Rate: {metrics['unsafe_sql_rate']:.2%}"
        )

    if with_llm_check and metrics["avg_answer_correctness"] is not None:
        if metrics["avg_answer_correctness"] < THRESHOLDS["answer_correctness"]:
            failures.append(
                f"Answer Correctness {metrics['avg_answer_correctness']:.4f} < "
                f"threshold {THRESHOLDS['answer_correctness']:.2f}"
            )

    return len(failures) == 0, failures


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def save_report(metrics: dict, results: list[dict], failures: list[str]) -> Path:
    """Save full JSON evaluation report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / "text2sql_eval_latest.json"

    report = {
        "evaluation":         "text2sql_deepeval",
        "timestamp":          datetime.now().isoformat(),
        "dataset":            "backend/evaluation/datasets/sql_golden.csv",
        "thresholds":         THRESHOLDS,
        "metrics":            metrics,
        "passed_thresholds":  len(failures) == 0,
        "threshold_failures": failures,
        "failed_cases": [
            r for r in results
            if r.get("error") or r.get("hallucinated") or r.get("unsafe")
        ],
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report_path


def print_report(metrics: dict, results: list[dict], failures: list[str]) -> None:
    """Print human-readable summary."""
    sep = "=" * 54
    print(f"\n{sep}")
    print(" TEXT2SQL EVALUATION REPORT (DeepEval)")
    print(sep)
    print(f"  Total Cases          : {metrics['total']}")
    print(f"  Expected Valid Cases : {metrics['valid_cases']}")
    print(f"  Hallucination Baits  : {metrics['invalid_cases']}")

    print(f"\n--- Structural Metrics ---")
    er = metrics["sql_execution_rate"]
    hr = metrics["hallucination_rate"]
    ur = metrics["unsafe_sql_rate"]
    bcr = metrics["bait_catch_rate"]
    emr = metrics["empty_result_rate"]

    print(f"  SQL Execution Rate   : {er:.2%}  {'✅' if er  >= THRESHOLDS['sql_execution_rate']  else '❌'}  (threshold: ≥{THRESHOLDS['sql_execution_rate']:.0%})")
    print(f"  Hallucination Rate   : {hr:.2%}  {'✅' if hr  <= THRESHOLDS['hallucination_rate']   else '❌'}  (threshold: ≤{THRESHOLDS['hallucination_rate']:.0%})")
    print(f"  Unsafe SQL Rate      : {ur:.2%}  {'✅' if ur  == 0.0                                else '❌'}  (threshold: 0%)")
    print(f"  Bait Catch Rate      : {bcr:.2%}  (% of hallucination bait correctly rejected)")
    print(f"  Empty Result Rate    : {emr:.2%}  (informational)")

    if metrics.get("avg_answer_correctness") is not None:
        ac = metrics["avg_answer_correctness"]
        print(f"\n--- DeepEval Metric ---")
        print(f"  Avg Answer Correctness : {ac:.4f}  "
              f"{'✅' if ac >= THRESHOLDS['answer_correctness'] else '❌'}  "
              f"(threshold: ≥{THRESHOLDS['answer_correctness']:.2f})")

    # Per-category breakdown
    categories: dict[str, list] = {}
    for r in results:
        categories.setdefault(r["category"], []).append(r)

    print(f"\n--- Per-Category Breakdown ---")
    for cat, cases in categories.items():
        executed = sum(1 for c in cases if c["sql_result"] is not None)
        halluc   = sum(1 for c in cases if c["hallucinated"])
        print(f"  {cat:<22}: executed={executed}/{len(cases)}  hallucinated={halluc}")

    # Failed cases
    failed = [r for r in results if r.get("error") and r.get("expected_valid")]
    if failed:
        print(f"\n--- Failed Cases (expected_valid=true but errored) ---")
        for i, r in enumerate(failed, 1):
            print(f"\n  [{i}] Question: {r['question'][:70]}")
            print(f"       SQL     : {str(r['sql_query'])[:80]}")
            print(f"       Error   : {r['error']}")

    if failures:
        print(f"\n--- ⚠️  THRESHOLD FAILURES ---")
        for f in failures:
            print(f"  ✗ {f}")
        print(f"\n  Result: EVAL FAILED (exit code 1)")
    else:
        print(f"\n  Result: ✅ EVAL PASSED (all thresholds met)")


# ---------------------------------------------------------------------------
# Pytest entry point
# ---------------------------------------------------------------------------

def test_text2sql_pipeline_quality():
    """
    Pytest entry point. Asserts Text2SQL pipeline meets structural thresholds.
    Run with: pytest evaluation/eval_text2sql.py -v
    """
    dataset = load_golden_dataset(DATASET_PATH)
    results = []

    for case in dataset:
        pipeline_result = run_sql_pipeline(case["question"])
        results.append({**case, **pipeline_result, "deepeval_score": None})

    metrics = compute_metrics(results, with_llm_check=False)
    passed, failures = check_thresholds(metrics, with_llm_check=False)
    print_report(metrics, results, failures)

    assert passed, (
        "Text2SQL eval FAILED. Threshold violations:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )


# ---------------------------------------------------------------------------
# CLI Argument Parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Text2SQL Pipeline Evaluation using DeepEval",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python eval_text2sql.py                                      # Full CI run\n"
            "  python eval_text2sql.py --limit 5                           # Quick dev run\n"
            "  python eval_text2sql.py --limit 5 --with-llm-check         # Dev + DeepEval\n"
            "  python eval_text2sql.py --category hallucination_bait      # Bait cases only\n"
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
    parser.add_argument(
        "--with-llm-check",
        action="store_true",
        default=False,
        help="Enable DeepEval answer correctness check (additional LLM calls).",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Main entry point. Returns 0 = pass, 1 = fail."""
    args = parse_args()
    is_dev_mode = args.limit is not None or args.category is not None

    if args.with_llm_check and not DEEPEVAL_AVAILABLE:
        print(
            "\n[ERROR] --with-llm-check requires DeepEval.\n"
            "Install it with:\n\n    pip install deepeval\n"
        )
        return 1

    logger.info("Starting Text2SQL Evaluation")
    if is_dev_mode:
        logger.info(
            "⚡ DEV MODE — limit=%s  category=%s  llm_check=%s",
            args.limit,
            args.category,
            args.with_llm_check,
        )

    # Load dataset
    try:
        dataset = load_golden_dataset(DATASET_PATH)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load dataset: %s", e)
        return 1

    # Apply filters
    if args.category:
        dataset = [r for r in dataset if r["category"] == args.category]
        if not dataset:
            logger.error("No cases found for category '%s'.", args.category)
            return 1
        logger.info("Filtered to category '%s': %d cases", args.category, len(dataset))

    if args.limit is not None:
        dataset = dataset[: args.limit]
        logger.info("Limited to first %d cases.", len(dataset))

    # Run pipeline
    results = []
    logger.info("Running Text2SQL pipeline for %d questions...", len(dataset))

    for i, case in enumerate(dataset, 1):
        logger.info("[%d/%d] %s", i, len(dataset), case["question"][:70])
        pipeline_result = run_sql_pipeline(case["question"])

        # Optional DeepEval check
        deepeval_score = None
        if args.with_llm_check and pipeline_result.get("sql_result"):
            deepeval_score = run_deepeval_check(case["question"], pipeline_result["sql_result"])

        status_icon = (
            "✅" if pipeline_result["sql_result"] is not None and not pipeline_result.get("error")
            else ("🚫" if pipeline_result["hallucinated"] else "❌")
        )
        logger.info(
            "  %s  valid=%s  hallucinated=%s  rows=%s",
            status_icon,
            pipeline_result["sql_valid"],
            pipeline_result["hallucinated"],
            len(pipeline_result["sql_result"]) if pipeline_result["sql_result"] else 0,
        )

        results.append({**case, **pipeline_result, "deepeval_score": deepeval_score})

    # Compute + report
    metrics = compute_metrics(results, with_llm_check=args.with_llm_check)

    if is_dev_mode:
        print_report(metrics, results, [])
        print(
            "\n  ℹ️  Dev mode — CI thresholds skipped. "
            "Run without --limit/--category for full CI check."
        )
        report_path = save_report(metrics, results, [])
        print(f"  Report saved to: {report_path}")
        return 0

    passed, failures = check_thresholds(metrics, with_llm_check=args.with_llm_check)
    print_report(metrics, results, failures)
    report_path = save_report(metrics, results, failures)
    print(f"\n  Full JSON report saved to: {report_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
