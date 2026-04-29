from __future__ import annotations

from datetime import datetime


def evidence_id(*parts: object) -> str:
    return ":".join(str(part).lower().replace(" ", "-") for part in parts)


def run_id(symbol: str, as_of: datetime) -> str:
    stamp = as_of.strftime("%Y%m%dT%H%M%SZ")
    safe_symbol = str(symbol).lower().replace("/", "-").replace(":", "-")
    return f"run-{safe_symbol}-{stamp.lower()}"
