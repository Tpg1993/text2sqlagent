import json
from langchain_openai import ChatOpenAI
from app.config import settings
from app.utils.state import AgentState

def chart_node(state: AgentState):
    """Suggests Chart."""
    print("--- CHART ---")
    if not state.get('sql_result') or not isinstance(state['sql_result'], list):
         return {"visualization_spec": None}
    
    # Tool-based Chart Logic
    from app.tools.chart_tools import generate_chart_spec, ChartSpec
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Bind tool to LLM (Using Gemini)
    llm = ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL, 
        temperature=0, 
        google_api_key=settings.GOOGLE_API_KEY,
        convert_system_message_to_human=True # Sometimes needed for Gemini
    )
    llm_with_tools = llm.bind_tools([generate_chart_spec], tool_choice="generate_chart_spec")
    
    CHART_TOOL_PROMPT = """
    You are a data visualization expert.
    Given the following data, generate a valid chart specification using the `generate_chart_spec` tool.
    
    User Query: {question}
    Data: {result}
    """
    
    try:
        # Invoke LLM with tools
        msg = llm_with_tools.invoke(
            CHART_TOOL_PROMPT.format(question=state['question'], result=str(state['sql_result'])[:2000]),
            config={"run_name": "Chart Generator Agent", "tags": ["chart", "visualization"]}
        )
        
        # Extract tool call arguments
        if msg.tool_calls:
            # The tool call arguments are already a dict matching our spec
            spec = msg.tool_calls[0]['args']
            # Map Python snake_case to frontend camelCase if needed, but our tool logic already does that?
            # Actually, the tool_calls['args'] will be the arguments to the function (snake_case).
            # We need to ensure the output matches what the frontend expects.
            # The 'generate_chart_spec' function helps, but bind_tools doesn't run the function automatically.
            # We can just use the args directly and transform them, OR run the function.
            
            # Let's run the function to get the clean dict
            final_spec = generate_chart_spec(**spec)
            return {"visualization_spec": final_spec}
        else:
            print("Warning: LLM did not call the chart tool.")
            return {"visualization_spec": None}
            
    except Exception as e:
        print(f"Error generating chart: {e}")
        return {"visualization_spec": None}
