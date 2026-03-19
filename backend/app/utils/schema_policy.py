"""
Semantic RBAC: Dynamic Schema Injection based on User Role.

Instead of exposing the full database schema to the LLM for every user,
this module filters the schema so the LLM only knows about tables the
current user is allowed to query. This prevents the LLM from generating
SQL for tables that should be invisible to that role.
"""

from typing import Dict, List
from app.sql.schema import get_schema_text, get_valid_tables_and_columns


# ── Table allowlists per role ───────────────────────────────────────────────
# "*" means all tables are allowed (used for admin).
# Only listed tables will be included in the schema injected into the LLM prompt.
ROLE_TABLE_ALLOWLIST: Dict[str, List[str] | str] = {
    "admin": "*",              # admin sees everything
    "user": [                  # regular users only see safe, public tables
        "sales",
        "employees",
        "departments",
    ],
}

# Tables that should never appear in the schema for any role
# (e.g., internal system tables)
ALWAYS_HIDDEN_TABLES = {
    "pii_vault",
    "audit_logs",   # hidden from non-admins separately via allowlist, but always hidden from LLM schema
    "saved_charts",
    "chat_messages",
    "chat_sessions",
}


def get_schema_for_role(role: str) -> str:
    """
    Returns a filtered schema string tailored to the specified user role.
    Tables not in the allowlist for the role are completely hidden from the LLM.

    Args:
        role: The JWT role of the current user (e.g., "admin", "user")

    Returns:
        Schema text string listing only permitted tables and their columns.
    """
    allowlist = ROLE_TABLE_ALLOWLIST.get(role, ROLE_TABLE_ALLOWLIST["user"])  # default to user
    valid_schema = get_valid_tables_and_columns()

    lines = []
    for table_name, columns in valid_schema.items():
        # Always skip internal system tables
        if table_name in ALWAYS_HIDDEN_TABLES:
            continue

        # Check role allowlist
        if allowlist != "*" and table_name not in allowlist:
            continue

        lines.append(f"Table: {table_name}")
        for col in columns:
            lines.append(f"  - {col}")

    if not lines:
        return "(No tables available for this role)"

    return "\n".join(lines)
