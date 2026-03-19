"""
Attribute-Based Access Control (ABAC) for the Text2SQL agent.

Unlike RBAC (Role-Based) which grants fixed permissions per role, ABAC evaluates
a set of contextual *attributes* to make fine-grained access decisions:
  - Subject Attributes:  Who is asking? (role, user_id, department)
  - Resource Attributes: What is accessed? (table_name, sensitivity)
  - Action Attributes:   What are they doing? (EXECUTE_SQL, AGGREGATE_ONLY)
  - Context Attributes:  Under what conditions? (approval_status)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ABACPolicy:
    """
    A single policy rule. Access is ALLOWED only if all specified
    subject/resource/action constraints match AND the effect is 'allow'.
    Deny policies take precedence over allow policies.
    """
    name: str
    effect: str  # 'allow' or 'deny'
    subject_attrs: Dict[str, Any] = field(default_factory=dict)   # e.g. {"role": "admin"}
    resource_attrs: Dict[str, Any] = field(default_factory=dict)   # e.g. {"table": "audit_logs"}
    action: Optional[str] = None                                    # e.g. "EXECUTE_SQL"
    context_attrs: Dict[str, Any] = field(default_factory=dict)    # e.g. {"approval_status": "approved"}


# ─────────────────────────────────────────────
# Global Policy Set
# ─────────────────────────────────────────────
# Evaluation order: DENY beats ALLOW. More specific rules should be listed first.
# Wildcard "*" in resource_attrs["table"] matches any table.

POLICIES: List[ABACPolicy] = [
    # ── Admin gets full access ──────────────────────────────────────────────────
    ABACPolicy(
        name="admin_full_access",
        effect="allow",
        subject_attrs={"role": "admin"},
        resource_attrs={"table": "*"},
        action="EXECUTE_SQL",
    ),

    # ── Regular users can query safe tables ─────────────────────────────────────
    ABACPolicy(
        name="user_can_query_sales",
        effect="allow",
        subject_attrs={"role": "user"},
        resource_attrs={"table": "sales"},
        action="EXECUTE_SQL",
    ),
    ABACPolicy(
        name="user_can_query_employees",
        effect="allow",
        subject_attrs={"role": "user"},
        resource_attrs={"table": "employees"},
        action="EXECUTE_SQL",
    ),
    ABACPolicy(
        name="user_can_query_departments",
        effect="allow",
        subject_attrs={"role": "user"},
        resource_attrs={"table": "departments"},
        action="EXECUTE_SQL",
    ),

    # ── Deny users from sensitive tables ────────────────────────────────────────
    ABACPolicy(
        name="deny_user_users_table",
        effect="deny",
        subject_attrs={"role": "user"},
        resource_attrs={"table": "users"},
        action="EXECUTE_SQL",
    ),
    ABACPolicy(
        name="deny_user_audit_logs",
        effect="deny",
        subject_attrs={"role": "user"},
        resource_attrs={"table": "audit_logs"},
        action="EXECUTE_SQL",
    ),

    # ── Deny queries that require approval but haven't been approved yet ─────────
    ABACPolicy(
        name="deny_unapproved_sensitive_query",
        effect="deny",
        subject_attrs={"role": "*"},  # applies to all roles
        resource_attrs={"table": "*"},
        action="EXECUTE_SQL",
        context_attrs={"requires_approval": True, "approval_status": "pending"},
    ),
]


class PolicyDecisionPoint:
    """
    Evaluates access requests against the global POLICIES list.

    Usage:
        pdp = PolicyDecisionPoint()
        allowed, reason = pdp.evaluate(
            subject={"role": "user"},
            resource={"table": "audit_logs"},
            action="EXECUTE_SQL",
            context={}
        )
    """

    def _matches(self, policy_attrs: Dict[str, Any], actual_attrs: Dict[str, Any]) -> bool:
        """
        Returns True if all attributes in policy_attrs match actual_attrs.
        Wildcard "*" in policy matches any value.
        """
        for key, expected_val in policy_attrs.items():
            actual_val = actual_attrs.get(key)
            if expected_val == "*":
                continue  # wildcard — always matches
            if actual_val != expected_val:
                return False
        return True

    def _matches_context(self, policy: ABACPolicy, context: Dict[str, Any]) -> bool:
        """
        Matches context attributes using AND logic.
        A policy with no context_attrs matches any context (unconditionally).
        """
        if not policy.context_attrs:
            return True
        return self._matches(policy.context_attrs, context)

    def evaluate(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Evaluate whether the subject can perform `action` on `resource`.

        Returns:
            (is_allowed: bool, reason: str)
        """
        context = context or {}
        applicable = []

        for policy in POLICIES:
            # Check action match
            if policy.action and policy.action != action:
                continue
            # Check subject, resource, and context
            if (
                self._matches(policy.subject_attrs, subject)
                and self._matches(policy.resource_attrs, resource)
                and self._matches_context(policy, context)
            ):
                applicable.append(policy)

        # Deny-first evaluation
        for policy in applicable:
            if policy.effect == "deny":
                reason = f"ABAC DENY by policy '{policy.name}': {subject} → {action} on {resource}"
                logger.warning(f"🔒 [ABAC] {reason}")
                return False, reason

        # Check if at least one allow applies
        for policy in applicable:
            if policy.effect == "allow":
                reason = f"ABAC ALLOW by policy '{policy.name}'"
                logger.info(f"✅ [ABAC] {reason}")
                return True, reason

        # Default deny — no matching allow policy found
        reason = f"ABAC DEFAULT DENY: no allow policy for {subject} → {action} on {resource}"
        logger.warning(f"🔒 [ABAC] {reason}")
        return False, reason


# Global singleton
pdp = PolicyDecisionPoint()
