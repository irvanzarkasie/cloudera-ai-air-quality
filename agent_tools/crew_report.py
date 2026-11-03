"""Extract full text from CrewAI kickoff results (avoid partial display on CDSW/SSH)."""

from __future__ import annotations

from typing import Any


def crew_result_text(result: Any) -> str:
    """Prefer the analysis task raw output, then crew-level raw."""
    if result is None:
        return ""
    tasks = getattr(result, "tasks_output", None) or []
    if tasks:
        last = tasks[-1]
        raw = getattr(last, "raw", None)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    raw = getattr(result, "raw", None)
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return str(result).strip()
