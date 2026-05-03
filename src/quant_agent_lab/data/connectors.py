from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import Bar, PortfolioSnapshot
from quant_agent_lab.data.importers import write_bars_csv


BINANCE_MARKET_DATA_BASE_URL = "https://data-api.binance.vision"
BINANCE_INTERVALS = {"1h": "1h", "1d": "1d"}


def _project_symbol_to_binance(symbol: str) -> str:
    return symbol.replace("-", "").replace("/", "").upper()


def _utc_from_ms(value: int | str) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _read_json(url: str, *, timeout: float = 10.0) -> Any:
    request = Request(url, headers={"User-Agent": "quant-agent-lab/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_binance_klines(
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    base_url: str = BINANCE_MARKET_DATA_BASE_URL,
) -> list[Bar]:
    if timeframe not in BINANCE_INTERVALS:
        raise ValueError(f"unsupported Binance timeframe: {timeframe}")
    if limit < 1 or limit > 1000:
        raise ValueError("Binance kline limit must be between 1 and 1000")

    exchange_symbol = _project_symbol_to_binance(symbol)
    query = urlencode(
        {
            "symbol": exchange_symbol,
            "interval": BINANCE_INTERVALS[timeframe],
            "limit": limit,
        }
    )
    url = f"{base_url.rstrip('/')}/api/v3/klines?{query}"
    rows = _read_json(url)
    bars: list[Bar] = []
    for row in rows:
        opened_at = _utc_from_ms(row[0])
        bars.append(
            Bar(
                symbol=symbol,
                timeframe=timeframe,  # type: ignore[arg-type]
                ts=opened_at,
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                source="binance",
                evidence_id=evidence_id("ohlcv", "binance", exchange_symbol, timeframe, opened_at.isoformat()),
            )
        )
    return bars


def write_binance_csv_dataset(
    output_dir: Path,
    *,
    symbol: str = "BTC-USDT",
    hourly_limit: int = 72,
    daily_limit: int = 45,
    equity: float = 100_000.0,
    cash: float = 100_000.0,
    position_pct: float = 0.0,
    base_url: str = BINANCE_MARKET_DATA_BASE_URL,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    bars_1h = fetch_binance_klines(
        symbol=symbol,
        timeframe="1h",
        limit=hourly_limit,
        base_url=base_url,
    )
    bars_1d = fetch_binance_klines(
        symbol=symbol,
        timeframe="1d",
        limit=daily_limit,
        base_url=base_url,
    )
    if not bars_1h or not bars_1d:
        raise ValueError("exchange returned empty kline data")

    as_of = bars_1h[-1].ts
    portfolio = PortfolioSnapshot(
        as_of=as_of,
        equity=equity,
        cash=cash,
        positions={symbol: position_pct},
        source="manual",
        evidence_id=evidence_id("portfolio", "manual", symbol, as_of.isoformat()),
    )

    write_bars_csv(output_dir / "bars_1h.csv", bars_1h)
    write_bars_csv(output_dir / "bars_1d.csv", bars_1d)
    (output_dir / "portfolio.json").write_text(
        json.dumps(portfolio.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "metadata.json").write_text(
        json.dumps(
            {
                "exchange": "binance",
                "symbol": symbol,
                "exchange_symbol": _project_symbol_to_binance(symbol),
                "as_of": as_of.isoformat(),
                "bars_1h_csv": "bars_1h.csv",
                "bars_1d_csv": "bars_1d.csv",
                "portfolio_json": "portfolio.json",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_dir
