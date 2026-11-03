import os
import sys

from crewai import LLM, Crew, Agent, Task
from agent_tools.air_quality_analysis_tool import AirQualityAnalysisTool
from agent_tools.crew_report import crew_result_text
from agent_tools.input_parser_tool import InputParserTool
from agent_tools.utils import ensure_openai_api_key
from agent_tools.weather_tools import CurrentWeatherTool

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
DEFAULT_LOCATION = "Jakarta, Indonesia"


def _guess_aq_parameters(user_input: str) -> list[str]:
    q = user_input.lower()
    found: list[str] = []
    for needle, param in (
        ("pm2.5", "pm25"),
        ("pm25", "pm25"),
        ("pm10", "pm10"),
        ("ispu", "ispu"),
        ("no2", "no2"),
        ("o3", "o3"),
    ):
        if needle in q:
            found.append(param)
    return list(dict.fromkeys(found)) or ["pm25", "ispu"]


def run_dry_snapshot(user_input: str) -> str:
    """Fetch Udara + weather without CrewAI (no OPENAI_API_KEY required)."""
    params = _guess_aq_parameters(user_input)
    locs = [DEFAULT_LOCATION]
    validated = InputParserTool()._run(locs, params)
    weather = CurrentWeatherTool()._run(DEFAULT_LOCATION)
    air = AirQualityAnalysisTool()._run(
        locations=locs, aq_parameters=params, bounding_boxes=[]
    )
    return (
        "--- Dry run (tools only, no LLM) ---\n\n"
        f"{validated}\n\n"
        f"Current weather:\n{weather}\n\n"
        f"Air quality snapshot:\n{air}\n"
    )


class AirQualityAnalysisCrew:
    """Jakarta live snapshot crew (udara.jakarta.go.id + current weather)."""

    def __init__(self, user_input: str, *, verbose: bool = True):
        ensure_openai_api_key()
        self.user_input = user_input
        self.verbose = verbose
        self.analyst_llm = self._configure_analyst_llm()
        self.tools = self._initialize_tools()
        self.agents = {}
        self.tasks = {}
        self.crew = None

        self._setup_agents()
        self._setup_tasks()
        self._initialize_crew()

    @staticmethod
    def _configure_analyst_llm() -> LLM:
        max_tokens = int(os.getenv("AIRAWARE_MAX_TOKENS", "8192"))
        return LLM(
            model=MODEL_NAME,
            temperature=0.5,
            max_tokens=max_tokens,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            seed=42,
        )

    @staticmethod
    def _initialize_tools():
        return {
            "input_parser_tool": InputParserTool(),
            "air_quality_tool": AirQualityAnalysisTool(),
            "weather_tool": CurrentWeatherTool(),
        }

    def _setup_agents(self):
        input_parser_agent = Agent(
            role="Input Data Parser",
            goal="Extract locations and air quality parameters for a live snapshot report.",
            backstory=(
                "Parses natural language into structured fields for Jakarta live air quality. "
                "Ignores historical date ranges if the user mentions them."
            ),
            verbose=self.verbose,
            allow_delegation=False,
            tools=[self.tools["input_parser_tool"]],
        )
        weather_data_integrator = Agent(
            role="Current Weather Specialist",
            goal="Retrieve current weather for the same locations as the air quality snapshot.",
            backstory="Summarizes present meteorological conditions that may affect pollution dispersion.",
            verbose=self.verbose,
            allow_delegation=False,
            tools=[self.tools["weather_tool"]],
        )
        air_quality_retriever = Agent(
            role="Air Quality Data Retriever",
            goal=(
                "Fetch the latest official Jakarta SPKU/LCS readings from udara.jakarta.go.id "
                "using air_quality_analysis."
            ),
            backstory="Specialized in live DKI DLH air quality snapshots.",
            verbose=self.verbose,
            allow_delegation=False,
            tools=[self.tools["air_quality_tool"]],
        )
        air_quality_analyst = Agent(
            role="Air Quality Analyst",
            goal=(
                "Produce a concise snapshot report from live station readings and current weather — "
                "no historical trend analysis."
            ),
            backstory="Experienced in interpreting ISPU/PM levels across Jakarta monitoring stations.",
            verbose=self.verbose,
            allow_delegation=False,
            llm=self.analyst_llm,
        )

        self.agents = {
            "input_parser_agent": input_parser_agent,
            "weather_data_integrator": weather_data_integrator,
            "air_quality_retriever": air_quality_retriever,
            "air_quality_analyst": air_quality_analyst,
        }

    def _setup_tasks(self):
        parse_user_input_task = Task(
            description=(
                f"Parse the user input: {self.user_input}. Use InputParserTool to extract "
                "locations and aq_parameters only. Do not require or validate start/end dates."
            ),
            agent=self.agents["input_parser_agent"],
            expected_output=(
                "Validated locations, aq_parameters, mode=live_snapshot, data_source=udara.jakarta.go.id."
            ),
        )
        get_weather_data_task = Task(
            description=(
                "From parsed locations in context, call CurrentWeatherTool for each location "
                "(or once for Jakarta). Summarize current temperature, humidity, wind, and precipitation."
            ),
            agent=self.agents["weather_data_integrator"],
            expected_output="Current weather summary per location with observation time.",
            context=[parse_user_input_task],
        )
        get_air_quality_data_task = Task(
            description=(
                "Call air_quality_tool with locations and aq_parameters from context. "
                "Pass bounding_boxes=[]; dates are optional and ignored. "
                "Return the live snapshot text from udara.jakarta.go.id (includes ISPU extremes summary)."
            ),
            agent=self.agents["air_quality_retriever"],
            expected_output=(
                "Air quality snapshot text with observation date, ISPU extremes, and sample rows."
            ),
            context=[parse_user_input_task],
        )
        analysis_task = Task(
            description=(
                f"User request: {self.user_input}\n\n"
                "Write a live snapshot report (not historical trends). Use the ISPU extremes block "
                "and weather context from prior tasks. Highlight the worst and best ISPU stations "
                "with station names and values. Do not enumerate every station — at most 5 highest "
                "and 5 lowest ISPU unless the user asked for a full table. "
                "State observation time, brief ISPU category explanation, weather/dispersion note, "
                "Summary and Conclusion. Source: udara.jakarta.go.id. Plain markdown, complete sentences."
            ),
            agent=self.agents["air_quality_analyst"],
            expected_output=(
                "Complete markdown report (not truncated mid-sentence) with worst/best ISPU stations."
            ),
            context=[get_air_quality_data_task, get_weather_data_task],
        )

        self.tasks = {
            "parse_user_input_task": parse_user_input_task,
            "get_weather_data_task": get_weather_data_task,
            "get_air_quality_data_task": get_air_quality_data_task,
            "analysis_task": analysis_task,
        }

    def _initialize_crew(self):
        self.crew = Crew(
            agents=list(self.agents.values()),
            tasks=list(self.tasks.values()),
            verbose=self.verbose,
        )

    def execute(self):
        return self.crew.kickoff()


def _write_report(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jakarta live air quality snapshot (CrewAI).")
    parser.add_argument(
        "--user-input",
        help="Natural language query, e.g. current Jakarta pm25 and ispu from official SPKU data.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run Udara + weather tools only (no OpenAI / CrewAI).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Less CrewAI console UI (recommended on CDSW/SSH).",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write the full report to this file (recommended on CAI/CDSW).",
    )
    args = parser.parse_args()

    user_query = args.user_input or (
        "Report current air quality for Jakarta, Indonesia from official SPKU data. "
        "Focus on pm25 and ispu."
    )

    try:
        if args.dry_run:
            print(run_dry_snapshot(user_query))
            raise SystemExit(0)

        verbose = not args.quiet and os.getenv("AIRAWARE_QUIET", "").lower() not in (
            "1",
            "true",
            "yes",
        )
        analysis_crew = AirQualityAnalysisCrew(user_input=user_query, verbose=verbose)
        result = analysis_crew.execute()
        report = crew_result_text(result)

        out_path = args.output or os.getenv("AIRAWARE_REPORT_PATH")
        if out_path:
            _write_report(out_path, report)
            print(f"Full report written to {out_path} ({len(report)} characters)", file=sys.stderr)

        print("\n--- Air Quality Snapshot Report ---\n")
        sys.stdout.write(report)
        if not report.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1) from e
    except KeyError as e:
        print(f"Configuration error (missing key {e!r}).")
    except Exception as e:
        import traceback

        print(f"An unexpected error occurred: {e!r}")
        traceback.print_exc()
