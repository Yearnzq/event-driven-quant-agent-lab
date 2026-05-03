from __future__ import annotations

from statistics import mean

from pydantic import BaseModel, ConfigDict, Field

from quant_agent_lab.core.schemas import Action, Bar


class SignalEvaluationPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    ts: str
    action: Action
    close: float
    forward_return: float
    signal_return: float
    fast_ma: float
    slow_ma: float


class SignalEvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    sample_count: int = Field(ge=0)
    directional_count: int = Field(ge=0)
    hit_rate: float = Field(ge=0, le=1)
    average_signal_return: float
    cumulative_signal_return: float
    max_drawdown: float = Field(ge=0)
    points: list[SignalEvaluationPoint]


def _max_drawdown(returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for value in returns:
        equity *= 1 + value
        peak = max(peak, equity)
        if peak:
            max_dd = max(max_dd, (peak - equity) / peak)
    return max_dd


def evaluate_ma_crossover(
    bars: list[Bar],
    *,
    fast_window: int = 7,
    slow_window: int = 30,
    horizon: int = 1,
) -> SignalEvaluationSummary:
    if fast_window < 1 or slow_window < 1 or horizon < 1:
        raise ValueError("windows and horizon must be positive")
    if fast_window >= slow_window:
        raise ValueError("fast_window must be smaller than slow_window")
    ordered = sorted(bars, key=lambda item: item.ts)
    if len(ordered) <= slow_window + horizon:
        raise ValueError("not enough bars for MA crossover evaluation")

    symbol = ordered[-1].symbol
    closes = [bar.close for bar in ordered]
    points: list[SignalEvaluationPoint] = []
    for index in range(slow_window - 1, len(ordered) - horizon):
        fast_ma = mean(closes[index - fast_window + 1 : index + 1])
        slow_ma = mean(closes[index - slow_window + 1 : index + 1])
        if fast_ma > slow_ma:
            action = Action.BUY
        elif fast_ma < slow_ma:
            action = Action.SELL
        else:
            action = Action.HOLD

        close = closes[index]
        forward_return = closes[index + horizon] / close - 1
        if action == Action.BUY:
            signal_return = forward_return
        elif action == Action.SELL:
            signal_return = -forward_return
        else:
            signal_return = 0.0

        points.append(
            SignalEvaluationPoint(
                symbol=ordered[index].symbol,
                ts=ordered[index].ts.isoformat(),
                action=action,
                close=round(close, 8),
                forward_return=round(forward_return, 8),
                signal_return=round(signal_return, 8),
                fast_ma=round(fast_ma, 8),
                slow_ma=round(slow_ma, 8),
            )
        )

    directional = [point for point in points if point.action in {Action.BUY, Action.SELL}]
    hits = sum(1 for point in directional if point.signal_return > 0)
    signal_returns = [point.signal_return for point in points]
    cumulative = 1.0
    for value in signal_returns:
        cumulative *= 1 + value

    return SignalEvaluationSummary(
        symbol=symbol,
        strategy_name=f"ma_crossover_{fast_window}_{slow_window}_h{horizon}",
        sample_count=len(points),
        directional_count=len(directional),
        hit_rate=round(hits / len(directional), 4) if directional else 0.0,
        average_signal_return=round(mean(signal_returns), 8) if signal_returns else 0.0,
        cumulative_signal_return=round(cumulative - 1, 8),
        max_drawdown=round(_max_drawdown(signal_returns), 8),
        points=points,
    )


def render_signal_evaluation_markdown(summary: SignalEvaluationSummary, *, max_points: int = 10) -> str:
    rows = "\n".join(
        "| {ts} | `{action}` | {forward:.4%} | {signal:.4%} |".format(
            ts=point.ts,
            action=point.action.value,
            forward=point.forward_return,
            signal=point.signal_return,
        )
        for point in summary.points[-max_points:]
    )
    return f"""# Signal Evaluation

Symbol: `{summary.symbol}`
Strategy: `{summary.strategy_name}`

## Summary

- Samples: `{summary.sample_count}`
- Directional samples: `{summary.directional_count}`
- Hit rate: `{summary.hit_rate:.2%}`
- Average signal return: `{summary.average_signal_return:.4%}`
- Cumulative signal return: `{summary.cumulative_signal_return:.4%}`
- Max drawdown: `{summary.max_drawdown:.4%}`

## Recent Points

| Timestamp | Action | Forward return | Signal return |
| --- | --- | --- | --- |
{rows}

Note: This is offline signal research only. It is not a trading instruction.
"""
