import operator
from typing import Annotated, List, Union, Dict, Any, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    State for the Text2SQL and RAG graph.
    """
    messages: Annotated[List[BaseMessage], operator.add]
    question: str
    
    # Orchestration
    intent: Optional[str] # 'sql', 'rag', 'general'
    
    # Text2SQL Flow
    schema: Optional[str]
    plan: Optional[str]
    sql_query: Optional[str]
    sql_result: Optional[Union[List[Dict[str, Any]], str]]
    sql_valid: bool
    error: Optional[str]
    visualization_spec: Optional[Dict[str, Any]]
    
    # RAG Flow
    documents: Optional[List[Any]]
    rag_answer: Optional[str]
    
    # Meta
    retry_count: int
    session_id: Optional[str]  # For SSE progress streaming
