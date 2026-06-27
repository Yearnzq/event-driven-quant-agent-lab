from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import Bar, PortfolioSnapshot
from quant_agent_lab.data.importers import write_bars_csv
from quant_agent_lab.data.metadata import build_dataset_manifest


BINANCE_MARKET_DATA_BASE_URL = "https://data-api.binance.vision"
BINANCE_INTERVALS = {"1h": "1h", "1d": "1d"}
PUBLIC_DATA_NETWORK_ENABLE_ENV = "QAL_ALLOW_PUBLIC_DATA_NETWORK"


def _project_symbol_to_binance(symbol: str) -> str:
    return symbol.replace("-", "").replace("/", "").upper()


def _utc_from_ms(value: int | str) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


def _ms_from_utc(value: datetime) -> int:
    utc = value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return int(utc.timestamp() * 1000)


def _read_json(url: str, *, timeout: float = 10.0, retries: int = 3) -> Any:
    request = Request(url, headers={"User-Agent": "quant-agent-lab/0.1"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - public data fetch is best-effort and retryable.
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"public data request failed after retries: {type(last_error).__name__}: redacted")


def fetch_binance_klines(
    *,
    symbol: str,
    timeframe: str,
    limit: int,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    base_url: str = BINANCE_MARKET_DATA_BASE_URL,
    allow_network: bool = False,
) -> list[Bar]:
    """Fetch public research OHLCV data.

    This connector is best-effort and public-data only. It is not broker,
    account, private API, paper-trading, or live-trading integration.
    """

    if not allow_network and os.environ.get(PUBLIC_DATA_NETWORK_ENABLE_ENV) != "1":
        raise RuntimeError("public data network access requires explicit allow_network")
    if timeframe not in BINANCE_INTERVALS:
        raise ValueError(f"unsupported Binance timeframe: {timeframe}")
    if limit < 1 or limit > 1000:
        raise ValueError("Binance kline limit must be between 1 and 1000")

    exchange_symbol = _project_symbol_to_binance(symbol)
    query_params: dict[str, str | int] = {
        "symbol": exchange_symbol,
        "interval": BINANCE_INTERVALS[timeframe],
        "limit": limit,
    }
    if start_at is not None:
        query_params["startTime"] = _ms_from_utc(start_at)
    if end_at is not None:
        query_params["endTime"] = _ms_from_utc(end_at)
    query = urlencode(query_params)
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


def fetch_binance_klines_range(
    *,
    symbol: str,
    timeframe: str,
    start_at: datetime,
    end_at: datetime,
    base_url: str = BINANCE_MARKET_DATA_BASE_URL,
    allow_network: bool = False,
) -> list[Bar]:
    """Fetch a closed UTC time range of public research OHLCV data."""

    if timeframe not in BINANCE_INTERVALS:
        raise ValueError(f"unsupported Binance timeframe: {timeframe}")
    start_utc = start_at.astimezone(timezone.utc) if start_at.tzinfo else start_at.replace(tzinfo=timezone.utc)
    end_utc = end_at.astimezone(timezone.utc) if end_at.tzinfo else end_at.replace(tzinfo=timezone.utc)
    if start_utc > end_utc:
        raise ValueError("start_at must be before or equal to end_at")

    step = timedelta(hours=1) if timeframe == "1h" else timedelta(days=1)
    cursor = start_utc
    by_timestamp: dict[datetime, Bar] = {}
    while cursor <= end_utc:
        page = fetch_binance_klines(
            symbol=symbol,
            timeframe=timeframe,
            limit=1000,
            start_at=cursor,
            end_at=end_utc,
            base_url=base_url,
            allow_network=allow_network,
        )
        if not page:
            break
        for bar in page:
            if start_utc <= bar.ts <= end_utc:
                by_timestamp[bar.ts] = bar
        next_cursor = page[-1].ts + step
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(page) < 1000:
            break

    return [by_timestamp[ts] for ts in sorted(by_timestamp)]


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
    allow_network: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    bars_1h = fetch_binance_klines(
        symbol=symbol,
        timeframe="1h",
        limit=hourly_limit,
        base_url=base_url,
        allow_network=allow_network,
    )
    bars_1d = fetch_binance_klines(
        symbol=symbol,
        timeframe="1d",
        limit=daily_limit,
        base_url=base_url,
        allow_network=allow_network,
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
    manifest = build_dataset_manifest(output_dir, symbol=symbol, as_of=as_of, source="binance")
    metadata = manifest.model_dump(mode="json")
    metadata["exchange"] = "binance"
    metadata["exchange_symbol"] = _project_symbol_to_binance(symbol)
    metadata["as_of"] = as_of.isoformat()
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_dir


def write_binance_historical_csv_dataset(
    output_dir: Path,
    *,
    symbol: str = "BTC-USDT",
    start_at: datetime,
    end_at: datetime,
    equity: float = 100_000.0,
    cash: float = 100_000.0,
    position_pct: float = 0.0,
    base_url: str = BINANCE_MARKET_DATA_BASE_URL,
    allow_network: bool = False,
) -> Path:
    """Write an explicitly authorized, frozen multi-year public OHLCV dataset.

    The resulting CSV files are intended to be reviewed and then reused offline.
    This is still public research data only; it is not broker, account,
    paper-trading, or live-trading integration.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    bars_1h = fetch_binance_klines_range(
        symbol=symbol,
        timeframe="1h",
        start_at=start_at,
        end_at=end_at,
        base_url=base_url,
        allow_network=allow_network,
    )
    bars_1d = fetch_binance_klines_range(
        symbol=symbol,
        timeframe="1d",
        start_at=start_at,
        end_at=end_at,
        base_url=base_url,
        allow_network=allow_network,
    )
    if not bars_1h or not bars_1d:
        raise ValueError("exchange returned empty historical kline data")

    as_of = min(bars_1h[-1].ts, bars_1d[-1].ts)
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
    manifest = build_dataset_manifest(
        output_dir,
        symbol=symbol,
        as_of=as_of,
        source="binance_frozen_historical",
        dataset_id=f"binance-frozen:{symbol}:{bars_1d[0].ts.date()}:{bars_1d[-1].ts.date()}",
    )
    metadata = manifest.model_dump(mode="json")
    metadata["dataset_kind"] = "frozen_historical_ohlcv"
    metadata["exchange"] = "binance"
    metadata["exchange_symbol"] = _project_symbol_to_binance(symbol)
    metadata["data_start"] = bars_1d[0].ts.date().isoformat()
    metadata["data_end"] = bars_1d[-1].ts.date().isoformat()
    metadata["bars_1h_count"] = len(bars_1h)
    metadata["bars_1d_count"] = len(bars_1d)
    metadata["frozen"] = True
    metadata["network_used_for_preparation"] = True
    metadata["as_of"] = as_of.isoformat()
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return output_dir
