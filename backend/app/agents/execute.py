from sqlalchemy import text
from app.utils.state import AgentState
from app.db.session import data_engine


def execute_node(state: AgentState):
    """
    Executes approved SQL queries with ABAC enforcement.

    The ABAC check runs AFTER validation and HITL approval to provide a
    final defence-in-depth layer: even if a query passed validation,
    the ABAC PDP blocks execution if the user's role doesn't permit it.
    """
    print("--- EXECUTE ---")

    role = state.get('user_role', 'user')
    user_id = state.get('user_id', 'unknown')
    sql = state.get('sql_query', '')
    print(f"🔒 User: {user_id} | Role: {role}")

    # ── ABAC enforcement ─────────────────────────────────────────────────────────
    try:
        import sqlglot
        import sqlglot.expressions as exp
        from app.utils.abac import pdp

        parsed_statements = sqlglot.parse(sql)
        if parsed_statements:
            parsed = parsed_statements[0]
            if parsed:
                tables_in_query = [
                    tbl.name.lower()
                    for tbl in parsed.find_all(exp.Table)
                    if tbl.name
                ]
                subject = {"role": role, "user_id": user_id}
                context = {
                    "requires_approval": state.get("requires_approval", False),
                    "approval_status": state.get("approval_status", "none"),
                }
                for table_name in tables_in_query:
                    resource = {"table": table_name}
                    is_allowed, reason = pdp.evaluate(
                        subject=subject,
                        resource=resource,
                        action="EXECUTE_SQL",
                        context=context,
                    )
                    if not is_allowed:
                        error_msg = f"⛔ [ABAC] Access Denied: {reason}"
                        print(error_msg)
                        return {"sql_result": None, "error": error_msg}

    except ImportError:
        # sqlglot not available — skip ABAC table-level check (degraded)
        print("⚠️  [ABAC] sqlglot not found; skipping table-level ABAC check.")
    except Exception as abac_err:
        print(f"⚠️  [ABAC] Check error (failing open): {abac_err}")

    # ── Execute SQL ──────────────────────────────────────────────────────────────
    try:
        with data_engine.connect() as conn:
            clean_query = sql.replace('```sql', '').replace('```', '').strip().strip('"').strip("'")
            result = conn.execute(text(clean_query))
            rows = [dict(row._mapping) for row in result]
            print(f"✅ [Execute] Query returned {len(rows)} rows.")
            return {"sql_result": rows, "error": None}
    except Exception as e:
        return {"sql_result": None, "error": str(e)}
