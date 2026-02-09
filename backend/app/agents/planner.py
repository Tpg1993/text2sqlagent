from app.utils.state import AgentState
from app.sql.generator import generate_plan

def planner_node(state: AgentState):
    """Generates SQL plan."""
    print("--- PLANNER ---")
    plan = generate_plan(state['schema'], state['question'])
    return {"plan": plan}
