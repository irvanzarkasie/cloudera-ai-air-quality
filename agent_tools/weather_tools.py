"""
weather_tools.py

Author: Vish Rajagopalan
Company: Cloudera
Date: 2025-05-21

Description:
This module provides tools for retrieving historical weather data.
It includes a Pydantic model for weather tool input and a tool to
fetch daily historical weather information from Open-Meteo.com based
on a bounding box and date range.
"""

from typing import Type
import requests
from pydantic import BaseModel, Field
from crewai.tools import BaseTool 
from typing import List, Optional



class OpenMeteoWeatherInput(BaseModel):
    """Input for the OpenMeteoHistoricalWeatherTool using a bounding box."""
    # Bounding box format: [south_latitude, west_longitude, north_latitude, east_longitude]
    bounding_box: List[float] = Field(..., description="Bounding box coordinates in [south_lat, west_lon, north_lat, east_lon] format.")
    start_date: str = Field(..., description="The start date for historical weather data in YYYY-MM-DD format.")
    end_date: str = Field(..., description="The end date for historical weather data in YYYY-MM-DD format.")

# A bounding box, or bbox, is a rectangular area defined by four coordinates: 
# two representing the southwest corner (minimum longitude, minimum latitude) and 
# two representing the northeast corner (maximum longitude, maximum latitude). 
# It's essentially a way to define a geographical area on a map or within a dataset. 

class HistoricalWeatherTool(BaseTool):
    name: str = "HistoricalWeatherTool"
    description: str = (
        "Retrieves DAILY historical weather data (mean temperature, max temperature, min temperature, "
        "sum of precipitation, mean wind speed, mean relative humidity) for a location "
        "defined by a bounding box and a date range from Open-Meteo.com (no API key required for non-commercial use). "
        "The tool internally calculates the center point of the bounding box for the API query."
    )
    args_schema: Type[BaseModel] = OpenMeteoWeatherInput

    def _run(self, bounding_box: List[float], start_date: str, end_date: str) -> str:
        if len(bounding_box) != 4:
            return "Error: Bounding box must contain exactly 4 float values: [south_lat, west_lon, north_lat, east_lon]."

        # bounding_box is in [south_lat, west_lon, north_lat, east_lon]
        south_lat, west_lon, north_lat, east_lon = bounding_box[0], bounding_box[1], bounding_box[2], bounding_box[3]
        
        # Calculate the center point of the bounding box
        center_latitude = (south_lat + north_lat) / 2
        center_longitude = (west_lon + east_lon) / 2

        base_url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": center_latitude,
            "longitude": center_longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_mean,relative_humidity_2m_mean",
            "timezone": "auto" # It's good practice to specify timezone for daily data
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors
            data = response.json()

            if "daily" not in data:
                return f"No daily weather data found for the bounding box {bounding_box} between {start_date} and {end_date}. API response: {data}"

            daily_data = data["daily"]
            times = daily_data.get("time", [])
            temp_means = daily_data.get("temperature_2m_mean", [])
            temp_maxs = daily_data.get("temperature_2m_max", [])
            temp_mins = daily_data.get("temperature_2m_min", [])
            precipitations = daily_data.get("precipitation_sum", [])
            wind_speeds_mean = daily_data.get("wind_speed_10m_mean", [])
            humidities_mean = daily_data.get("relative_humidity_2m_mean", [])

            weather_summary = []
            for i in range(len(times)):
                summary = {
                    "date": times[i],
                    "temperature_mean_2m": temp_means[i] if i < len(temp_means) else "N/A",
                    "temperature_max_2m": temp_maxs[i] if i < len(temp_maxs) else "N/A",
                    "temperature_min_2m": temp_mins[i] if i < len(temp_mins) else "N/A",
                    "precipitation_sum": precipitations[i] if i < len(precipitations) else "N/A",
                    "wind_speed_10m_mean": wind_speeds_mean[i] if i < len(wind_speeds_mean) else "N/A",
                    "relative_humidity_2m_mean": humidities_mean[i] if i < len(humidities_mean) else "N/A"
                }
                weather_summary.append(summary)

            return str(weather_summary) # Return as string for LLM processing
        except requests.exceptions.RequestException as e:
            return f"Error fetching weather data from Open-Meteo for bounding box {bounding_box}: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"


class CurrentWeatherInput(BaseModel):
    """Input for current conditions at a named place (Jakarta lab default)."""

    location: str = Field(
        default="Jakarta, Indonesia",
        description="Place name; Jakarta/DKI uses the official DKI center coordinates.",
    )


class CurrentWeatherTool(BaseTool):
    name: str = "CurrentWeatherTool"
    description: str = (
        "Retrieves CURRENT weather (temperature, wind, humidity, precipitation) "
        "from Open-Meteo forecast API for a location. No API key required. "
        "Use for live air-quality snapshot context, not historical date ranges."
    )
    args_schema: Type[BaseModel] = CurrentWeatherInput

    def _run(self, location: str = "Jakarta, Indonesia") -> str:
        from .jakarta_air_sources import JAKARTA_LAT, JAKARTA_LON

        lat, lon = JAKARTA_LAT, JAKARTA_LON
        if location and "jakarta" not in location.lower() and "dki" not in location.lower():
            try:
                from .bounding_box_extractor_tool import BoundingBoxExtractorTool

                bbox = BoundingBoxExtractorTool().run(location=location)
                if isinstance(bbox, list) and len(bbox) == 4:
                    south, west, north, east = bbox
                    lat = (south + north) / 2
                    lon = (west + east) / 2
            except Exception:
                pass

        base_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": (
                "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m"
            ),
            "timezone": "Asia/Jakarta",
        }
        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            current = data.get("current") or {}
            summary = {
                "location": location,
                "latitude": lat,
                "longitude": lon,
                "observation_time": current.get("time"),
                "temperature_2m_c": current.get("temperature_2m"),
                "relative_humidity_2m_pct": current.get("relative_humidity_2m"),
                "precipitation_mm": current.get("precipitation"),
                "wind_speed_10m_kmh": current.get("wind_speed_10m"),
                "wind_direction_10m_deg": current.get("wind_direction_10m"),
            }
            return str(summary)
        except requests.exceptions.RequestException as e:
            return f"Error fetching current weather for {location}: {e}"
        except Exception as e:
            return f"An unexpected error occurred: {e}"


if __name__ == "__main__":
    print(CurrentWeatherTool().run(location="Jakarta, Indonesia"))

# Only for Testing
# from bounding_box_extractor_tool import BoundingBoxExtractorTool
# def main(location: str, start_date: str, end_date: str):
#     """
#     Main function to get the bounding box for a location and then fetch historical weather details.

#     Args:
#         location (str): The name of the location.
#         start_date (str): The start date for weather data in YYYY-MM-DD format.
#         end_date (str): The end date for weather data in YYYY-MM-DD format.
#     """
#     bbox_extractor = BoundingBoxExtractorTool()
#     weather_tool = HistoricalWeatherTool()

#     print(f"Getting bounding box for {location}...")
#     bounding_box = bbox_extractor.run(location=location)

#     if isinstance(bounding_box, str):
#         print(f"Error: {bounding_box}")
#         return

#     print(f"Bounding box for {location}: {bounding_box}")
#     print(f"Fetching weather details for {location} from {start_date} to {end_date}...")
#     weather_details = weather_tool.run(bounding_box=bounding_box, start_date=start_date, end_date=end_date)
    
#     print("\nWeather Details:")
#     print(weather_details)

# if __name__ == "__main__":
#     # Example usage:
#     location_name = "Tokyo"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)

#     print("\n" + "="*50 + "\n")

#     location_name = "London"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
#     print("\n" + "="*50 + "\n")

#     location_name = "Frankfurt"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
    
#     location_name = "Chennai"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)
    
#     location_name = "New Delhi, India"
#     start = "2025-01-01"
#     end = "2025-01-03"
#     main(location_name, start, end)