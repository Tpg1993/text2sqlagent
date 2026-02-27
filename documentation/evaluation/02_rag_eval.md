# RAG Evaluation — RAGAS

## Overview

The **RAG pipeline** retrieves relevant document chunks from FAISS and generates an answer grounded in those chunks. Evaluation uses **[RAGAS](https://docs.ragas.io/)** — a framework purpose-built for RAG systems that uses an LLM as a judge internally to compute semantic metrics without requiring exact-match answers.

---

## How RAGAS Works in This Project

```
Query
  │
  ▼
FAISS Retriever (k=3, Gemini embeddings)   ← measures context_precision / context_recall
  │
  ▼
RAG Generate Node (LLM answers from docs)  ← measures faithfulness / answer_relevancy
  │
  ▼
RAGAS LLM Judge (Gemini Flash)             ← computes all four scores
  │
  ▼
Evaluation Report (JSON + console)
```

---

## Files

| File | Location | Purpose |
|---|---|---|
| `rag_golden.csv` | `backend/evaluation/datasets/` | 20 Q&A pairs with reference answers |
| `eval_rag.py` | `backend/evaluation/` | Eval runner using RAGAS |
| `02_rag_eval.md` | `documentation/evaluation/` | This document |

---

## RAGAS Metrics

| Metric | What it measures | How |
|---|---|---|
| **faithfulness** | Is the answer 100% grounded in the retrieved context? | Judge LLM checks for statements not supported by retrieved docs |
| **answer_relevancy** | Does the answer actually address the question asked? | Judge LLM rates if the answer is on-topic |
| **context_precision** | Are the retrieved chunks actually useful for answering? | Judge LLM checks if retrieved chunks are relevant to the question |
| **context_recall** | Were all necessary facts retrieved? | Judge LLM cross-checks answer against ground truth reference |

All scores are **0.0 to 1.0** — higher is better.

> **Note:** `context_recall` requires a `ground_truth` reference answer — this is why our golden dataset includes one.

---

## Dataset Design

The 20 Q&A pairs are drawn from the `support.pdf` document (the same document ingested into FAISS). They cover five policy categories:

| Category | Cases | Examples |
|---|---|---|
| `return_policy` | 5 | How to return, return window, exclusions |
| `support_contact` | 4 | Contact channels, hours, escalation |
| `shipping_policy` | 5 | Methods, duration, tracking, damage |
| `refund_policy` | 3 | Timeline, amount, defective goods |
| `order_management` | 3 | Cancel, address change |

> **Security:** All golden data is synthetic — no real customer PII. Follows the same principle as the orchestrator dataset.

---

## Security Considerations

- No API keys hardcoded. All secrets loaded from `.env`.
- The eval script calls `get_retriever()` and `rag_gen_node()` directly — no HTTP requests to the running server.
- RAGAS uses your `GOOGLE_API_KEY` for the judge LLM (Gemini). This is the same key already in `.env`.
- Reports written locally to `evaluation/reports/` only.
- Dataset must not contain any real user data or production document contents.

---

## How to Run

### Prerequisites
```powershell
cd "c:\Users\Tejas\Downloads\APPS\text2sql rag\backend"
.\.venv\Scripts\Activate.ps1

# Install RAGAS (first time only)
pip install ragas
```

### Run standalone
```powershell
# Full run (20 cases — ~20 LLM calls for retrieval + generation + judging)
python evaluation/eval_rag.py

# Quick dev run — first 5 cases only
python evaluation/eval_rag.py --limit 5

# Run only one category
python evaluation/eval_rag.py --category return_policy
```

### Run via pytest (CI mode)
```powershell
pytest evaluation/eval_rag.py -v
```

---

## Expected Output

```
==================================================
 RAG EVALUATION REPORT (RAGAS)
==================================================
  Cases Evaluated : 20
  LLM Judge       : gemini-2.0-flash

--- RAGAS Metrics (avg across all cases) ---
  faithfulness        : 0.91  ✅ (threshold: 0.80)
  answer_relevancy    : 0.87  ✅ (threshold: 0.75)
  context_precision   : 0.83  ✅ (threshold: 0.70)
  context_recall      : 0.78  ✅ (threshold: 0.70)

--- Per-Category Breakdown ---
  return_policy    : faithfulness=0.94  answer_relevancy=0.90
  support_contact  : faithfulness=0.88  answer_relevancy=0.85
  shipping_policy  : faithfulness=0.92  answer_relevancy=0.86
  refund_policy    : faithfulness=0.89  answer_relevancy=0.88
  order_management : faithfulness=0.90  answer_relevancy=0.84

  Result: ✅ EVAL PASSED (all thresholds met)

Full JSON report saved to: evaluation/reports/rag_report_20260227_181500.json
```

---

## Threshold Policy (CI Gate)

| Metric | Minimum Threshold |
|---|---|
| `faithfulness` | ≥ 0.80 |
| `answer_relevancy` | ≥ 0.75 |
| `context_precision` | ≥ 0.70 |
| `context_recall` | ≥ 0.70 |

If any metric drops below its threshold, the eval script exits with code `1`.

---

## When to Re-Run

| Trigger | Action |
|---|---|
| New document ingested into FAISS | Re-run full eval |
| Embedding model changed | Re-run full eval (mandatory) |
| `rag_generate.py` prompt changed | Re-run full eval |
| FAISS `k` value changed | Re-run and check `context_precision` |
| New policy added to `support.pdf` | Add new cases to golden dataset |
