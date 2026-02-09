from langgraph.graph import StateGraph, END
from app.utils.state import AgentState
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# Agent step display names for SSE
AGENT_DISPLAY_NAMES = {
    "orchestrator": "🤖 Analyzing query...",
    "schema": "📋 Fetching database schema...",
    "generate": "✍️ Generating SQL...",
    "validate": "✅ Validating SQL...",
    "execute": "⚡ Running query...",
    "evaluate": "📊 Evaluating results...",
    "chart": "📈 Creating visualization...",
    "format": "✨ Formatting response...",
    "retrieve": "🔍 Searching documents...",
    "rag_gen": "💬 Generating answer...",
    "retry": "🔄 Retrying...",
}

# Helper to trace nodes and emit SSE events
def trace_node(node_name, node_func):
    def wrapped(state):
        # Emit SSE event for progress
        session_id = state.get("session_id")
        if session_id:
            import asyncio
            from app.utils.sse_manager import sse_manager
            try:
                asyncio.create_task(sse_manager.send_event(
                    session_id,
                    "progress",
                    {"step": node_name, "message": AGENT_DISPLAY_NAMES.get(node_name, f"Processing {node_name}...")}
                ))
            except:
                pass  # Ignore SSE errors
        
        with tracer.start_as_current_span(f"agent_node_{node_name}"):
            return node_func(state)
    return wrapped

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
workflow.add_node("orchestrator", trace_node("orchestrator", orchestrator_node))
workflow.add_node("schema", trace_node("schema", fetch_schema_node))
workflow.add_node("planner", trace_node("planner", planner_node))
workflow.add_node("generate", trace_node("generate", generate_node))
workflow.add_node("validate", trace_node("validate", validate_node))
workflow.add_node("execute", trace_node("execute", execute_node))
workflow.add_node("evaluate", trace_node("evaluate", evaluate_node))
workflow.add_node("retry", trace_node("retry", retry_node))
workflow.add_node("chart", trace_node("chart", chart_node))
workflow.add_node("format", trace_node("format", format_node))

workflow.add_node("retrieve", trace_node("retrieve", retrieve_node))
workflow.add_node("rag_gen", trace_node("rag_gen", rag_gen_node))

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
