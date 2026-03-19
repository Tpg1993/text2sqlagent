from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage
from app.utils.state import AgentState
from app.utils.llm import invoke_chain_with_fallback

RAG_PROMPT = """You are a helpful company support assistant. Answer the user's question STRICTLY and ONLY based on the provided document context below.

RULES:
- ONLY use information from the context. Do NOT use your general training knowledge.
- If the context does not contain the answer, say exactly: "I don't have information about that in the company documents. Please contact support for assistance."
- Be concise. Do NOT cite sources in your answer text, they are displayed elsewhere.
- Do NOT make up information or policies not found in the context.
- IMPORTANT: If you need to reason or think before answering, you MUST wrap your reasoning entirely within <think> and </think> xml tags. Do not put reasoning outside those tags! After closing the tags, provide your concise answer.

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
        return {"messages": [no_docs_msg], "rag_answer": no_docs_msg.content, "reasoning": None}

    docs_content = "\n\n".join([
        f"[Source: {d.metadata.get('source', 'company doc')}, page {d.metadata.get('page', d.metadata.get('page_number', '?'))}]\n{d.page_content}"
        for d in docs
    ])
    
    print(f"📄 RAG: Retrieved {len(docs)} chunks, total {len(docs_content)} chars")
    
    def create_chain(llm):
        return ChatPromptTemplate.from_template(RAG_PROMPT) | llm | StrOutputParser()

    ans, pid = invoke_chain_with_fallback(
        create_chain, 
        {"context": docs_content, "question": state['question']},
        name="RAG Answer Generator",
        tags=["rag", "generation"],
        metadata={"session_id": state.get("session_id")},
        return_provider=True
    )
    
    import re
    reasoning = None
    think_match = re.search(r'<think>(.*?)</think>', ans, flags=re.IGNORECASE | re.DOTALL)
    if think_match:
        reasoning = think_match.group(1).strip()
        ans = re.sub(r'<think>.*?</think>', '', ans, flags=re.IGNORECASE | re.DOTALL).strip()
    elif '<think>' in ans:
        after_think = ans.split('<think>', 1)[-1]
        after_think = re.sub(r'</think>', '', after_think).strip()
        ans = '' # if model never closed the think block, consider the entire output reasoning? Actually let's assume if tag opened, everything is reasoning.
        reasoning = after_think.strip()
    
    return {"rag_answer": ans, "llm_used": pid, "reasoning": reasoning}
