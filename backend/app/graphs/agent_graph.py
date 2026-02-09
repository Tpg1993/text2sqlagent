from langgraph.graph import StateGraph, END
from app.utils.state import AgentState

# Modular Imports
from app.agents.orchestrator import orchestrator_node
from app.agents.schema import fetch_schema_node
from app.agents.planner import planner_node
from app.agents.generate import generate_node
from app.agents.validate import validate_node
from app.agents.execute import execute_node
from app.agents.evaluate import evaluate_node
from app.agents.retry import retry_node
from app.agents.chart import chart_node
from app.agents.format import format_node
from app.agents.rag_retrieve import retrieve_node
from app.agents.rag_generate import rag_gen_node

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("schema", fetch_schema_node)
workflow.add_node("planner", planner_node)
workflow.add_node("generate", generate_node)
workflow.add_node("validate", validate_node)
workflow.add_node("execute", execute_node)
workflow.add_node("evaluate", evaluate_node)
workflow.add_node("retry", retry_node)
workflow.add_node("chart", chart_node)
workflow.add_node("format", format_node)

workflow.add_node("retrieve", retrieve_node)
workflow.add_node("rag_gen", rag_gen_node)

# Entry
workflow.set_entry_point("orchestrator")

# Edges
def route_orchestrator(state):
    return state.get('intent', 'general')

workflow.add_conditional_edges(
    "orchestrator",
    route_orchestrator,
    {
        "sql": "schema",
        "rag": "retrieve",
        "general": "format"
    }
)

# RAG Flow
workflow.add_edge("retrieve", "rag_gen")
workflow.add_edge("rag_gen", "format")

# SQL Flow
workflow.add_edge("schema", "generate")
# workflow.add_edge("planner", "generate")
workflow.add_edge("generate", "validate")

def route_validate(state):
    if state.get("sql_valid"): return "execute"
    return "retry"

workflow.add_conditional_edges("validate", route_validate, {"execute": "execute", "retry": "retry"})

workflow.add_edge("execute", "evaluate")

def route_evaluate(state):
    if state.get("error"): return "retry"
    return "chart"

workflow.add_conditional_edges("evaluate", route_evaluate, {"retry": "retry", "chart": "chart"})

workflow.add_edge("chart", "format")

# Retry Logic
def route_retry(state):
    if state.get("retry_count", 0) > 3: return "format"
    return "generate"

workflow.add_conditional_edges("retry", route_retry, {"generate": "generate", "format": "format"})
workflow.add_edge("format", END)

graph = workflow.compile()
