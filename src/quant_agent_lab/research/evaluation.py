from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from pydantic import BaseModel, ConfigDict, Field

from quant_agent_lab.core.events import run_id
from quant_agent_lab.core.schemas import Action, Bar
from quant_agent_lab.data.audit import (
    stable_hash,
    write_artifact_catalog,
    write_json,
    write_run_manifest,
)


ActionFn = Callable[[list[Bar], int], tuple[Action, dict[str, float | str]]]


@dataclass(frozen=True)
class SignalDefinition:
    name: str
    family: str
    min_bars: int
    action_fn: ActionFn
    parameters: dict[str, float | int | str]


class SignalEvaluationPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    ts: str
    action: Action
    close: float
    forward_return: float
    signal_return: float
    details: dict[str, float | str] = Field(default_factory=dict)
    fast_ma: float | None = None
    slow_ma: float | None = None


class SignalEvaluationSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    strategy_name: str
    signal_family: str = "trend"
    sample_count: int = Field(ge=0)
    directional_count: int = Field(ge=0)
    hit_rate: float = Field(ge=0, le=1)
    average_signal_return: float
    cumulative_signal_return: float
    max_drawdown: float = Field(ge=0)
    points: list[SignalEvaluationPoint]


class SignalComparisonRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    strategy_name: str
    signal_family: str
    sample_count: int = Field(ge=0)
    directional_count: int = Field(ge=0)
    hit_rate: float = Field(ge=0, le=1)
    average_signal_return: float
    cumulative_signal_return: float
    max_drawdown: float = Field(ge=0)
    research_score: float
    score_components: dict[str, float] = Field(default_factory=dict)
    deployable: bool = False
    order_allowed: bool = False


class SignalResearchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "phase4.signal_research.v1"
    symbol: str
    generated_at: datetime
    strategy_count: int = Field(ge=0)
    summaries: list[SignalEvaluationSummary]
    ranking: list[SignalComparisonRow]
    best_research_score_strategy: str | None
    disclaimer: str = "Offline signal research only. Not a trading instruction."
    deployable: bool = False
    order_allowed: bool = False
    human_required: bool = True


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


def _window_closes(bars: list[Bar], index: int, window: int) -> list[float]:
    return [bar.close for bar in bars[index - window + 1 : index + 1]]


def _ma_crossover_action(fast_window: int, slow_window: int) -> ActionFn:
    if fast_window < 1 or slow_window < 1 or fast_window >= slow_window:
        raise ValueError("MA windows must be positive and fast_window < slow_window")

    def decide(bars: list[Bar], index: int) -> tuple[Action, dict[str, float | str]]:
        fast_ma = mean(_window_closes(bars, index, fast_window))
        slow_ma = mean(_window_closes(bars, index, slow_window))
        if fast_ma > slow_ma:
            action = Action.BUY
        elif fast_ma < slow_ma:
            action = Action.SELL
        else:
            action = Action.HOLD
        return action, {"fast_ma": round(fast_ma, 8), "slow_ma": round(slow_ma, 8)}

    return decide


def _breakout_action(window: int) -> ActionFn:
    if window < 2:
        raise ValueError("breakout window must be at least 2")

    def decide(bars: list[Bar], index: int) -> tuple[Action, dict[str, float | str]]:
        history = bars[index - window + 1 : index]
        prior_high = max(bar.close for bar in history)
        prior_low = min(bar.close for bar in history)
        close = bars[index].close
        if close > prior_high:
            action = Action.BUY
        elif close < prior_low:
            action = Action.SELL
        else:
            action = Action.HOLD
        return action, {"prior_high": round(prior_high, 8), "prior_low": round(prior_low, 8)}

    return decide


def _volatility_regime_action(window: int, threshold: float) -> ActionFn:
    if window < 3:
        raise ValueError("volatility window must be at least 3")
    if threshold <= 0:
        raise ValueError("volatility threshold must be positive")

    def decide(bars: list[Bar], index: int) -> tuple[Action, dict[str, float | str]]:
        closes = _window_closes(bars, index, window)
        returns = [(right / left) - 1 for left, right in zip(closes, closes[1:])]
        volatility = pstdev(returns) if len(returns) > 1 else 0.0
        drift = closes[-1] / closes[0] - 1
        if volatility <= threshold and drift > 0:
            action = Action.BUY
        elif volatility > threshold * 1.5:
            action = Action.SELL
        else:
            action = Action.HOLD
        return action, {"volatility": round(volatility, 8), "drift": round(drift, 8)}

    return decide


def default_signal_registry(
    *,
    fast_window: int = 7,
    slow_window: int = 30,
    breakout_window: int = 20,
    volatility_window: int = 20,
    volatility_threshold: float = 0.03,
) -> list[SignalDefinition]:
    return [
        SignalDefinition(
            name=f"ma_crossover_{fast_window}_{slow_window}_h1",
            family="trend",
            min_bars=slow_window,
            action_fn=_ma_crossover_action(fast_window, slow_window),
            parameters={"fast_window": fast_window, "slow_window": slow_window},
        ),
        SignalDefinition(
            name=f"breakout_{breakout_window}_h1",
            family="breakout",
            min_bars=breakout_window,
            action_fn=_breakout_action(breakout_window),
            parameters={"breakout_window": breakout_window},
        ),
        SignalDefinition(
            name=f"volatility_regime_{volatility_window}_h1",
            family="volatility",
            min_bars=volatility_window,
            action_fn=_volatility_regime_action(volatility_window, volatility_threshold),
            parameters={
                "volatility_window": volatility_window,
                "volatility_threshold": volatility_threshold,
            },
        ),
    ]


def serialize_signal_registry(
    registry: list[SignalDefinition],
) -> list[dict[str, str | int | dict[str, float | int | str]]]:
    return [
        {
            "name": definition.name,
            "family": definition.family,
            "min_bars": definition.min_bars,
            "parameters": definition.parameters,
        }
        for definition in registry
    ]


def evaluate_signal_definition(
    bars: list[Bar],
    definition: SignalDefinition,
    *,
    horizon: int = 1,
) -> SignalEvaluationSummary:
    if horizon < 1:
        raise ValueError("horizon must be positive")
    ordered = sorted(bars, key=lambda item: item.ts)
    if len(ordered) <= definition.min_bars + horizon:
        raise ValueError(f"not enough bars for {definition.name} evaluation")

    symbol = ordered[-1].symbol
    points: list[SignalEvaluationPoint] = []
    for index in range(definition.min_bars - 1, len(ordered) - horizon):
        action, details = definition.action_fn(ordered, index)
        close = ordered[index].close
        forward_return = ordered[index + horizon].close / close - 1
        if action == Action.BUY:
            signal_return = forward_return
        elif action == Action.SELL:
            signal_return = -forward_return
        else:
            signal_return = 0.0

        point_details = {key: value for key, value in details.items()}
        points.append(
            SignalEvaluationPoint(
                symbol=ordered[index].symbol,
                ts=ordered[index].ts.isoformat(),
                action=action,
                close=round(close, 8),
                forward_return=round(forward_return, 8),
                signal_return=round(signal_return, 8),
                details=point_details,
                fast_ma=point_details.get("fast_ma") if isinstance(point_details.get("fast_ma"), float) else None,
                slow_ma=point_details.get("slow_ma") if isinstance(point_details.get("slow_ma"), float) else None,
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
        strategy_name=definition.name,
        signal_family=definition.family,
        sample_count=len(points),
        directional_count=len(directional),
        hit_rate=round(hits / len(directional), 4) if directional else 0.0,
        average_signal_return=round(mean(signal_returns), 8) if signal_returns else 0.0,
        cumulative_signal_return=round(cumulative - 1, 8),
        max_drawdown=round(_max_drawdown(signal_returns), 8),
        points=points,
    )


def evaluate_ma_crossover(
    bars: list[Bar],
    *,
    fast_window: int = 7,
    slow_window: int = 30,
    horizon: int = 1,
) -> SignalEvaluationSummary:
    definition = SignalDefinition(
        name=f"ma_crossover_{fast_window}_{slow_window}_h{horizon}",
        family="trend",
        min_bars=slow_window,
        action_fn=_ma_crossover_action(fast_window, slow_window),
        parameters={"fast_window": fast_window, "slow_window": slow_window, "horizon": horizon},
    )
    return evaluate_signal_definition(bars, definition, horizon=horizon)


def _normalized_scores(values: dict[str, float], *, higher_is_better: bool = True) -> dict[str, float]:
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    if high == low:
        return {key: 1.0 for key in values}
    if higher_is_better:
        return {key: round((value - low) / (high - low), 8) for key, value in values.items()}
    return {key: round((high - value) / (high - low), 8) for key, value in values.items()}


def _research_score_components(
    summaries: list[SignalEvaluationSummary],
) -> dict[str, dict[str, float]]:
    cumulative = {summary.strategy_name: summary.cumulative_signal_return for summary in summaries}
    average = {summary.strategy_name: summary.average_signal_return for summary in summaries}
    hit_rate = {summary.strategy_name: summary.hit_rate for summary in summaries}
    drawdown = {summary.strategy_name: summary.max_drawdown for summary in summaries}
    coverage = {
        summary.strategy_name: summary.directional_count / summary.sample_count
        if summary.sample_count
        else 0.0
        for summary in summaries
    }
    return {
        summary.strategy_name: {
            "cumulative_return_rank": _normalized_scores(cumulative)[summary.strategy_name],
            "average_return_rank": _normalized_scores(average)[summary.strategy_name],
            "hit_rate_rank": _normalized_scores(hit_rate)[summary.strategy_name],
            "drawdown_inverse_rank": _normalized_scores(drawdown, higher_is_better=False)[summary.strategy_name],
            "directional_coverage_rank": _normalized_scores(coverage)[summary.strategy_name],
        }
        for summary in summaries
    }


def _robust_research_score(components: dict[str, float]) -> float:
    return round(
        0.30 * components["cumulative_return_rank"]
        + 0.25 * components["average_return_rank"]
        + 0.20 * components["hit_rate_rank"]
        + 0.15 * components["drawdown_inverse_rank"]
        + 0.10 * components["directional_coverage_rank"],
        8,
    )


def build_signal_research_report(
    bars: list[Bar],
    *,
    registry: list[SignalDefinition] | None = None,
    horizon: int = 1,
) -> SignalResearchReport:
    registry = registry or default_signal_registry()
    summaries = [
        evaluate_signal_definition(bars, definition, horizon=horizon)
        for definition in registry
    ]
    score_components = _research_score_components(summaries)
    ranking = sorted(
        [
            SignalComparisonRow(
                strategy_name=summary.strategy_name,
                signal_family=summary.signal_family,
                sample_count=summary.sample_count,
                directional_count=summary.directional_count,
                hit_rate=summary.hit_rate,
                average_signal_return=summary.average_signal_return,
                cumulative_signal_return=summary.cumulative_signal_return,
                max_drawdown=summary.max_drawdown,
                research_score=_robust_research_score(score_components[summary.strategy_name]),
                score_components=score_components[summary.strategy_name],
            )
            for summary in summaries
        ],
        key=lambda row: (row.research_score, row.hit_rate, row.directional_count),
        reverse=True,
    )
    symbol = summaries[0].symbol if summaries else "UNKNOWN"
    generated_at = bars[-1].ts.astimezone(timezone.utc) if bars else datetime(1970, 1, 1, tzinfo=timezone.utc)
    return SignalResearchReport(
        symbol=symbol,
        generated_at=generated_at,
        strategy_count=len(summaries),
        summaries=summaries,
        ranking=ranking,
        best_research_score_strategy=ranking[0].strategy_name if ranking else None,
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
Family: `{summary.signal_family}`

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


def render_signal_research_markdown(report: SignalResearchReport) -> str:
    ranking_rows = "\n".join(
        "| {name} | `{family}` | {score:.4%} | {cum:.4%} | {hit:.2%} | {dd:.4%} |".format(
            name=row.strategy_name,
            family=row.signal_family,
            score=row.research_score,
            cum=row.cumulative_signal_return,
            hit=row.hit_rate,
            dd=row.max_drawdown,
        )
        for row in report.ranking
    )
    return f"""# Signal Research Report

Symbol: `{report.symbol}`
Schema: `{report.schema_version}`
Generated at: `{report.generated_at.isoformat()}`

## Ranking

Research score is a normalized robust score: cumulative return rank, average return rank,
hit-rate rank, drawdown inverse rank, and directional coverage rank. It is not a
deployability score.

| Strategy | Family | Research score | Cumulative signal return | Hit rate | Max drawdown |
| --- | --- | ---: | ---: | ---: | ---: |
{ranking_rows}

## Boundary

- Research-only: `true`
- Deployable: `{str(report.deployable).lower()}`
- Order allowed: `{str(report.order_allowed).lower()}`
- Human required: `{str(report.human_required).lower()}`

Note: {report.disclaimer}
"""


def write_signal_research_artifacts(
    output_dir: Path,
    *,
    bars: list[Bar],
    report: SignalResearchReport,
    registry: list[SignalDefinition],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    research_md = output_dir / "signal_research_report.md"
    research_json = output_dir / "signal_research_report.json"
    registry_json = output_dir / "signal-registry.json"
    research_md.write_text(render_signal_research_markdown(report), encoding="utf-8")
    write_json(research_json, report.model_dump(mode="json"))
    write_json(registry_json, serialize_signal_registry(registry))

    artifacts: list[tuple[str, Path]] = [
        ("research_markdown", research_md),
        ("research_json", research_json),
        ("registry_json", registry_json),
    ]
    for summary in report.summaries:
        summary_md = output_dir / f"{summary.strategy_name}.md"
        summary_json = output_dir / f"{summary.strategy_name}.json"
        summary_md.write_text(render_signal_evaluation_markdown(summary), encoding="utf-8")
        write_json(summary_json, summary.model_dump(mode="json"))
        artifacts.append((f"strategy_markdown:{summary.strategy_name}", summary_md))
        artifacts.append((f"strategy_json:{summary.strategy_name}", summary_json))

    catalog_path = write_artifact_catalog(
        output_dir,
        run_id=run_id("signal-research", report.generated_at),
        artifacts=artifacts,
        created_at=report.generated_at,
    )
    write_run_manifest(
        output_dir,
        run_id=run_id("signal-research", report.generated_at),
        symbol=report.symbol,
        as_of=report.generated_at,
        input_hash=stable_hash([bar.model_dump(mode="json") for bar in bars]),
        output_hash=stable_hash(report.model_dump(mode="json")),
        config_hash=stable_hash(serialize_signal_registry(registry)),
        validation_result="research_only",
        artifact_catalog_path=catalog_path,
        created_at=report.generated_at,
    )
    return output_dir
