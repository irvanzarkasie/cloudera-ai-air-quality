"""Read-only Impala SQL for agent analysis (SELECT / WITH only)."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_FORBIDDEN = re.compile(
    r"\b(CREATE|DROP|INSERT|UPDATE|DELETE|ALTER|TRUNCATE|GRANT|REVOKE|"
    r"INVALIDATE|COMPUTE|SET)\b",
    re.IGNORECASE,
)
_TEMP_TABLE = re.compile(r"\bTEMPORARY\b|\bTEMP\b", re.IGNORECASE)


class ImpalaSqlInput(BaseModel):
    sql: str = Field(
        ...,
        description=(
            "Single read-only Impala statement. Must be SELECT or WITH ... SELECT. "
            "No CREATE/DROP/INSERT. No TEMPORARY tables; use WITH for staging."
        ),
    )
    max_rows: int = Field(default=500, description="Max rows returned to the agent.")


class ImpalaReadOnlyTool(BaseTool):
    name: str = "impala_readonly_query"
    description: str = (
        "Run a read-only SQL query against Impala (id_workshop.jakarta_air_daily). "
        "Use WITH clauses for multi-step logic. Returns result rows as text."
    )
    args_schema: Type[BaseModel] = ImpalaSqlInput

    def _validate_sql(self, sql: str) -> None:
        stripped = sql.strip().rstrip(";")
        if _FORBIDDEN.search(stripped):
            raise ValueError("Only read-only SELECT/WITH queries are allowed.")
        if _TEMP_TABLE.search(stripped):
            raise ValueError("TEMPORARY tables are not allowed; use WITH ... AS (...) instead.")
        upper = stripped.lstrip().upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH")):
            raise ValueError("Query must start with SELECT or WITH.")

    def _run(self, sql: str, max_rows: int = 500) -> str:
        from dataclasses import replace

        from agent_tools.impala_config import load_impala_settings
        from agent_tools.impala_connect import connect

        self._validate_sql(sql)
        settings = load_impala_settings()
        bootstrap = __import__("os").environ.get("IMPALA_BOOTSTRAP_DATABASE", "default")
        conn = connect(replace(settings, database=bootstrap))
        try:
            cur = conn.cursor()
            cur.execute(f"USE {settings.database}")
            cur.execute(sql.strip().rstrip(";"))
            cols = [d[0] for d in (cur.description or [])]
            rows = cur.fetchmany(max_rows)
            extra = cur.fetchone()
            tail = "\n...(truncated)" if extra else ""
            if not rows:
                return "Query returned 0 rows."
            lines = ["\t".join(cols)]
            for row in rows:
                lines.append("\t".join("" if v is None else str(v) for v in row))
            return "\n".join(lines) + tail
        finally:
            conn.close()


if __name__ == "__main__":
    tool = ImpalaReadOnlyTool()
    out = tool.run(
        sql="""
        WITH mx AS (SELECT MAX(observation_date) AS d FROM jakarta_air_daily)
        SELECT COUNT(DISTINCT observation_date) AS n FROM jakarta_air_daily
        WHERE observation_date >= CAST(DATE_SUB(CAST((SELECT d FROM mx) AS TIMESTAMP), 6) AS STRING)
        """
    )
    print(out)
