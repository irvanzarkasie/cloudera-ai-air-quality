#!/usr/bin/env python3
"""Compute reference answers for the 7-day kecamatan ISPU lab (pandas on Impala extract)."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_tools.impala_config import load_impala_settings
from agent_tools.impala_connect import connect

FETCH_SQL = """
SELECT observation_date, kecamatan, station_name, ispu, is_synthetic
FROM jakarta_air_daily
WHERE kecamatan IS NOT NULL AND TRIM(kecamatan) != ''
  AND ispu IS NOT NULL
"""


def fetch_df() -> pd.DataFrame:
    settings = load_impala_settings()
    bootstrap = __import__("os").environ.get("IMPALA_BOOTSTRAP_DATABASE", "default")
    conn = connect(replace(settings, database=bootstrap))
    try:
        cur = conn.cursor()
        cur.execute(f"USE {settings.database}")
        cur.execute(FETCH_SQL)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    return pd.DataFrame(rows, columns=cols)


def main() -> None:
    df = fetch_df()
    df["observation_date"] = df["observation_date"].astype(str)
    last7 = sorted(df["observation_date"].unique())[-7:]
    d7 = df[df["observation_date"].isin(last7)].copy()
    print("Last 7 dates:", last7)
    print("Rows in window:", len(d7), "synthetic pct:", d7["is_synthetic"].mean())

    daily = (
        d7.groupby(["observation_date", "kecamatan"], as_index=False)
        .agg(avg_ispu=("ispu", "mean"), stations=("station_name", "nunique"))
    )
    worst = (
        daily.groupby("kecamatan", as_index=False)
        .agg(mean_ispu_7d=("avg_ispu", "mean"), days=("observation_date", "nunique"))
        .sort_values("mean_ispu_7d", ascending=False)
        .head(10)
    )
    print("\n=== TOP 10 WORST KECAMATAN (highest mean ISPU, last 7 days) ===")
    print(worst.to_string(index=False))

    daily["day_idx"] = daily["observation_date"].map({d: i for i, d in enumerate(last7)})

    def trend_corr(g: pd.DataFrame) -> float:
        if len(g) < 5:
            return float("nan")
        return g["day_idx"].corr(g["avg_ispu"], method="pearson")

    trends = (
        daily.groupby("kecamatan")
        .apply(trend_corr, include_groups=False)
        .reset_index(name="ispu_day_corr")
    )
    trends = trends.dropna().sort_values("ispu_day_corr", ascending=True)
    print("\n=== TOP 3 IMPROVEMENT TREND (most negative ISPU vs time correlation) ===")
    print(
        "Negative correlation = ISPU tends to fall as days advance (high → low).\n"
    )
    print(trends.head(3).to_string(index=False))


if __name__ == "__main__":
    main()
