"""Live Jakarta air quality from public sources (DKI udara.jakarta.go.id + Open-Meteo grid)."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime
from typing import Any

import pandas as pd

UDARA_JAKARTA_URL = "https://udara.jakarta.go.id/"
USER_AGENT = "AirAware-Jakarta/1.0 (workshop; +https://udara.jakarta.go.id)"
JAKARTA_LAT, JAKARTA_LON = -6.2088, 106.8456

_METRIC_TO_PARAM = {
    "PM25": "pm25",
    "PM2.5": "pm25",
    "PM10": "pm10",
    "O3": "o3",
    "NO2": "no2",
    "SO2": "so2",
    "CO": "co",
}


def is_jakarta_location(location: str) -> bool:
    loc = (location or "").lower()
    return "jakarta" in loc or "dki" in loc


def any_jakarta_location(locations: list[str]) -> bool:
    return any(is_jakarta_location(loc) for loc in locations)


def _http_get(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def fetch_udara_spku_snapshot() -> tuple[list[dict[str, Any]], str | None]:
    """Official DKI DLH live SPKU/LCS snapshot embedded in homepage HTML."""
    html = _http_get(UDARA_JAKARTA_URL)
    updated = None
    m_time = re.search(r'window\.__SPKU_UPDATE_TIME__\s*=\s*"([^"]+)"', html)
    if m_time:
        updated = m_time.group(1)
    m_data = re.search(r"window\.__SPKU_DATA__\s*=\s*(\[.*?\]);", html, re.S)
    if not m_data:
        raise RuntimeError("Could not find window.__SPKU_DATA__ on udara.jakarta.go.id")
    return json.loads(m_data.group(1)), updated


def _parse_observation_date(updated_at: str | None) -> date:
    if not updated_at:
        return datetime.now().date()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(updated_at.strip(), fmt).date()
        except ValueError:
            continue
    return datetime.now().date()


def spku_to_dataframe(
    stations: list[dict[str, Any]],
    updated_at: str | None,
    aq_parameters: list[str] | None = None,
    location_label: str = "Jakarta, Indonesia",
) -> pd.DataFrame:
    """Long-format frame aligned with OpenAQ tool output columns."""
    obs_date = _parse_observation_date(updated_at)
    want = {p.lower() for p in aq_parameters} if aq_parameters else None
    rows: list[dict[str, Any]] = []

    for st in stations:
        station_name = st.get("name") or "unknown"
        loc = f"{location_label} — {station_name}"
        kec = st.get("kecamatan")
        if kec:
            loc = f"{loc} ({kec})"

        ispu = st.get("ispu")
        if ispu is not None and (want is None or "ispu" in want):
            rows.append(
                {
                    "date": obs_date,
                    "parameter": "ispu",
                    "value": float(ispu),
                    "units": "ISPU index",
                    "location": loc,
                    "source": "udara.jakarta.go.id",
                    "observed_at": updated_at,
                    "lat": st.get("lat"),
                    "lng": st.get("lng"),
                    "status": st.get("status"),
                    "kecamatan": st.get("kecamatan"),
                }
            )

        metric = (st.get("dominantMetric") or "").upper().replace(" ", "")
        param = _METRIC_TO_PARAM.get(metric, metric.lower() if metric else None)
        raw = st.get("dominantRawValue")
        if param and raw is not None and (want is None or param in want):
            rows.append(
                {
                    "date": obs_date,
                    "parameter": param,
                    "value": float(raw),
                    "units": "µg/m³",
                    "location": loc,
                    "source": "udara.jakarta.go.id",
                    "observed_at": updated_at,
                    "lat": st.get("lat"),
                    "lng": st.get("lng"),
                    "status": st.get("status"),
                    "kecamatan": st.get("kecamatan"),
                }
            )

    return pd.DataFrame(rows)


def fetch_open_meteo_jakarta_current() -> dict[str, Any]:
    """Model-based current PM at Jakarta centroid (no API key)."""
    q = urllib.parse.urlencode(
        {
            "latitude": JAKARTA_LAT,
            "longitude": JAKARTA_LON,
            "current": "pm2_5,pm10",
            "timezone": "Asia/Jakarta",
        }
    )
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{q}"
    return json.loads(_http_get(url))


def open_meteo_current_to_rows(payload: dict[str, Any], location_label: str) -> list[dict[str, Any]]:
    cur = payload.get("current") or {}
    t = cur.get("time")
    obs_date = _parse_observation_date(str(t).replace("T", " ") if t else None)
    rows = []
    for param, key, unit in (
        ("pm25", "pm2_5", "µg/m³"),
        ("pm10", "pm10", "µg/m³"),
    ):
        val = cur.get(key)
        if val is None:
            continue
        rows.append(
            {
                "date": obs_date,
                "parameter": param,
                "value": float(val),
                "units": unit,
                "location": f"{location_label} (Open-Meteo grid)",
                "source": "open-meteo.com",
                "observed_at": t,
                "lat": JAKARTA_LAT,
                "lng": JAKARTA_LON,
                "status": None,
                "kecamatan": None,
            }
        )
    return rows


def fetch_jakarta_realtime_dataframe(
    locations: list[str],
    aq_parameters: list[str] | None = None,
    *,
    include_open_meteo: bool = True,
) -> pd.DataFrame:
    """Combine DKI Udara SPKU snapshot and optional Open-Meteo current grid."""
    label = next((loc for loc in locations if is_jakarta_location(loc)), "Jakarta, Indonesia")
    stations, updated_at = fetch_udara_spku_snapshot()
    df = spku_to_dataframe(stations, updated_at, aq_parameters, location_label=label)

    if include_open_meteo:
        try:
            om = fetch_open_meteo_jakarta_current()
            extra = open_meteo_current_to_rows(om, label)
            if extra:
                df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)
        except (urllib.error.URLError, json.JSONDecodeError, KeyError) as e:
            print(f"[jakarta_air] Open-Meteo supplement skipped: {e}")

    if df.empty:
        return pd.DataFrame(
            columns=["date", "parameter", "value", "units", "location", "kecamatan", "status"]
        )
    return df


if __name__ == "__main__":
    df = fetch_jakarta_realtime_dataframe(["Jakarta, Indonesia"], ["pm25", "ispu"])
    assert not df.empty, "expected Jakarta live rows"
    assert "udara.jakarta.go.id" in df["source"].values
    print(df.head())
    print("rows", len(df), "stations~", df["location"].nunique())
