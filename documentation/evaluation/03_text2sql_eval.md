# Text2SQL Evaluation — DeepEval

## Overview

The **Text2SQL pipeline** converts natural language questions into SQL, executes them, and returns results. Evaluation uses **[DeepEval](https://docs.confident-ai.com/)** — a testing framework for LLM outputs — combined with direct SQL execution checks.

Unlike RAG (semantic similarity) or orchestrator (exact match), Text2SQL eval primarily focuses on **structural correctness** and **provable outcomes** — did the SQL run? Did it return the right shape of data? Did it hallucinate table names?

---

## Evaluation Architecture

```
Golden Dataset (CSV)
        │
        ├──► SQL Generation Pipeline
        │         │
        │         ├─ fetch_schema → generate_sql → validate_node
        │         └─ execute SQL against real SQLite DB
        │
        ├──► Structural Checks (no LLM needed)
        │         ├─ Did SQL execute without error?
        │         ├─ Did it use only valid tables/columns?
        │         └─ Did it return non-empty results?
        │
        └──► DeepEval LLM Checks (Gemini judge)
                  └─ Is the natural language answer correct for the question?
```

---

## Files

| File | Location | Purpose |
|---|---|---|
| `sql_golden.csv` | `backend/evaluation/datasets/` | 25 labelled SQL test cases |
| `eval_text2sql.py` | `backend/evaluation/` | Eval runner — DeepEval + structural |
| `03_text2sql_eval.md` | `documentation/evaluation/` | This document |

---

## Database Schema

The eval runs against the real `data/sales.db` SQLite database:

```
departments  : id, name
employees    : id, name, department_id, salary
sales        : id, employee_id, amount, date
customers    : id, name, email, location
```

Sample data includes 3 departments, 3 employees, 3 sales records, 4 customers.

---

## Metrics

### Structural Metrics (deterministic — no LLM needed)

| Metric | What it measures | Target |
|---|---|---|
| **SQL Execution Rate** | % of queries that run without DB error | ≥ 90% |
| **Hallucination Rate** | % of queries using non-existent tables/columns | ≤ 5% |
| **Empty Result Rate** | % of queries returning zero rows (may be valid) | ≤ 15% |
| **Unsafe SQL Rate** | % of queries containing DROP/DELETE/UPDATE | 0% |

### DeepEval LLM Metric (semantic)

| Metric | What it measures | Target |
|---|---|---|
| **Answer Correctness** | Does the generated natural language answer correctly reflect the SQL result? | ≥ 0.80 |

---

## Dataset Categories

| Category | Cases | Example |
|---|---|---|
| `aggregate` | 6 | Total revenue, average salary, count |
| `filter` | 5 | Employees with salary > 70000 |
| `join` | 5 | Sales joined with employee names |
| `group_by` | 4 | Revenue grouped by department |
| `hallucination_bait` | 5 | Questions mentioning non-existent columns/tables |

> **Hallucination bait** rows have `expected_valid=false` — the pipeline should reject these via `validate_node`, not generate bad SQL.

---

## Security Considerations

- No real production data in the golden dataset — all examples use the sample DB.
- Eval calls `generate_sql_query()` and `execute_node()` directly — no HTTP requests.
- The SQLite DB is read-only for eval purposes (only SELECT queries are tested).
- All secrets from `.env`, none hardcoded.

---

## How to Run

### Prerequisites
```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Install DeepEval (first time only)
pip install deepeval
```

### Run standalone
```powershell
# Quick dev run — 5 cases (structural checks only, no LLM judge)
python evaluation/eval_text2sql.py --limit 5

# Dev run with LLM-based answer correctness check
python evaluation/eval_text2sql.py --limit 5 --with-llm-check

# Run only hallucination bait cases
python evaluation/eval_text2sql.py --category hallucination_bait

# Full CI run (all 25 cases, thresholds enforced)
python evaluation/eval_text2sql.py
```

### Run via pytest (CI mode)
```powershell
pytest evaluation/eval_text2sql.py -v
```

---

## Threshold Policy (CI Gate)

| Metric | Fail if |
|---|---|
| SQL Execution Rate | < 90% |
| Hallucination Rate | > 5% |
| Unsafe SQL Rate | > 0% |

The `--with-llm-check` flag additionally enforces:

| Metric | Fail if |
|---|---|
| Answer Correctness (DeepEval) | < 0.80 |

---

## Steps to Run This Evaluation

### Step 1 — Install DeepEval
```powershell
pip install deepeval
```

### Step 2 — (Optional) Configure DeepEval API
DeepEval can run fully locally using your own LLM — no DeepEval cloud account needed:
```powershell
# No config needed when using --with-llm-check (uses your GOOGLE_API_KEY from .env)
# DeepEval Cloud login is OPTIONAL and not required for local eval
```

### Step 3 — Run structural eval first (fast, no LLM)
```powershell
python evaluation/eval_text2sql.py --limit 5
```

### Step 4 — Run with LLM answer check (slower, more thorough)
```powershell
python evaluation/eval_text2sql.py --limit 5 --with-llm-check
```

### Step 5 — Full CI run
```powershell
python evaluation/eval_text2sql.py
```
