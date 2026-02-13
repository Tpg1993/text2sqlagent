from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm import invoke_chain_with_fallback
from app.utils.state import AgentState

ORCHESTRATOR_PROMPT = """You are a master routing agent.
Determine if the request requires:
1. 'sql' - Structured database query (sales, employees, departments, data analysis)
2. 'rag' - Document search (policies, returns, shipping, support)
3. 'general' - General chat or greetings

Query: {question}

Return ONLY one word: 'sql', 'rag', 'general'.
"""

def orchestrator_node(state: AgentState):
    """Determines intent."""
    print("--- ORCHESTRATOR ---")
    
    def chain_factory(llm):
        return ChatPromptTemplate.from_template(ORCHESTRATOR_PROMPT) | llm | StrOutputParser()
        
    intent = invoke_chain_with_fallback(
        chain_factory, 
        {"question": state['question']}, 
        name="Orchestrator Agent",
        tags=["orchestrator", "routing"]
    ).strip().lower()
    
    # Fallback / Cleaning
    if "sql" in intent: intent = "sql"
    elif "rag" in intent: intent = "rag"
    elif "general" in intent: intent = "general"
    else: intent = "general"
    
    return {"intent": intent}
