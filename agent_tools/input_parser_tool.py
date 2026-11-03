"""Parse user input for Jakarta live air-quality snapshot lab (no date range)."""

from typing import List, Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

DEFAULT_LOCATION = "Jakarta, Indonesia"


class SnapshotAirQualityInput(BaseModel):
    locations: List[str] = Field(
        default_factory=lambda: [DEFAULT_LOCATION],
        description="Focus on Jakarta, Indonesia for this lab.",
    )
    aq_parameters: List[str] = Field(
        ...,
        description="Air quality parameters to highlight (e.g. pm25, ispu, pm10).",
    )


class InputParserTool(BaseTool):
    name: str = "InputParserTool"
    description: str = (
        "Validates parameters for a current Jakarta air quality snapshot report: "
        "locations and aq_parameters only (no historical dates)."
    )
    args_schema: Type[BaseModel] = SnapshotAirQualityInput

    def _run(self, locations: List[str], aq_parameters: List[str]) -> str:
        if not aq_parameters:
            return "Error: At least one air quality parameter must be specified."
        locs = locations or [DEFAULT_LOCATION]
        if not any("jakarta" in loc.lower() or "dki" in loc.lower() for loc in locs):
            locs = [DEFAULT_LOCATION]
        summary = {
            "locations": locs,
            "aq_parameters": aq_parameters,
            "mode": "live_snapshot",
            "data_source": "udara.jakarta.go.id",
        }
        return f"Validated Input: {summary}"
