#!/usr/bin/env python3
"""Document why main_v1 cannot answer the Impala analysis prompt."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

USER_PROMPT = (
    "Based on our data on the id_workshop.jakarta_air_daily table, inspect the last 7 days "
    "and highlight the top 10 kecamatan with the worst ISPU..."
)

def main() -> None:
    from main_v1 import AirQualityAnalysisCrew

    tools = AirQualityAnalysisCrew._initialize_tools()
    names = list(tools.keys())
    print("main_v1 AirQualityAnalysisCrew tools:", names)
    print()
    if "impala_readonly_query" not in names and "impala" not in " ".join(names).lower():
        print("GAP: No Impala/SQL tool — crew cannot query jakarta_air_daily.")
    print("Agents: input parser, weather, Udara snapshot retriever, LLM analyst only.")
    print()
    print("Expected behavior if you run main_v1 with the workshop prompt:")
    print("  - May call air_quality_tool (live Udara, NOT the Impala table)")
    print("  - Analyst may hallucinate kecamatan rankings without warehouse data")
    print()
    print("Use test_complex_analysis/run_complex_analysis_crew.py for steered prototype.")


if __name__ == "__main__":
    main()
