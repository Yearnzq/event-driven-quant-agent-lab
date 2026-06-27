from __future__ import annotations

from statistics import mean, pstdev

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import MarketSnapshot, Signal, SignalBundle


def build_signal_bundle(snapshot: MarketSnapshot) -> SignalBundle:
    closes_1d = [bar.close for bar in snapshot.bars_1d]
    closes_1h = [bar.close for bar in snapshot.bars_1h]
    latest = closes_1h[-1]
    ma_fast = mean(closes_1d[-7:])
    ma_slow = mean(closes_1d[-30:])
    returns = [(b / a) - 1 for a, b in zip(closes_1h[-25:-1], closes_1h[-24:])]
    vol = pstdev(returns) if len(returns) > 1 else 0
    recent_high = max(closes_1h[-24:-1])

    trend_direction = "bullish" if ma_fast > ma_slow else "bearish" if ma_fast < ma_slow else "neutral"
    trend_strength = min(abs(ma_fast / ma_slow - 1) * 20, 1)
    vol_direction = "bearish" if vol > 0.025 else "neutral"
    breakout_direction = "bullish" if latest > recent_high else "neutral"

    ids = snapshot.evidence_ids
    signals = [
        Signal(
            signal_id=evidence_id("signal", snapshot.symbol, "trend", "v1", snapshot.as_of.isoformat()),
            symbol=snapshot.symbol,
            name="trend",
            direction=trend_direction,
            strength=round(trend_strength, 4),
            evidence_ids=ids,
            generated_at=snapshot.as_of,
            details={"ma_fast_7d": round(ma_fast, 2), "ma_slow_30d": round(ma_slow, 2)},
        ),
        Signal(
            signal_id=evidence_id("signal", snapshot.symbol, "volatility", "v1", snapshot.as_of.isoformat()),
            symbol=snapshot.symbol,
            name="volatility",
            direction=vol_direction,
            strength=round(min(vol / 0.04, 1), 4),
            evidence_ids=ids,
            generated_at=snapshot.as_of,
            details={"hourly_return_vol": round(vol, 6)},
        ),
        Signal(
            signal_id=evidence_id("signal", snapshot.symbol, "breakout", "v1", snapshot.as_of.isoformat()),
            symbol=snapshot.symbol,
            name="breakout",
            direction=breakout_direction,
            strength=0.7 if breakout_direction == "bullish" else 0.2,
            evidence_ids=ids,
            generated_at=snapshot.as_of,
            details={"latest_close": round(latest, 2), "prior_24h_high": round(recent_high, 2)},
        ),
    ]
    return SignalBundle(symbol=snapshot.symbol, as_of=snapshot.as_of, signals=signals)
