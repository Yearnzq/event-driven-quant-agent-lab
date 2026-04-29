from __future__ import annotations

from datetime import datetime, timedelta, timezone

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import Bar, MarketSnapshot, PortfolioSnapshot


def _bar(symbol: str, timeframe: str, ts: datetime, index: int, base: float) -> Bar:
    drift = index * (18 if timeframe == "1h" else 95)
    wave = ((index % 7) - 3) * (6 if timeframe == "1h" else 24)
    open_ = base + drift + wave
    close = open_ + (9 if index % 3 else -5)
    high = max(open_, close) + 22
    low = min(open_, close) - 18
    return Bar(
        symbol=symbol,
        timeframe=timeframe,  # type: ignore[arg-type]
        ts=ts,
        open=round(open_, 2),
        high=round(high, 2),
        low=round(low, 2),
        close=round(close, 2),
        volume=round(1200 + index * 17.5, 2),
        evidence_id=evidence_id("ohlcv", "mock", symbol, timeframe, ts.isoformat()),
    )


def load_mock_market_snapshot(
    symbol: str = "BTC-USDT",
    as_of: datetime | None = None,
    bars_1h_count: int = 72,
    bars_1d_count: int = 45,
) -> MarketSnapshot:
    as_of = as_of or datetime(2026, 4, 29, 0, 0, tzinfo=timezone.utc)
    bars_1h = [
        _bar(symbol, "1h", as_of - timedelta(hours=bars_1h_count - index), index, 64000)
        for index in range(bars_1h_count)
    ]
    bars_1d = [
        _bar(symbol, "1d", as_of - timedelta(days=bars_1d_count - index), index, 61000)
        for index in range(bars_1d_count)
    ]
    portfolio = PortfolioSnapshot(
        as_of=as_of,
        equity=100_000,
        cash=82_500,
        positions={symbol: 0.175},
        evidence_id=evidence_id("portfolio", "mock", as_of.isoformat()),
    )
    return MarketSnapshot(
        symbol=symbol,
        as_of=as_of,
        bars_1h=bars_1h,
        bars_1d=bars_1d,
        portfolio=portfolio,
    )
