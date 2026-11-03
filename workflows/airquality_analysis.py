import os
from typing import List, Optional
from crewai import LLM, Crew, Agent, Task
from agent_tools.air_quality_analysis_tool import AirQualityAnalysisTool
from agent_tools.weather_tools import CurrentWeatherTool
from agent_tools.input_parser_tool import InputParserTool

MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")

llm = LLM(
    model=MODEL_NAME,
    temperature=0.7,
    max_tokens=1000,
    top_p=0.9,
    frequency_penalty=0.1,
    presence_penalty=0.1,
    stop=["END"],
    seed=42,
)

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

input_parser_tool = InputParserTool()
air_quality_tool = AirQualityAnalysisTool()
weather_tool = CurrentWeatherTool()


def create_air_quality_analysis_crew(
    locations: List[str],
    aq_parameters: Optional[List[str]] = None,
    user_input: Optional[str] = None,
):
    """Jakarta live snapshot crew (dates optional/ignored for compatibility)."""
    locs = locations or ["Jakarta, Indonesia"]
    params = aq_parameters or ["pm25", "ispu"]
    query = user_input or (
        f"Current air quality snapshot for {', '.join(locs)} focusing on {', '.join(params)}."
    )

    input_parser_agent = Agent(
        role="Input Data Parser",
        goal="Validate locations and parameters for live snapshot mode.",
        backstory="Workshop parser for udara.jakarta.go.id.",
        verbose=True,
        allow_delegation=False,
        tools=[input_parser_tool],
    )

    parse_task = Task(
        description=f"Parse: {query}. Use InputParserTool; ignore dates.",
        agent=input_parser_agent,
        expected_output="Validated live_snapshot input.",
    )

    weather_data_integrator = Agent(
        role="Current Weather Specialist",
        goal="Current weather for snapshot context.",
        backstory="Open-Meteo current conditions.",
        verbose=True,
        allow_delegation=False,
        tools=[weather_tool],
    )

    get_weather_data_task = Task(
        description="Call CurrentWeatherTool for each location from context.",
        agent=weather_data_integrator,
        expected_output="Current weather summary.",
        context=[parse_task],
    )

    air_quality_retriever = Agent(
        role="Air Quality Data Retriever",
        goal="Fetch live Jakarta SPKU data from udara.jakarta.go.id.",
        backstory="DKI DLH snapshot specialist.",
        verbose=True,
        allow_delegation=False,
        tools=[air_quality_tool],
    )

    get_air_quality_data_task = Task(
        description=(
            f"Call air_quality_tool for locations {locs} and parameters {params}; "
            "bounding_boxes=[]; return current DataFrame."
        ),
        agent=air_quality_retriever,
        expected_output="Live air quality DataFrame.",
        context=[parse_task],
    )

    air_quality_analyst = Agent(
        role="Air Quality Analyst",
        goal="Snapshot report — no historical trends.",
        backstory="ISPU/PM interpretation across Jakarta stations.",
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )

    analysis_task = Task(
        description=(
            "Snapshot report with observation time, station comparison, ISPU context, "
            "current weather; source udara.jakarta.go.id."
        ),
        agent=air_quality_analyst,
        expected_output="Summary and conclusion for current conditions.",
        context=[get_air_quality_data_task, get_weather_data_task],
    )

    crew = Crew(
        agents=[
            input_parser_agent,
            weather_data_integrator,
            air_quality_retriever,
            air_quality_analyst,
        ],
        tasks=[parse_task, get_weather_data_task, get_air_quality_data_task, analysis_task],
        verbose=True,
    )

    return crew.kickoff()
