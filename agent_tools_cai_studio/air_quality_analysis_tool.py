"""Jakarta live air quality snapshot for CAI Studio (udara.jakarta.go.id)."""

from pydantic import BaseModel, Field
from typing import List, Optional, Any
import json
import argparse
import pandas as pd


class UserParameters(BaseModel):
    api_key: Optional[str] = Field(
        default=None,
        description="Unused for Jakarta snapshot; kept for Studio compatibility.",
    )


class ToolParameters(BaseModel):
    bounding_boxes: Optional[List[List[float]]] = Field(
        default=None,
        description="Ignored for Jakarta snapshot.",
    )
    locations: Optional[str] = Field(default=["Jakarta, Indonesia"], description="Location labels (Jakarta/DKI for this lab).")
    start_date: Optional[str] = Field(default=None, description="Ignored — current snapshot only.")
    end_date: Optional[str] = Field(default=None, description="Ignored — current snapshot only.")
    aq_parameters: Optional[List[str]] = Field(
        default=None,
        description="Optional filter e.g. ['pm25', 'ispu'].",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    import sys
    from pathlib import Path

    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from agent_tools.jakarta_air_sources import fetch_jakarta_realtime_dataframe

    locs = args.locations or ["Jakarta, Indonesia"]
    live_df = fetch_jakarta_realtime_dataframe(
        locs, args.aq_parameters, include_open_meteo=True
    )
    core = ["date", "parameter", "value", "units", "location", "kecamatan", "status"]
    if live_df.empty:
        return pd.DataFrame(columns=core)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.max_columns', None)
    pd.set_option("display.max_rows", 200)
    return live_df[[c for c in core if c in live_df.columns]]


OUTPUT_KEY = "tool_output"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="User configuration in JSON format")
    parser.add_argument("--tool-params", required=True, help="Tool arguments in JSON format")
    args = parser.parse_args()

    user_dict = json.loads(args.user_params)
    tool_dict = json.loads(args.tool_params)

    config = UserParameters(**user_dict)
    params = ToolParameters(**tool_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, output)
