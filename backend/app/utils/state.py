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
    step_count: int = 0
    visualization_spec: Optional[Dict[str, Any]]
    schema_context: Optional[str]
    failed_sql: Optional[str]
    
    # RAG Flow
    documents: Optional[List[Any]]
    rag_answer: Optional[str]
    
    # Meta
    retry_count: int
    session_id: Optional[str]  # For SSE progress streaming
    llm_used: Optional[str]
    
    # Security Context (Identity & Audit)
    agent_identity: dict
    security_context: dict
    
    # HITL Approval Workflow
    requires_approval: bool
    approval_status: Optional[str]  # 'pending', 'approved', 'rejected'
    approval_request_id: Optional[str]
    sensitive_tables: Optional[List[str]]

