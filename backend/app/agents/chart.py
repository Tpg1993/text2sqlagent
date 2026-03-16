import json
from app.config import settings
from app.utils.state import AgentState

def _infer_chart_spec(question: str, rows: list) -> dict | None:
    """Deterministically infer a chart spec from result rows without LLM tool calls."""
    if not rows:
        return None
    cols = list(rows[0].keys())
    # Pick first string column as X, first numeric column as Y
    x_key = next((c for c in cols if isinstance(rows[0][c], str)), cols[0])
    y_keys = [c for c in cols if c != x_key and isinstance(rows[0].get(c), (int, float))]
    if not y_keys:
        return None
    q = question.lower()
    chart_type = "pie" if "pie" in q else "line" if ("trend" in q or "over time" in q) else "bar"
    return {
        "type": chart_type,
        "title": question[:60],
        "data": rows,
        "xKey": x_key,
        "yKey": y_keys[0],
    }

def chart_node(state: AgentState):
    """Suggests Chart."""
    print("--- CHART ---")
    if not state.get('sql_result') or not isinstance(state['sql_result'], list):
         return {"visualization_spec": None}
    
    # Tool-based Chart Logic
    from app.tools.chart_tools import generate_chart_spec, ChartSpec
    # Tool-based Chart Logic
    from app.tools.chart_tools import generate_chart_spec
    from app.utils.llm import invoke_chain_with_fallback
    
    # Tool Registration Hardening: Only bind allowed tools for this agent
    allowed_tools = [generate_chart_spec]
    
    def chain_factory(llm):
        """Bind tools if the LLM natively supports it."""
        is_unsupported_sarvam = False
        if hasattr(llm, 'model_name') and llm.model_name == 'sarvam-m':
            is_unsupported_sarvam = True

        if hasattr(llm, "bind_tools") and not is_unsupported_sarvam:
            return llm.bind_tools(allowed_tools, tool_choice="any")
        return llm
    
    CHART_TOOL_PROMPT = """
    You are a data visualization expert.
    Given the following data, generate a valid chart specification using the `generate_chart_spec` tool.
    
    User Query: {question}
    Data: {result}
    """
    
    try:
        # Invoke LLM with tools
        msg = invoke_chain_with_fallback(
            chain_factory,
            input_data=CHART_TOOL_PROMPT.format(question=state['question'], result=str(state['sql_result'])[:2000]),
            name="Chart Generator Agent",
            tags=["chart", "visualization", "tool_use"],
            metadata={"session_id": state.get("session_id")}
        )
        
        # Extract tool call arguments
        if msg.tool_calls:
            spec = msg.tool_calls[0]['args']
            final_spec = generate_chart_spec(**spec)
            return {"visualization_spec": final_spec}
        else:
            print("Warning: LLM did not call the chart tool — using deterministic fallback.")
            fallback = _infer_chart_spec(state.get('question', ''), state['sql_result'])
            return {"visualization_spec": fallback}
            
    except Exception as e:
        print(f"Error generating chart: {e} — using deterministic fallback.")
        fallback = _infer_chart_spec(state.get('question', ''), state['sql_result'])
        return {"visualization_spec": fallback}
