from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm import invoke_chain_with_fallback
from app.utils.state import AgentState

ORCHESTRATOR_PROMPT = """You are a master routing agent.
Determine if the request requires:
1. 'sql' - Structured database query (sales, employees, departments, data analysis, company data)
2. 'rag' - Document search (policies, returns, shipping, support, contacting support, how to contact support)
3. 'general' - General chat, simple greetings, or asking about external world news that are not about the company's own support.

If the user asks ANYTHING about support, including how to contact support, returning items, or shipping, map it to 'rag'.
If the user asks for SQL queries, sales info, database records, map to 'sql'.
Only if it's completely unrelated (e.g. hello, how are you, stock prices), map to 'general'.

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
        tags=["orchestrator", "routing"],
        metadata={"session_id": state.get("session_id")}
    ).strip().lower()
    
    # Robust intent extraction: search for the last valid keyword
    import re
    words = re.findall(r'[a-zA-Z]+', intent)
    
    final_intent = "general"
    for word in reversed(words):
        if word in ["sql", "rag", "general"]:
            final_intent = word
            break
            
    return {"intent": final_intent}
