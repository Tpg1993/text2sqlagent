

from typing import List, Optional, Dict, Any, Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.utils.security import security_manager

# Tool Registration Hardening: Only allow registration if policy allows
def _is_tool_registration_allowed(tool_name: str) -> bool:
    # You can enhance this logic as needed (env var, config, etc.)
    # For demo, allow only if tool is in a hardcoded whitelist
    allowed_tools = {"generate_chart_spec"}
    return tool_name in allowed_tools

if not _is_tool_registration_allowed("generate_chart_spec"):
    raise RuntimeError("Tool registration not allowed for generate_chart_spec")

class ChartSpec(BaseModel):
    """
    Schema for generating a chart visualization configuration.
    This ensures the frontend receives a valid Recharts specification.
    """
    chart_type: Literal["bar", "line", "pie", "area", "scatter"] = Field(
        ..., 
        description="The type of chart to display."
    )
    title: str = Field(
        ..., 
        description="A descriptive title for the chart."
    )
    data: List[Dict[str, Any]] = Field(
        ..., 
        description="The data points to be plotted. Each dict represents a row."
    )
    x_key: str = Field(
        ..., 
        description="The key in the data objects to use for the X-axis (category)."
    )
    y_keys: List[str] = Field(
        ..., 
        description="The keys in the data objects to use for the Y-axis (values/series)."
    )
    colors: Optional[List[str]] = Field(
        default=None, 
        description="Optional list of hex color codes for the chart series."
    )

@tool(parse_docstring=True)
def generate_chart_spec(
    chart_type: Literal["bar", "line", "pie", "area", "scatter"],
    title: str,
    data: List[Dict[str, Any]],
    x_key: str,
    y_keys: List[str],
    colors: Optional[List[str]] = None,
    state: dict = None
) -> Dict[str, Any]:
    """
    Generates a structured chart specification for the frontend.

    Args:
        chart_type: The type of chart to display.
        title: A descriptive title for the chart.
        data: The data points to be plotted. Each dict represents a row.
        x_key: The key in the data objects to use for the X-axis (category).
        y_keys: The keys in the data objects to use for the Y-axis (values/series).
        colors: Optional list of hex color codes for the chart series.
    """
    # RBAC: Only chart agent
    allowed_agents = {"chart"}
    # Immutable security context: copy to prevent mutation
    import copy
    security_context = copy.deepcopy((state or {}).get("security_context", {}))
    agent = security_context.get("current_agent")
    if agent not in allowed_agents:
        # Fail-safe default: deny access and log
        import logging
        logging.warning(f"Access denied for agent: {agent}")
        return {"error": "Access denied for this agent."}
    return {
        "type": chart_type,
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKeys": y_keys,
        "colors": colors
    }
