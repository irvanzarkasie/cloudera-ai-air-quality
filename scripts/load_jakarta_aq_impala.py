#!/usr/bin/env python3
"""
Fetch live Jakarta air quality, synthesize history (default 6 months), load into Impala.

Usage (from AirAware/):
  export IMPALA_USER=workshop-user040
  export IMPALA_PASSWORD='changeme'
  export IMPALA_HOST=coordinator-psedemo1-impala-1.dw-psedemo1-cdp-env.dp5i-5vkq.cloudera.site
  # or IMPALA_JDBC_URL='jdbc:impala://host:443/id_workshop;...;UID=...;PWD=...'

  python scripts/load_jakarta_aq_impala.py --replace-table
  python scripts/load_jakarta_aq_impala.py --months 6 --dry-run
  python scripts/load_jakarta_aq_impala.py --days 7 --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataclasses import replace

from agent_tools.impala_config import load_impala_settings
from agent_tools.jakarta_historical_synthetic import build_station_history, days_for_months

DEFAULT_TABLE = "jakarta_air_daily"


def connect_impala(settings):
    from agent_tools.impala_connect import connect

    return connect(settings)


def ensure_database(cursor, database: str) -> None:
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
    cursor.execute(f"USE {database}")


def ensure_table(cursor, table: str) -> None:
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
          observation_date STRING,
          station_name STRING,
          kecamatan STRING,
          lat DOUBLE,
          lng DOUBLE,
          ispu DOUBLE,
          pm25_ugm3 DOUBLE,
          city_pm25_mean DOUBLE,
          trend_factor DOUBLE,
          data_source STRING,
          is_synthetic BOOLEAN,
          udara_updated_at STRING,
          ingested_at TIMESTAMP
        )
        STORED AS PARQUET
        """
    )


def replace_table(cursor, table: str) -> None:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")
    ensure_table(cursor, table)


def _sql_literal(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "NULL"
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    return "'" + str(val).replace("'", "''") + "'"


def insert_rows(cursor, table: str, df, ingested_at: str, chunk: int = 200) -> None:
    rows_sql: list[str] = []
    for _, r in df.iterrows():
        vals = (
            r["observation_date"],
            r["station_name"],
            r["kecamatan"],
            float(r["lat"]) if r["lat"] is not None else None,
            float(r["lng"]) if r["lng"] is not None else None,
            float(r["ispu"]) if r["ispu"] is not None else None,
            float(r["pm25_ugm3"]) if r["pm25_ugm3"] is not None else None,
            float(r["city_pm25_mean"]) if r.get("city_pm25_mean") is not None else None,
            float(r["trend_factor"]) if r.get("trend_factor") is not None else None,
            r["data_source"],
            bool(r["is_synthetic"]),
            r.get("udara_updated_at"),
            ingested_at,
        )
        rows_sql.append("(" + ", ".join(_sql_literal(v) for v in vals) + ")")

    for i in range(0, len(rows_sql), chunk):
        part = ",\n".join(rows_sql[i : i + chunk])
        cursor.execute(f"INSERT INTO {table} VALUES\n{part}")
        print(f"Inserted rows {i + 1}-{min(i + chunk, len(rows_sql))} / {len(rows_sql)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Load Jakarta AQ history into Impala")
    parser.add_argument(
        "--months",
        type=float,
        default=6.0,
        help="History window in months (default 6); ignored if --days is set",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=None,
        help="Exact inclusive day count (overrides --months)",
    )
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build dataframe only; print summary, no Impala",
    )
    parser.add_argument(
        "--replace-table",
        action="store_true",
        help="DROP + CREATE table before load (safest for Parquet workshop reloads)",
    )
    args = parser.parse_args()

    if args.days is not None:
        df, updated = build_station_history(days=args.days)
        window = f"{args.days} days"
    else:
        df, updated = build_station_history(months=args.months)
        window = f"{args.months} months ({days_for_months(args.months)} days)"

    ingested_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Window: {window}", flush=True)
    print(f"Udara snapshot time: {updated}", flush=True)
    print(f"Rows: {len(df)}  stations: {df['station_name'].nunique()}  days: {df['observation_date'].nunique()}")
    print(df.groupby("is_synthetic").size())
    print("Date range:", df["observation_date"].min(), "→", df["observation_date"].max())

    if args.dry_run:
        print(df.head(5).to_string(index=False))
        return

    settings = load_impala_settings()
    # Connect to an existing DB first (id_workshop may not exist yet on first run).
    bootstrap_db = os.environ.get("IMPALA_BOOTSTRAP_DATABASE", "default")
    conn = connect_impala(replace(settings, database=bootstrap_db))
    try:
        cur = conn.cursor()
        ensure_database(cur, settings.database)
        if args.replace_table:
            replace_table(cur, args.table)
        else:
            ensure_table(cur, args.table)
        insert_rows(cur, args.table, df, ingested_at)
        cur.execute(f"SELECT COUNT(*) FROM {args.table}")
        total = cur.fetchone()[0]
        print(f"Loaded into {settings.database}.{args.table}; table row count now: {total}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
