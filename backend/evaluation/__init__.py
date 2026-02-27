"""
Evaluation package for the text2sql RAG agent.

Contains evaluation scripts for:
    - eval_orchestrator.py  : Routing accuracy (custom golden dataset)
    - eval_rag.py           : RAG faithfulness & relevancy (RAGAS)
    - eval_text2sql.py      : SQL execution & hallucination rate (DeepEval)
    - eval_general.py       : Safety & helpfulness (LLM-as-a-judge)
"""
