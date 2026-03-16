from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.llm import invoke_chain_with_fallback
from typing import Optional

# Prompts
PLANNER_PROMPT = """You are a senior data architect.
Given the following database schema:
{schema}

And the user request:
{question}

Create a step-by-step plan to retrieve the requested data.
Focus on which tables to join and what filters to apply.
Keep it concise.
"""

GEN_SQL_PROMPT = """You are a SQLite expert. You MUST follow strict SQLite syntax rules.
Given the database schema:
{schema}

And the plan:
{plan}

Write a SQL query to answer the user's question: {question}

{error_context}

CRITICAL INSTRUCTIONS:
1. ONLY use column names and table names explicitly defined in the provided schema.
2. DO NOT use table aliases (e.g., NEVER write `FROM employees e` or `JOIN sales s`). Always use the FULL table name.
   - BAD:  SELECT e.name FROM employees e JOIN sales s ON e.id = s.employee_id
   - GOOD: SELECT employees.name FROM employees JOIN sales ON employees.id = sales.employee_id
3. DO NOT use backticks. Use double-quotes for identifiers if needed, or no quotes at all.
4. DO NOT hallucinate columns — only use what is in the schema.
5. Format output strictly as:
-- REASONING: <brief 1-line explanation>
<The actual SQL string>

Return ONLY the commented reasoning followed by the SQL. No markdown code fences.
"""

def generate_plan(schema: str, question: str, tags: Optional[list] = None, metadata: Optional[dict] = None) -> str:
    def create_chain(llm):
        return ChatPromptTemplate.from_template(PLANNER_PROMPT) | llm | StrOutputParser()
        
    return invoke_chain_with_fallback(
        create_chain, 
        {"schema": schema, "question": question},
        name="SQL Planner Agent",
        tags=tags or ["sql", "planning"],
        metadata=metadata
    )

def generate_sql_query(schema: str, plan: str, question: str, previous_error: Optional[str] = None, previous_query: Optional[str] = None, tags: Optional[list] = None, metadata: Optional[dict] = None) -> str:
    error_context = ""
    if previous_error and previous_query:
        error_context = f"IMPORTANT: The previous query `{previous_query}` failed with error: {previous_error}. Fix the query."
    
    def create_chain(llm):
        return ChatPromptTemplate.from_template(GEN_SQL_PROMPT) | llm | StrOutputParser()
        
    sql = invoke_chain_with_fallback(
        create_chain, 
        {
            "schema": schema, 
            "plan": plan, 
            "question": question,
            "error_context": error_context
        },
        name="SQL Generator Agent",
        tags=tags or ["sql", "generation"],
        metadata=metadata
    )
    
    # Strip markdown and reasoning
    raw_response = sql.replace("```sql", "").replace("```", "").strip().strip('"').strip("'")
    
    # Strip <think>...</think> blocks (Sarvam and other reasoning models output these)
    # Also handles unclosed <think> tags (no </think>)
    import re
    # First try to remove a fully-closed think block
    raw_response = re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()
    # If an unclosed <think> tag remains, take only the text AFTER </think> or after <think>
    # i.e., if <think> is still present, grab everything from the last > onwards as SQL
    if '<think>' in raw_response:
        # Split on <think>, take the part after it, then strip any remaining closing tag
        after_think = raw_response.split('<think>', 1)[-1]
        after_think = re.sub(r'</think>', '', after_think).strip()
        raw_response = after_think
    
    # Extract only the SQL if reasoning is present
    lines = raw_response.split('\n')
    filtered_lines = []
    for line in lines:
        if line.strip().startswith("-- REASONING:"):
            continue # Skip reasoning
        filtered_lines.append(line)
        
    final_sql = "\n".join(filtered_lines).strip()
    return final_sql
