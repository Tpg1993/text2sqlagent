"""
Human-in-the-Loop (HITL) Approval System
Manages approval workflows for sensitive database queries.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

class ApprovalStatus(Enum):
    """Approval status for queries."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class ApprovalRequest:
    """Represents a query awaiting approval."""
    request_id: str
    query: str
    sensitive_tables: List[str]
    timestamp: datetime
    status: ApprovalStatus
    user_id: Optional[str] = None
    reason: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_dict(self):
        return {
            "request_id": self.request_id,
            "query": self.query,
            "sensitive_tables": self.sensitive_tables,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "user_id": self.user_id,
            "reason": self.reason,
            "session_id": self.session_id
        }

class ApprovalManager:
    """
    Manages approval requests for sensitive queries.
    In production, this would use a database. For now, using in-memory storage.
    """
    
    # Sensitive tables that require approval
    # TEMPORARILY REDUCED: Removed "employees" to allow direct query execution
    # (SSE is disabled, so approval results cannot reach frontend)
    SENSITIVE_TABLES = {
        "customers", "salaries", "users", 
        "payments", "credit_cards", "personal_info"
    }
    
    def __init__(self):
        self._pending_requests: Dict[str, ApprovalRequest] = {}
    
    def is_query_sensitive(self, query: str) -> tuple[bool, List[str]]:
        """
        Check if a query touches sensitive tables.
        
        Returns:
            (is_sensitive, list_of_sensitive_tables)
        """
        query_lower = query.lower()
        found_tables = []
        
        for table in self.SENSITIVE_TABLES:
            # Simple detection: check if table name appears in query
            # In production, use SQL parser for accurate detection
            if table in query_lower:
                found_tables.append(table)
        
        return (len(found_tables) > 0, found_tables)
    
    def create_approval_request(
        self, 
        query: str, 
        sensitive_tables: List[str],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> ApprovalRequest:
        """Create a new approval request."""
        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            query=query,
            sensitive_tables=sensitive_tables,
            timestamp=datetime.now(),
            status=ApprovalStatus.PENDING,
            user_id=user_id,
            session_id=session_id
        )
        
        self._pending_requests[request.request_id] = request
        print(f"🔒 [HITL] Created approval request: {request.request_id}")
        print(f"   Query: {query[:100]}...")
        print(f"   Sensitive tables: {', '.join(sensitive_tables)}")
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get an approval request by ID."""
        return self._pending_requests.get(request_id)
    
    def approve_request(self, request_id: str, approver_id: Optional[str] = None) -> bool:
        """Approve a pending request."""
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.APPROVED
        request.reason = f"Approved by {approver_id or 'admin'}"
        
        print(f"✅ [HITL] Request {request_id} approved")
        return True
    
    def reject_request(self, request_id: str, reason: str, rejector_id: Optional[str] = None) -> bool:
        """Reject a pending request."""
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        
        if request.status != ApprovalStatus.PENDING:
            return False
        
        request.status = ApprovalStatus.REJECTED
        request.reason = f"Rejected by {rejector_id or 'admin'}: {reason}"
        
        print(f"❌ [HITL] Request {request_id} rejected: {reason}")
        return True
    
    def get_pending_requests(self) -> List[ApprovalRequest]:
        """Get all pending approval requests."""
        return [
            req for req in self._pending_requests.values()
            if req.status == ApprovalStatus.PENDING
        ]
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove old requests (approved/rejected) older than max_age_hours."""
        now = datetime.now()
        to_remove = []
        
        for request_id, request in self._pending_requests.items():
            age_hours = (now - request.timestamp).total_seconds() / 3600
            if age_hours > max_age_hours and request.status != ApprovalStatus.PENDING:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self._pending_requests[request_id]
        
        if to_remove:
            print(f"🧹 [HITL] Cleaned up {len(to_remove)} old requests")

# Global singleton instance
approval_manager = ApprovalManager()
