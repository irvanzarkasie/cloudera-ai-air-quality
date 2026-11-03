import os
from crewai import LLM, Crew, Agent, Task
from agent_tools.air_quality_analysis_tool import AirQualityAnalysisTool
from agent_tools.utils import ensure_openai_api_key
from agent_tools.weather_tools import CurrentWeatherTool
from agent_tools.input_parser_tool_v2 import InputParserTool

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")


class AirQualityAnalysisCrew:
    """Jakarta live snapshot crew with optional report author (v2 parser)."""

    def __init__(self, user_input: str):
        ensure_openai_api_key()
        self.user_input = user_input
        self.llm = self._configure_llm()
        self.tools = self._initialize_tools()
        self.agents = {}
        self.tasks = {}
        self.crew = None

        self._setup_agents()
        self._setup_tasks()
        self._initialize_crew()

    @staticmethod
    def _configure_llm() -> LLM:
        return LLM(
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=1000,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.1,
            stop=["END"],
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
            goal="Extract locations, aq_parameters, and optional author for a live snapshot report.",
            backstory="Parses user input for Jakarta live air quality; ignores historical dates.",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["input_parser_tool"]],
        )
        weather_data_integrator = Agent(
            role="Current Weather Specialist",
            goal="Retrieve current weather for locations in the snapshot workflow.",
            backstory="Summarizes present meteorological conditions.",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["weather_tool"]],
        )
        air_quality_retriever = Agent(
            role="Air Quality Data Retriever",
            goal="Fetch latest Jakarta SPKU data from udara.jakarta.go.id via air_quality_analysis.",
            backstory="Specialized in live DKI DLH air quality snapshots.",
            verbose=True,
            allow_delegation=False,
            tools=[self.tools["air_quality_tool"]],
        )
        air_quality_analyst = Agent(
            role="Air Quality Analyst",
            goal="Snapshot report with author attribution — no historical trends.",
            backstory="Interprets ISPU/PM across Jakarta monitoring stations.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
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
                f"Parse the user input: {self.user_input}. Use InputParserTool for locations, "
                "aq_parameters, and author. Ignore any dates mentioned by the user."
            ),
            agent=self.agents["input_parser_agent"],
            expected_output="Validated locations, aq_parameters, author, mode=live_snapshot.",
        )
        get_weather_data_task = Task(
            description=(
                "Call CurrentWeatherTool for each location from parsed context. "
                "Summarize current temperature, humidity, wind, precipitation."
            ),
            agent=self.agents["weather_data_integrator"],
            expected_output="Current weather per location with observation time.",
            context=[parse_user_input_task],
        )
        get_air_quality_data_task = Task(
            description=(
                "Call air_quality_tool with locations and aq_parameters from context; bounding_boxes=[]. "
                "Return live DataFrame from udara.jakarta.go.id."
            ),
            agent=self.agents["air_quality_retriever"],
            expected_output="Current air quality DataFrame (date, parameter, value, units, location).",
            context=[parse_user_input_task],
        )
        analysis_task = Task(
            description=(
                "Live snapshot report only — no historical trends. Include author from parse context. "
                "State observation time, compare stations, ISPU bands if applicable, current weather context. "
                "Source: udara.jakarta.go.id. Summary and Conclusion."
            ),
            agent=self.agents["air_quality_analyst"],
            expected_output="Author-attributed Jakarta air quality snapshot report.",
            context=[parse_user_input_task, get_air_quality_data_task, get_weather_data_task],
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
            verbose=True,
        )

    def execute(self):
        return self.crew.kickoff()


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jakarta live air quality snapshot (CrewAI v2).")
    parser.add_argument("--user-input", help="Natural language snapshot query.")
    args = parser.parse_args()

    user_query = args.user_input or (
        "Report current air quality for Jakarta from official SPKU data. "
        "Focus on pm25 and ispu. Author: Workshop Lab."
    )

    try:
        analysis_crew = AirQualityAnalysisCrew(user_input=user_query)
        report = analysis_crew.execute()
        print("\n--- Air Quality Snapshot Report ---")
        print(report)
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
