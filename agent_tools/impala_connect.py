"""Impala HS2 over HTTPS (CDP) with impyla on Python 3.12+."""

from __future__ import annotations

import http.client
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_tools.impala_config import ImpalaSettings


def _patch_https_for_py312() -> None:
    """impyla 0.19 passes key_file= to HTTPSConnection; removed in Python 3.12."""
    if getattr(http.client.HTTPSConnection, "_airaware_patched", False):
        return
    _orig = http.client.HTTPSConnection.__init__

    def _init(self, host, port=None, *args, **kwargs):
        kwargs.pop("key_file", None)
        kwargs.pop("cert_file", None)
        return _orig(self, host, port, *args, **kwargs)

    http.client.HTTPSConnection.__init__ = _init  # type: ignore[method-assign]
    http.client.HTTPSConnection._airaware_patched = True  # type: ignore[attr-defined]


def connect(settings: ImpalaSettings):
    _patch_https_for_py312()
    from impala.dbapi import connect as impala_connect

    use_http = settings.port == 443 or settings.use_ssl
    return impala_connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        use_ssl=settings.use_ssl,
        auth_mechanism=settings.auth_mechanism,
        use_http_transport=use_http,
        http_path=settings.http_path,
    )
