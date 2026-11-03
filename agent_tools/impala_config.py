"""Impala connection settings from environment (never commit passwords)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ImpalaSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    use_ssl: bool = True
    http_path: str = "cliservice"
    auth_mechanism: str = "PLAIN"


def _parse_jdbc(jdbc_url: str) -> ImpalaSettings:
    # jdbc:impala://host:port/db;key=value;...
    m = re.match(
        r"jdbc:impala://([^:/]+):(\d+)/([^;?]+)(?:;(.*))?",
        jdbc_url.strip(),
        re.I,
    )
    if not m:
        raise ValueError("Invalid IMPALA_JDBC_URL format")
    host, port, database, rest = m.group(1), int(m.group(2)), m.group(3), m.group(4) or ""
    opts: dict[str, str] = {}
    for part in rest.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            opts[k.strip().lower()] = v.strip()
    user = opts.get("uid") or os.environ.get("IMPALA_USER", "")
    password = opts.get("pwd") or os.environ.get("IMPALA_PASSWORD", "")
    if password == "PASSWORD":
        password = os.environ.get("IMPALA_PASSWORD", password)
    http_path = opts.get("httppath") or "cliservice"
    ssl = opts.get("ssl", "1") in ("1", "true", "True")
    return ImpalaSettings(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        use_ssl=ssl,
        http_path=http_path,
    )


def load_impala_settings() -> ImpalaSettings:
    jdbc = os.environ.get("IMPALA_JDBC_URL")
    if jdbc:
        return _parse_jdbc(jdbc)
    host = os.environ.get("IMPALA_HOST")
    user = os.environ.get("IMPALA_USER")
    password = os.environ.get("IMPALA_PASSWORD")
    if not all([host, user, password]):
        raise ValueError(
            "Set IMPALA_JDBC_URL or IMPALA_HOST + IMPALA_USER + IMPALA_PASSWORD"
        )
    return ImpalaSettings(
        host=host,
        port=int(os.environ.get("IMPALA_PORT", "443")),
        database=os.environ.get("IMPALA_DATABASE", "id_workshop"),
        user=user,
        password=password,
        use_ssl=os.environ.get("IMPALA_SSL", "1") == "1",
        http_path=os.environ.get("IMPALA_HTTP_PATH", "cliservice"),
    )
