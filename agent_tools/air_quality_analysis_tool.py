"""
Live Jakarta air quality snapshot via udara.jakarta.go.id (+ optional Open-Meteo grid).

Workshop fork: no OpenAQ historical pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Type

import pandas as pd
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from .jakarta_air_sources import fetch_jakarta_realtime_dataframe, is_jakarta_location

DEFAULT_LOCATION = "Jakarta, Indonesia"
_AGENT_MAX_ROWS = 80


def _ispu_extremes_block(df: pd.DataFrame, n: int = 5) -> str:
    if "parameter" not in df.columns or "value" not in df.columns:
        return ""
    ispu = df.loc[df["parameter"].astype(str).str.lower() == "ispu"].copy()
    if ispu.empty:
        return ""
    ispu = ispu.sort_values("value", ascending=False)
    loc_col = "location" if "location" in ispu.columns else None
    lines = ["ISPU extremes (official stations):"]
    lines.append(f"  Highest {n}:")
    for _, row in ispu.head(n).iterrows():
        loc = row[loc_col] if loc_col else "?"
        lines.append(f"    {row['value']:.1f} — {loc}")
    lines.append(f"  Lowest {n}:")
    for _, row in ispu.tail(n).iloc[::-1].iterrows():
        loc = row[loc_col] if loc_col else "?"
        lines.append(f"    {row['value']:.1f} — {loc}")
    return "\n".join(lines) + "\n\n"


def format_air_quality_for_agent(df: pd.DataFrame, max_rows: int = _AGENT_MAX_ROWS) -> str:
    if df.empty:
        return "No air quality data returned from udara.jakarta.go.id."
    obs = df["date"].dropna().unique().tolist() if "date" in df.columns else []
    extremes = _ispu_extremes_block(df)
    head = df.head(max_rows)
    body = head.to_string(index=False)
    tail = len(df) - len(head)
    extra = f"\n\n... ({tail} more rows omitted; total {len(df)} rows)" if tail > 0 else ""
    return f"Observation date(s): {obs}\nRows: {len(df)}\n\n{extremes}{body}{extra}"


class AirQualityAnalysisInput(BaseModel):
    locations: List[str] = Field(
        ...,
        description="Locations to label results (Jakarta/DKI for this lab).",
    )
    aq_parameters: Optional[List[str]] = Field(
        default=None,
        description="Optional filter e.g. ['pm25', 'ispu'].",
    )
    bounding_boxes: Optional[List[List[float]]] = Field(
        default=None,
        description="Ignored for Jakarta snapshot; pass null or [].",
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Ignored — snapshot is always current.",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Ignored — snapshot is always current.",
    )


class AirQualityAnalysisTool(BaseTool):
    name: str = "air_quality_analysis"
    description: str = (
        "Fetch the current official Jakarta air quality snapshot from udara.jakarta.go.id "
        "(DKI DLH SPKU/LCS stations). Returns PM/ISPU readings at the latest observation time. "
        "Date range and bounding boxes are accepted for workflow compatibility but are not used."
    )
    args_schema: Type[BaseModel] = AirQualityAnalysisInput

    def _run(
        self,
        locations: List[str],
        aq_parameters: Optional[List[str]] = None,
        bounding_boxes: Optional[List[List[float]]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        locs = locations or [DEFAULT_LOCATION]
        if not any(is_jakarta_location(loc) for loc in locs):
            locs = [DEFAULT_LOCATION]

        print(
            "[AirQualityAnalysisTool] Fetching live Jakarta SPKU snapshot from udara.jakarta.go.id "
            f"(requested locations={locations!r}; dates ignored)."
        )
        live_df = fetch_jakarta_realtime_dataframe(
            locs, aq_parameters, include_open_meteo=True
        )
        core = ["date", "parameter", "value", "units", "location"]
        if live_df.empty:
            return format_air_quality_for_agent(pd.DataFrame(columns=core))
        trimmed = live_df[[c for c in core if c in live_df.columns]]
        return format_air_quality_for_agent(trimmed)


if __name__ == "__main__":
    import re
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    tool = AirQualityAnalysisTool()
    today = datetime.now().strftime("%Y-%m-%d")
    out = tool.run(
        bounding_boxes=[],
        locations=[DEFAULT_LOCATION],
        start_date=today,
        end_date=today,
        aq_parameters=["pm25", "ispu"],
    )
    print(out[:2000])
    m = re.search(r"Rows:\s*(\d+)", out)
    assert m and int(m.group(1)) > 0, "expected live Jakarta rows"
