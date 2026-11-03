"""Reference solution: same Jakarta live snapshot workflow as main_v1.py."""

from main_v1 import AirQualityAnalysisCrew

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jakarta live air quality snapshot (full solution).")
    parser.add_argument("--user-input", help="Natural language snapshot query.")
    args = parser.parse_args()

    user_query = args.user_input or (
        "Report current air quality for Jakarta, Indonesia from official SPKU data. "
        "Focus on pm25 and ispu."
    )

    try:
        report = AirQualityAnalysisCrew(user_input=user_query).execute()
        print("\n--- Air Quality Snapshot Report ---")
        print(report)
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
