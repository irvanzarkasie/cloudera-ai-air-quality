"""
Backfill Jakarta station metrics from live Udara + Open-Meteo daily PM2.5 trend.

Past days without official Udara history are marked is_synthetic=True (scaled from today's
snapshot using city-level Open-Meteo archive ratios).
"""

from __future__ import annotations

import hashlib
import json
import urllib.parse
from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd

from .jakarta_air_sources import JAKARTA_LAT, JAKARTA_LON, _http_get
from .jakarta_viz import fetch_station_snapshot_table


def days_for_months(months: float) -> int:
    """Calendar-ish day count for workshop windows (6 months ≈ 183 days)."""
    return max(1, int(round(months * 365.25 / 12)))


def _parse_udara_updated(updated_at: str | None) -> date:
    if not updated_at:
        return datetime.now().date()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(updated_at.strip(), fmt).date()
        except ValueError:
            continue
    return datetime.now().date()


def fetch_open_meteo_daily_pm25(start: date, end: date) -> pd.DataFrame:
    """Daily mean PM2.5 at Jakarta centroid from Open-Meteo air-quality archive."""
    q = urllib.parse.urlencode(
        {
            "latitude": JAKARTA_LAT,
            "longitude": JAKARTA_LON,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": "pm2_5",
            "timezone": "Asia/Jakarta",
        }
    )
    url = f"https://air-quality-api.open-meteo.com/v1/air-quality?{q}"
    payload = json.loads(_http_get(url))
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    pm = hourly.get("pm2_5") or []
    if not times:
        return pd.DataFrame(columns=["observation_date", "city_pm25_mean"])
    df = pd.DataFrame({"ts": times, "pm2_5": pm})
    df["observation_date"] = pd.to_datetime(df["ts"]).dt.date
    daily = df.groupby("observation_date", as_index=False)["pm2_5"].mean()
    daily.rename(columns={"pm2_5": "city_pm25_mean"}, inplace=True)
    return daily


def fetch_open_meteo_daily_pm25_chunked(
    start: date, end: date, *, chunk_days: int = 90
) -> pd.DataFrame:
    """Open-Meteo for long ranges (e.g. 6 months) in smaller API windows."""
    if start > end:
        return pd.DataFrame(columns=["observation_date", "city_pm25_mean"])
    parts: list[pd.DataFrame] = []
    cur = start
    while cur <= end:
        chunk_end = min(end, cur + timedelta(days=chunk_days - 1))
        parts.append(fetch_open_meteo_daily_pm25(cur, chunk_end))
        cur = chunk_end + timedelta(days=1)
    if not parts:
        return pd.DataFrame(columns=["observation_date", "city_pm25_mean"])
    daily = pd.concat(parts, ignore_index=True)
    return daily.drop_duplicates(subset=["observation_date"], keep="last")


def _station_pm25_proxy(row: pd.Series) -> float:
    metric = (row.get("dominant_metric") or "").upper().replace(" ", "")
    val = row.get("dominant_value")
    if metric in ("PM25", "PM2.5") and val is not None and not pd.isna(val):
        return float(val)
    ispu = row.get("ispu")
    if ispu is not None and not pd.isna(ispu):
        return max(5.0, float(ispu) * 0.45)
    return 25.0


def _noise_factor(station: str, day: date) -> float:
    h = hashlib.md5(f"{station}|{day}".encode()).hexdigest()
    bucket = int(h[:8], 16) / 0xFFFFFFFF
    return 0.95 + bucket * 0.10


def build_station_history(
    days: int | None = None,
    *,
    months: float | None = None,
) -> tuple[pd.DataFrame, str | None]:
    """
    Long-form history: one row per station per day (ispu + pm25 proxy).
    Anchor day (Udara snapshot) is live (is_synthetic=False); earlier days are synthetic.
    """
    if days is None:
        months = 6.0 if months is None else months
        days = days_for_months(months)
    if days < 1:
        raise ValueError("days must be >= 1")

    stations, updated_at = fetch_station_snapshot_table()
    if stations.empty:
        raise RuntimeError("No geolocated Udara stations")

    anchor_day = _parse_udara_updated(updated_at)
    start_day = anchor_day - timedelta(days=days - 1)
    city_daily = fetch_open_meteo_daily_pm25_chunked(start_day, anchor_day)
    city_by_date = {
        row["observation_date"]: row["city_pm25_mean"]
        for _, row in city_daily.iterrows()
    }
    anchor_pm = city_by_date.get(anchor_day)

    day_list = [start_day + timedelta(days=i) for i in range(days)]
    rows: list[dict[str, Any]] = []
    for day in day_list:
        city_pm = city_by_date.get(day)
        if anchor_pm and city_pm is not None and pd.notna(city_pm) and anchor_pm:
            trend = max(0.55, min(1.45, float(city_pm) / float(anchor_pm)))
        else:
            trend = 1.0
        is_live_day = day == anchor_day

        for _, st in stations.iterrows():
            base_ispu = float(st["ispu"]) if pd.notna(st.get("ispu")) else None
            base_pm = _station_pm25_proxy(st)
            station_name = st.get("station") or "unknown"
            jitter = 1.0 if is_live_day else _noise_factor(station_name, day)
            scale = 1.0 if is_live_day else trend * jitter

            if is_live_day and base_ispu is not None:
                ispu_val = base_ispu
                pm_val = base_pm
                synthetic = False
            else:
                synthetic = True
                ispu_val = round(base_ispu * scale, 2) if base_ispu is not None else None
                pm_val = round(base_pm * scale, 2)

            rows.append(
                {
                    "observation_date": day.isoformat(),
                    "station_name": station_name,
                    "kecamatan": st.get("kecamatan"),
                    "lat": st.get("lat"),
                    "lng": st.get("lng"),
                    "ispu": ispu_val,
                    "pm25_ugm3": pm_val,
                    "city_pm25_mean": float(city_pm) if city_pm is not None else None,
                    "trend_factor": trend if not is_live_day else 1.0,
                    "data_source": "udara.jakarta.go.id" if is_live_day else "synthetic+open-meteo-trend",
                    "is_synthetic": synthetic,
                    "udara_updated_at": updated_at,
                }
            )

    return pd.DataFrame(rows), updated_at


def build_seven_day_station_history(days: int = 7) -> tuple[pd.DataFrame, str | None]:
    """Backward-compatible alias."""
    return build_station_history(days=days)


if __name__ == "__main__":
    hist, ts = build_station_history(months=6)
    assert len(hist) > 0
    print("updated", ts, "rows", len(hist), "days", hist["observation_date"].nunique())
    print(hist.groupby("is_synthetic").size())
    print(hist.head(3))
