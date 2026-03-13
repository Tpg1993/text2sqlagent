from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage
from app.utils.state import AgentState
from app.utils.llm import invoke_chain_with_fallback

RAG_PROMPT = """You are a helpful company support assistant. Answer the user's question STRICTLY and ONLY based on the provided document context below.

RULES:
- ONLY use information from the context. Do NOT use your general training knowledge.
- If the context does not contain the answer, say exactly: "I don't have information about that in the company documents. Please contact support for assistance."
- Be concise and cite which section of the document your answer comes from.
- Do NOT make up information or policies not found in the context.

--- COMPANY DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Answer (based ONLY on context above):"""

def rag_gen_node(state: AgentState):
    print("--- RAG GENERATE ---")
    docs = state.get('documents', [])
    
    # Guard: no documents retrieved
    if not docs:
        no_docs_msg = AIMessage(content=(
            "I couldn't find relevant information in the company documents to answer your question. "
            "This could be because the document index is unavailable. "
            "Please try rephrasing your question or contact support directly."
        ))
        return {"messages": [no_docs_msg], "rag_answer": no_docs_msg.content}

    docs_content = "\n\n".join([
        f"[Source: {d.metadata.get('source', 'company doc')}, page {d.metadata.get('page', '?')}]\n{d.page_content}"
        for d in docs
    ])
    
    print(f"📄 RAG: Retrieved {len(docs)} chunks, total {len(docs_content)} chars")
    
    def create_chain(llm):
        return ChatPromptTemplate.from_template(RAG_PROMPT) | llm | StrOutputParser()

    ans = invoke_chain_with_fallback(
        create_chain, 
        {"context": docs_content, "question": state['question']},
        name="RAG Answer Generator",
        tags=["rag", "generation"],
        metadata={"session_id": state.get("session_id")}
    )
    return {"rag_answer": ans}
