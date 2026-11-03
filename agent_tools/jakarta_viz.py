"""Jakarta SPKU map helpers for the workshop notebook (folium)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .jakarta_air_sources import JAKARTA_LAT, JAKARTA_LON, fetch_udara_spku_snapshot

# DKI / ISPU band colors (approximate official scale)
ISPU_BANDS: list[tuple[float, str, str]] = [
    (50, "#00e400", "Good (0–50)"),
    (100, "#ffff00", "Moderate (51–100)"),
    (150, "#ff7e00", "Unhealthy for sensitive groups (101–150)"),
    (200, "#ff0000", "Unhealthy (151–200)"),
    (300, "#8f3f97", "Very unhealthy (201–300)"),
    (float("inf"), "#7e0023", "Hazardous (>300)"),
]


def ispu_to_color(ispu: float | None) -> str:
    if ispu is None or (isinstance(ispu, float) and pd.isna(ispu)):
        return "#999999"
    for limit, color, _ in ISPU_BANDS:
        if ispu <= limit:
            return color
    return ISPU_BANDS[-1][1]


def fetch_station_snapshot_table() -> tuple[pd.DataFrame, str | None]:
    """One row per SPKU/LCS station with coordinates and ISPU."""
    stations, updated_at = fetch_udara_spku_snapshot()
    rows: list[dict[str, Any]] = []
    for st in stations:
        lat, lng = st.get("lat"), st.get("lng")
        if lat is None or lng is None:
            continue
        rows.append(
            {
                "station": st.get("name") or "unknown",
                "kecamatan": st.get("kecamatan"),
                "ispu": st.get("ispu"),
                "status": st.get("status"),
                "dominant_metric": st.get("dominantMetric"),
                "dominant_value": st.get("dominantRawValue"),
                "lat": float(lat),
                "lng": float(lng),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty and "ispu" in df.columns:
        df["ispu"] = pd.to_numeric(df["ispu"], errors="coerce")
        df["color"] = df["ispu"].map(ispu_to_color)
    return df, updated_at


def build_ispu_map(
    stations: pd.DataFrame,
    *,
    updated_at: str | None = None,
    zoom: int = 11,
) -> Any:
    """Interactive Folium map; returns folium.Map (display in Jupyter with final `m`)."""
    try:
        import folium
    except ImportError as e:
        raise ImportError(
            "folium is not installed. In the notebook, re-run the setup cell: "
            "ensure_minimal(ROOT). Or: pip install folium==0.19.6"
        ) from e

    m = folium.Map(location=[JAKARTA_LAT, JAKARTA_LON], zoom_start=zoom, tiles="OpenStreetMap")
    title = "Jakarta SPKU/LCS — ISPU snapshot"
    if updated_at:
        title = f"{title} (updated {updated_at})"
    for _, row in stations.iterrows():
        ispu = row.get("ispu")
        label = f"{row.get('station')}<br>ISPU: {ispu}<br>{row.get('kecamatan') or ''}"
        folium.CircleMarker(
            location=[row["lat"], row["lng"]],
            radius=8,
            color="#333333",
            weight=1,
            fill=True,
            fill_color=row.get("color") or "#999999",
            fill_opacity=0.85,
            popup=folium.Popup(label, max_width=280),
            tooltip=f"{row.get('station')}: ISPU {ispu}",
        ).add_to(m)

    legend_html = (
        "<div style=\"position: fixed; bottom: 24px; left: 24px; z-index: 9999;"
        " background: white; padding: 10px 12px; border: 1px solid #ccc;"
        " font-size: 12px; max-width: 260px;\">"
        f"<b>{title}</b><br>"
    )
    for _limit, color, label in ISPU_BANDS:
        legend_html += f'<div><span style="background:{color}; width:14px; height:14px; display:inline-block; margin-right:6px;"></span>{label}</div>'
    legend_html += "</div>"
    m.get_root().html.add_child(folium.Element(legend_html))
    return m


if __name__ == "__main__":
    table, ts = fetch_station_snapshot_table()
    assert len(table) > 0, "expected geolocated stations"
    print("stations", len(table), "updated", ts)
    print(table[["station", "ispu", "lat", "lng"]].head())
