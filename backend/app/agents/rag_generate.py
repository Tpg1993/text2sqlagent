from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.state import AgentState
from app.utils.llm import invoke_chain_with_fallback

def rag_gen_node(state: AgentState):
    print("--- RAG GENERATE ---")
    docs_content = "\n\n".join([d.page_content for d in state['documents']])
    RAG_PROMPT = "Answer based on context:\n{context}\n\nQuestion: {question}"
    
    def create_chain(llm):
        return ChatPromptTemplate.from_template(RAG_PROMPT) | llm | StrOutputParser()

    ans = invoke_chain_with_fallback(create_chain, {"context": docs_content, "question": state['question']})
    return {"rag_answer": ans}
