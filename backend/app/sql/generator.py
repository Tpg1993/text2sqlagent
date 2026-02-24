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

GEN_SQL_PROMPT = """You are a PostgreSQL/SQLite expert.
Given the database schema:
{schema}

And the plan:
{plan}

Write a SQL query to answer the user's question: {question}

{error_context}

Return ONLY the SQL string. Do not use markdown backticks.
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
    return sql.replace("```sql", "").replace("```", "").strip().strip('"').strip("'")
