"""
DLP (Data Loss Prevention) Masking Node.

This node sits between execute_node and evaluate_node in the agent graph.
It scrubs PII from the raw SQL result rows before the LLM ever sees them,
using the existing Presidio-based PIIScrubber and the PII vault for token storage.

The vault stores the mapping:  [PII_EMAIL_ADDRESS_abc12345] → john@example.com
After the LLM formats the response, main.py calls deanonymize_text() to restore
real values for the frontend display.
"""

from app.utils.state import AgentState
from app.utils.pii import get_pii_scrubber


def masking_node(state: AgentState) -> dict:
    """
    Scrubs PII from sql_result rows before downstream LLM processing.

    - Iterates over each row in sql_result
    - Converts string column values containing PII into vault tokens like [PII_EMAIL_ADDRESS_xxxxxxxx]
    - Returns cleaned rows back into state
    - If scrubbing fails on any value, it fails open (returns original value) to ensure availability
    """
    print("--- MASKING ---")

    sql_result = state.get("sql_result")
    if not sql_result or not isinstance(sql_result, list):
        print("⏭️  [DLP] No SQL results to mask.")
        return {}

    scrubber = get_pii_scrubber()
    pii_found = False
    masked_rows = []

    for row in sql_result:
        masked_row = {}
        for col, value in row.items():
            if isinstance(value, str) and value.strip():
                scrubbed = scrubber.scrub_text(value)
                if scrubbed != value:
                    pii_found = True
                    print(f"🔒 [DLP] PII detected and masked in column '{col}'")
                masked_row[col] = scrubbed
            else:
                masked_row[col] = value
        masked_rows.append(masked_row)

    if pii_found:
        print(f"✅ [DLP] Masked PII across {len(masked_rows)} rows. Vault tokens created.")
    else:
        print(f"✅ [DLP] No PII detected in {len(masked_rows)} rows.")

    return {"sql_result": masked_rows}
