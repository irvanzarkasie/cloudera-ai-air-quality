#!/usr/bin/env python3
"""Steered CrewAI prototype for 7-day kecamatan ISPU analysis on Impala."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEST_DIR))

from crewai import Agent, Crew, LLM, Task

from agent_tools.crew_report import crew_result_text
from agent_tools.utils import ensure_openai_api_key
from impala_readonly_tool import ImpalaReadOnlyTool

WORKSHOP_USER_QUERY = """Based on our data on the id_workshop.jakarta_air_daily table, can you inspect the data from the last 7 days and highlight the top 10 kecamatan with the worst ISPU value?

Additionally, can you also identify top 3 kecamatan with the best positive trend of ISPU improvements during these 7 days?

Please note that each kecamatan will have multiple observation stations which you need to take into account. You may average the ISPU values from the observation stations on a particular kecamatan to get an approximation of the ISPU values for a kecamatan.

As for the ISPU improvement trend, compare ISPU for each kecamatan across the 7 days in time order. A positive improvement trend is ISPU moving from high to low over time (lower ISPU is better air quality).

You are NOT allowed to CREATE tables or TEMPORARY tables. Use WITH clauses for staging only.

Before final answers, run impala_readonly_query to validate counts and date range."""


SCHEMA_HINT = """
Table id_workshop.jakarta_air_daily (already in database id_workshop):
  observation_date STRING, station_name STRING, kecamatan STRING,
  ispu DOUBLE, is_synthetic BOOLEAN, pm25_ugm3 DOUBLE, ...
Last 7 days = 7 distinct observation_date values ending at MAX(observation_date).
"""


def build_crew(verbose: bool = True) -> Crew:
    llm = LLM(model=os.getenv("MODEL_NAME", "openai/gpt-4o-mini"), temperature=0.2, max_tokens=8192)
    sql_tool = ImpalaReadOnlyTool()

    analyst = Agent(
        role="Impala Air Quality Analyst",
        goal="Answer kecamatan ISPU questions using read-only SQL on jakarta_air_daily.",
        backstory=(
            "Expert in Impala SQL and Jakarta ISPU. Always aggregates stations to kecamatan "
            "before ranking. Uses WITH CTEs; never CREATE or TEMP tables."
        ),
        tools=[sql_tool],
        verbose=verbose,
        allow_delegation=False,
        llm=llm,
    )

    plan_task = Task(
        description=(
            f"User request:\n{WORKSHOP_USER_QUERY}\n\nSchema hint:{SCHEMA_HINT}\n"
            "Step 1: Query max(observation_date) and list the 7 dates used.\n"
            "Step 2: SQL with WITH — daily avg ISPU per kecamatan per day; then top 10 worst "
            "(highest mean ISPU over the 7 days).\n"
            "Step 3: SQL with WITH — for each kecamatan compute correlation of day index vs "
            "daily avg ISPU; pick 3 kecamatan with most negative correlation (steady high→low).\n"
            "Step 4: Write final report with tables, mention is_synthetic if relevant."
        ),
        agent=analyst,
        expected_output=(
            "Top 10 worst kecamatan list, top 3 improving trend kecamatan with brief methodology, "
            "SQL snippets used, and caveats."
        ),
    )

    return Crew(agents=[analyst], tasks=[plan_task], verbose=verbose)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("-o", "--output", default=str(TEST_DIR / "agent_report.md"))
    args = parser.parse_args()

    ensure_openai_api_key()
    crew = build_crew(verbose=not args.quiet)
    result = crew.kickoff()
    text = crew_result_text(result)
    Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(f"\nWrote {args.output} ({len(text)} chars)\n")
    print(text[:4000])
    if len(text) > 4000:
        print("\n... [see full file]")


if __name__ == "__main__":
    main()
