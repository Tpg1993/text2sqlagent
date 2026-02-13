import json
from langchain_openai import ChatOpenAI
from app.config import settings
from app.utils.state import AgentState

def chart_node(state: AgentState):
    """Suggests Chart."""
    print("--- CHART ---")
    if not state.get('sql_result') or not isinstance(state['sql_result'], list):
         return {"visualization_spec": None}
    
    # Simple Chart Logic inline or imported
    CHART_PROMPT = """Suggest a Recharts JSON config (type: bar|line|pie, data, xKey, yKey, title) for: {question} \n Data: {result}"""
    llm = ChatOpenAI(model=settings.LLM_MODEL, temperature=0, api_key=settings.OPENAI_API_KEY, model_kwargs={"response_format": {"type": "json_object"}})
    try:
        res = llm.invoke(
            CHART_PROMPT.format(question=state['question'], result=str(state['sql_result'])[:1000]),
            config={"run_name": "Chart Generator Agent", "tags": ["chart", "visualization"]}
        )
        spec = json.loads(res.content)
        return {"visualization_spec": spec}
    except:
        return {"visualization_spec": None}
