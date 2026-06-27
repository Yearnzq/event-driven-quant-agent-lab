from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import Bar, MarketSnapshot, PortfolioSnapshot


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_bars_csv(path: Path, *, symbol: str, timeframe: str) -> list[Bar]:
    rows: list[Bar] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader):
            row_symbol = row.get("symbol") or symbol
            ts = _parse_dt(row["ts"])
            source = row.get("source") or "csv"
            rows.append(
                Bar(
                    symbol=row_symbol,
                    timeframe=timeframe,  # type: ignore[arg-type]
                    ts=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume") or 0),
                    source=source,
                    evidence_id=row.get("evidence_id")
                    or evidence_id("ohlcv", source, row_symbol, timeframe, ts.isoformat(), index),
                )
            )
    return rows


def load_portfolio_json(path: Path, *, as_of: datetime, symbol: str) -> PortfolioSnapshot:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    portfolio_as_of = _parse_dt(str(payload.get("as_of") or as_of.isoformat()))
    source = str(payload.get("source") or "json")
    evidence = str(payload.get("evidence_id") or evidence_id("portfolio", source, portfolio_as_of.isoformat()))
    positions = payload.get("positions") or {symbol: 0.0}
    return PortfolioSnapshot(
        as_of=portfolio_as_of,
        base_currency=str(payload.get("base_currency") or "USDT"),
        equity=float(payload["equity"]),
        cash=float(payload.get("cash") or 0),
        positions={str(k): float(v) for k, v in positions.items()},
        source=source,
        evidence_id=evidence,
    )


def load_csv_market_snapshot(
    *,
    symbol: str,
    as_of: datetime,
    bars_1h_csv: Path,
    bars_1d_csv: Path,
    portfolio_json: Path,
) -> MarketSnapshot:
    as_of_utc = as_of.astimezone(timezone.utc) if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
    return MarketSnapshot(
        symbol=symbol,
        as_of=as_of_utc,
        bars_1h=load_bars_csv(bars_1h_csv, symbol=symbol, timeframe="1h"),
        bars_1d=load_bars_csv(bars_1d_csv, symbol=symbol, timeframe="1d"),
        portfolio=load_portfolio_json(portfolio_json, as_of=as_of_utc, symbol=symbol),
    )
