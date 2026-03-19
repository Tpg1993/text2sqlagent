from app.utils.state import AgentState
from app.utils.hitl import approval_manager

def validate_node(state: AgentState):
    """
    Validates SQL using AST parsing (sqlglot) and checks for sensitive table access.

    Security improvements over regex approach:
    - Detects non-SELECT roots (DROP, UPDATE, INSERT, DELETE, multi-statement)
    - Extracts ALL table references from the full AST (subqueries, CTEs, aliases)
    - Cannot be bypassed by SQL comments or obfuscated keywords
    """
    print("--- VALIDATE ---")
    sql = state['sql_query']

    # ── 1. AST-based structural validation ──────────────────────────────────────
    try:
        import sqlglot
        import sqlglot.expressions as exp

        # Parse into AST. dialect=None auto-detects (SQLite compatible).
        parsed_statements = sqlglot.parse(sql)

        # Reject multi-statement injections (e.g. SELECT 1; DROP TABLE users)
        if len(parsed_statements) > 1:
            error_msg = "Security: Multi-statement SQL rejected. Only single SELECT statements are allowed."
            print(f"❌ [AST] {error_msg}")
            return {"sql_valid": False, "error": error_msg}

        parsed = parsed_statements[0]

        # Enforce root must be a SELECT statement
        if parsed is None or not isinstance(parsed, exp.Select):
            error_msg = f"Security: Only SELECT statements are permitted. Detected root type: {type(parsed).__name__}."
            print(f"❌ [AST] {error_msg}")
            return {"sql_valid": False, "error": error_msg}

        # Extract ALL table names from AST — traverses subqueries, CTEs, JOINs
        from app.sql.schema import get_valid_tables_and_columns
        valid_schema = get_valid_tables_and_columns()
        valid_tables = set(valid_schema.keys())

        all_referenced_tables = [
            tbl.name.lower()
            for tbl in parsed.find_all(exp.Table)
            if tbl.name  # skip anonymous subquery aliases
        ]

        print(f"🔍 [AST] Tables referenced in query: {all_referenced_tables}")

        for table_name in all_referenced_tables:
            if table_name not in valid_tables:
                error_msg = f"Hallucination Detected: Table '{table_name}' does not exist in the database schema."
                print(f"❌ [AST] {error_msg}")
                return {"sql_valid": False, "error": error_msg}

    except ImportError:
        # Fallback: sqlglot not installed — use legacy regex (degraded security)
        import re
        print("⚠️  [Validate] sqlglot not found, falling back to regex validation (reduced security)")
        sql_upper = sql.upper()
        if any(kw in sql_upper for kw in ("DROP", "DELETE", "UPDATE", "ALTER", "INSERT")):
            return {"sql_valid": False, "error": "Unsafe SQL keyword detected."}
        from app.sql.schema import get_valid_tables_and_columns
        valid_schema = get_valid_tables_and_columns()
        valid_tables = set(valid_schema.keys())
        matches = re.findall(r'(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)', sql_upper)
        all_referenced_tables = [m.lower() for m in matches]
        for table_name in all_referenced_tables:
            if table_name not in valid_tables:
                return {"sql_valid": False, "error": f"Hallucination Detected: Table '{table_name}' not in schema."}

    except Exception as parse_err:
        error_msg = f"SQL parsing failed: {parse_err}"
        print(f"❌ [AST] {error_msg}")
        return {"sql_valid": False, "error": error_msg}

    # ── 2. HITL: Check if query touches sensitive tables ─────────────────────────
    is_sensitive, sensitive_tables = approval_manager.is_query_sensitive(sql)

    if is_sensitive:
        print(f"⚠️  [HITL] Sensitive query detected: {', '.join(sensitive_tables)}")
        approval_request = approval_manager.create_approval_request(
            query=sql,
            sensitive_tables=sensitive_tables,
            user_id=state.get('user_id'),
            session_id=state.get('session_id')
        )
        return {
            "sql_valid": True,
            "requires_approval": True,
            "approval_status": "pending",
            "approval_request_id": approval_request.request_id,
            "sensitive_tables": sensitive_tables
        }

    # ── 3. All checks passed ─────────────────────────────────────────────────────
    print("✅ [Validate] SQL validated via AST — structure and schema checks passed.")
    return {
        "sql_valid": True,
        "requires_approval": False
    }
