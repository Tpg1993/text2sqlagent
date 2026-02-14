
from typing import List, Optional, Dict, Any, Literal
from langchain_core.tools import tool
from pydantic import BaseModel, Field

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

@tool(parse_docstring=True, tags=["tool", "chart", "visualization"])
def generate_chart_spec(
    chart_type: Literal["bar", "line", "pie", "area", "scatter"],
    title: str,
    data: List[Dict[str, Any]],
    x_key: str,
    y_keys: List[str],
    colors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Generates a structured chart specification for the frontend.
    Call this tool when the user asks for a visualization or when data needs to be plotted.
    """
    return {
        "type": chart_type,
        "title": title,
        "data": data,
        "xKey": x_key,
        "yKeys": y_keys,
        "colors": colors
    }
