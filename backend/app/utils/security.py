from typing import List, Dict, Optional, Any, Callable
import functools
import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class Permission(Enum):
    """
    Granular permissions for agents.
    Based on Strata.io's Least Privilege model.
    """
    ROUTE_REQUEST = "route_request"
    PLAN_QUERY = "plan_query"
    GENERATE_SQL = "generate_sql"
    VALIDATE_SQL = "validate_sql"
    EXECUTE_SQL = "execute_sql"
    READ_VECTOR_DB = "read_vector_db"
    GENERATE_RAG_ANSWER = "generate_rag_answer"
    GENERATE_CHART = "generate_chart"
    FORMAT_RESPONSE = "format_response"
    
@dataclass
class AgentIdentity:
    """
    Represents the unique identity of an agent node in the graph.
    """
    name: str
    role: str
    permissions: List[Permission] = field(default_factory=list)
    
    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

class SecurityPolicy:
    """
    Defines the security policy (RBAC) for the entire agent system.
    """
    def __init__(self):
        self.identities: Dict[str, AgentIdentity] = {}
        self._load_policies()
        
    def _load_policies(self):
        """
        Define roles and permissions for each agent node.
        This enforces Least Privilege - agents only get what they need.
        """
        # Orchestrator: Can only route, cannot execute or read DB
        self.identities["orchestrator"] = AgentIdentity(
            name="orchestrator", 
            role="router",
            permissions=[Permission.ROUTE_REQUEST]
        )
        
        # Schema: Can read schema metadata (implicit in its function, but we can secure it if needed)
        # For now, we treat schema fetching as a low-risk read op, but let's give it a permission
        self.identities["schema"] = AgentIdentity(
            name="schema",
            role="metadata_reader",
            permissions=[] # Schema fetch is currently safe/read-only 
        )
        
        # Planner: Can plan
        self.identities["planner"] = AgentIdentity(
            name="planner",
            role="planner", 
            permissions=[Permission.PLAN_QUERY]
        )
        
        # Generator: Can WRITE SQL strings, but NOT execute
        self.identities["generate"] = AgentIdentity(
            name="generate",
            role="sql_writer",
            permissions=[Permission.GENERATE_SQL]
        )
        
        # Validator: Can validate strings
        self.identities["validate"] = AgentIdentity(
            name="validate",
            role="security_audit",
            permissions=[Permission.VALIDATE_SQL]
        )
        
        # Executor: THE ONLY ONE allowed to actually run SQL
        self.identities["execute"] = AgentIdentity(
            name="execute",
            role="db_admin",
            permissions=[Permission.EXECUTE_SQL]
        )
        
        # Evaluator: Can check results
        self.identities["evaluate"] = AgentIdentity(
            name="evaluate",
            role="auditor",
            permissions=[]
        )
        
        # RAG Retriever: Can access Vector DB
        self.identities["retrieve"] = AgentIdentity(
            name="retrieve",
            role="knowledge_seeker",
            permissions=[Permission.READ_VECTOR_DB]
        )
        
        # RAG Generator: Can write answers
        self.identities["rag_gen"] = AgentIdentity(
            name="rag_gen",
            role="writer",
            permissions=[Permission.GENERATE_RAG_ANSWER]
        )
        
        # Chart: Can visualize data
        self.identities["chart"] = AgentIdentity(
            name="chart", 
            role="analyst",
            permissions=[Permission.GENERATE_CHART]
        )
        
        # Format: Can format output
        self.identities["format"] = AgentIdentity(
            name="format",
            role="frontend_interface",
            permissions=[Permission.FORMAT_RESPONSE]
        )
        
        # Retry: Logic only
        self.identities["retry"] = AgentIdentity(
            name="retry",
            role="logic",
            permissions=[]
        )
        
        # Approval Pending (HITL): Routing only, no special permissions
        self.identities["approval_pending"] = AgentIdentity(
            name="approval_pending",
            role="approval_router",
            permissions=[]
        )


        
    def get_identity(self, node_name: str) -> Optional[AgentIdentity]:
        return self.identities.get(node_name)

class SecurityManager:
    """
    Manages authentication and authorization enforcement.
    Acts as the 'Security Gateway' for the agent loop.
    """
    def __init__(self):
        self.policy = SecurityPolicy()
        
    def enforce(self, node_name: str, required_permission: Optional[Permission] = None) -> Callable:
        """
        Decorator/Wrapper to enforce security context and permissions before node execution.
        Concepts:
        - Authentication: Verifies 'node_name' exists in policy.
        - Authorization: Verifies identity has 'required_permission'.
        - Audit: Logs the access.
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(state: Any):
                # 1. Identify
                identity = self.policy.get_identity(node_name)
                if not identity:
                    # In strict mode, we might raise error. For now, log warning.
                    logger.warning(f"🔒 [Security] Unknown agent node '{node_name}' attempted execution.")
                    # Fallback generic identity for unlisted nodes
                    identity = AgentIdentity(name="unknown", role="guest")
                
                # 2. Authorize
                if required_permission and not identity.has_permission(required_permission):
                    error_msg = f"⛔ [Security] Access Denied: Agent '{node_name}' does not have permission '{required_permission.value}'"
                    logger.error(error_msg)
                    return {
                        "error": error_msg,
                        "messages": [f"Security Error: {error_msg}"]
                    }
                
                # 3. Context Injection (Simulating Secure Session)
                # We inject the current agent's identity into the state for downstream awareness
                # This mimics passing a "Security Token" along the chain
                if isinstance(state, dict):
                    state["security_context"] = {
                        "current_agent": identity.name,
                        "role": identity.role,
                        "permissions": [p.value for p in identity.permissions]
                    }
                
                logger.info(f"✅ [Security] Allowed: {node_name} (Role: {identity.role})")
                
                # 4. Execute
                return func(state)
            return wrapper
        return decorator

# Global Instance
security_manager = SecurityManager()
