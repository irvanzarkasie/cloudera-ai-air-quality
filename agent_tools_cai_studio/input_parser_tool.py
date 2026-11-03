"""
Parse and validate input for Jakarta live air quality snapshot (no date range).
"""

import json
import argparse
from pydantic import BaseModel, Field
from typing import List, Optional, Any

DEFAULT_LOCATION = "Jakarta, Indonesia"


class UserParameters(BaseModel):
    pass


class ToolParameters(BaseModel):
    locations: List[str] = Field(
        default_factory=lambda: [DEFAULT_LOCATION],
        description="Locations for the snapshot (Jakarta/DKI for this lab).",
    )
    aq_parameters: Optional[str] = Field(
        default=["pm25", "ispu"],
        description="Air quality parameters to highlight (e.g., pm25, ispu).",
    )
    start_date: Optional[str] = Field(
        None,
        description="Ignored — snapshot is always current.",
    )
    end_date: Optional[str] = Field(
        None,
        description="Ignored — snapshot is always current.",
    )


def run_tool(config: UserParameters, args: ToolParameters) -> Any:
    aqparams = args.aq_parameters or ["pm25", "ispu"]
    locs = args.locations or [DEFAULT_LOCATION]
    if not any("jakarta" in loc.lower() or "dki" in loc.lower() for loc in locs):
        locs = [DEFAULT_LOCATION]
    return {
        "validated_input": {
            "locations": locs,
            "aq_parameters": aqparams,
            "mode": "live_snapshot",
            "data_source": "udara.jakarta.go.id",
        }
    }


OUTPUT_KEY = "tool_output"

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-params", required=True, help="Tool configuration")
    parser.add_argument("--tool-params", required=True, help="Tool arguments")
    args = parser.parse_args()

    user_dict = json.loads(args.user_params)
    tool_dict = json.loads(args.tool_params)

    config = UserParameters(**user_dict)
    params = ToolParameters(**tool_dict)

    output = run_tool(config, params)
    print(OUTPUT_KEY, output)
