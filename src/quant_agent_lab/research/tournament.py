from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import pi, sin, sqrt
from pathlib import Path
from statistics import mean, pstdev
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import Bar
from quant_agent_lab.data.audit import file_sha256, stable_hash, write_artifact_catalog, write_json


StyleName = Literal[
    "trend_following",
    "breakout",
    "mean_reversion",
    "volatility_regime",
    "defensive_vol_target",
    "momentum",
]


class CostModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: Literal["low_cost", "medium_cost", "high_cost"]
    fee_bps: float = Field(ge=0)
    slippage_bps: float = Field(ge=0)


class WalkForwardSplit(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    test_locked: bool = True
    shuffle: bool = False
    purge_lag_bars: int = 1


class StrategyStyleSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    style_name: StyleName
    version: str = "phase10.strategy_style.v1"
    family: str
    parameters: dict[str, float | int | str]
    research_only: bool = True
    deployable: bool = False
    order_allowed: bool = False

    @model_validator(mode="after")
    def research_boundary(self) -> "StrategyStyleSpec":
        if not self.research_only:
            raise ValueError("Phase 10 strategy styles must be research-only")
        if self.deployable:
            raise ValueError("Phase 10 strategy styles cannot be deployable")
        if self.order_allowed:
            raise ValueError("Phase 10 strategy styles cannot allow orders")
        return self


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    scored_return_count: int = Field(ge=0)
    first_scored_at: str | None = None
    last_scored_at: str | None = None
    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    drawdown_duration: int = Field(ge=0)
    cvar_95: float
    turnover: float
    trade_count: int = Field(ge=0)
    fee_paid: float = Field(ge=0)
    slippage_cost: float = Field(ge=0)
    win_rate: float = Field(ge=0, le=1)
    profit_factor: float
    out_of_sample_return: float
    out_of_sample_sharpe: float
    parameter_stability: float = Field(ge=0, le=1)


class WalkForwardStyleResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    split_name: str
    style_name: StyleName
    train: BacktestMetrics
    validation: BacktestMetrics
    test: BacktestMetrics


class StyleRankingRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    style_name: StyleName
    robust_score: float = Field(ge=0, le=1)
    total_return: float
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    calmar: float
    max_drawdown: float
    drawdown_duration: int
    cvar_95: float
    turnover: float
    trade_count: int
    fee_paid: float
    slippage_cost: float
    win_rate: float
    profit_factor: float
    out_of_sample_return: float
    out_of_sample_sharpe: float
    parameter_stability: float
    cost_sensitive: bool
    deployability: Literal["not_recommended"] = "not_recommended"
    score_components: dict[str, float] = Field(default_factory=dict)


class CostSensitivityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    style_name: StyleName
    cost_model: CostModel
    average_oos_return: float
    average_oos_sharpe: float
    average_max_drawdown: float
    cost_sensitive: bool
    deployability: Literal["not_recommended"] = "not_recommended"


class StressTestResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    scenario: str
    style_name: StyleName
    average_oos_return: float
    average_oos_sharpe: float
    average_max_drawdown: float
    passed: bool
    notes: list[str] = Field(default_factory=list)


class AIBlindPreferenceCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    ai_preferred_style_before_test: StyleName
    reason: list[str]
    actual_best_oos_style_by_robust_score: StyleName
    ai_preferred_style_rank_oos: int = Field(ge=1)
    match: bool
    data_visible_to_ai: Literal["train_validation_only"] = "train_validation_only"
    test_period_locked_before_preference: bool = True


class StrategyStyleTournamentReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase10.strategy_style_tournament.v1"] = "phase10.strategy_style_tournament.v1"
    phase: Literal[10] = 10
    simulation_type: Literal["offline_walk_forward_strategy_style_tournament"] = (
        "offline_walk_forward_strategy_style_tournament"
    )
    generated_at: datetime
    human_intervention_during_run: bool = False
    symbol: str
    data_start: str
    data_end: str
    styles_tested: list[StyleName]
    ranking: list[StyleRankingRow]
    best_total_return_style: StyleName
    best_risk_adjusted_style: StyleName
    lowest_drawdown_style: StyleName
    most_stable_oos_style: StyleName
    recommended_next_research_style: StyleName
    ai_blind_preference_check: AIBlindPreferenceCheck
    reason_not_deployable: list[str]
    research_only: bool = True
    deployable: bool = False
    order_allowed: bool = False
    human_required: bool = True

    @model_validator(mode="after")
    def advisory_boundary(self) -> "StrategyStyleTournamentReport":
        if self.human_intervention_during_run:
            raise ValueError("Phase 10 run must not have human intervention during simulation")
        if not self.research_only:
            raise ValueError("Phase 10 tournament must be research-only")
        if self.deployable:
            raise ValueError("Phase 10 tournament cannot be deployable")
        if self.order_allowed:
            raise ValueError("Phase 10 tournament cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 10 tournament must require human review")
        return self


class SimulationManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase10.simulation_manifest.v1"] = "phase10.simulation_manifest.v1"
    phase: Literal[10] = 10
    simulation_type: Literal["offline_walk_forward_strategy_style_tournament"] = (
        "offline_walk_forward_strategy_style_tournament"
    )
    generated_at: datetime
    symbol: str
    data_start: str
    data_end: str
    data_hash: str
    strategy_registry_hash: str
    risk_config_hash: str
    walk_forward_split_hash: str
    cost_model_hash: str
    artifacts: dict[str, str]
    artifact_hashes: dict[str, str]
    human_intervention_during_run: bool = False
    deployable: bool = False
    order_allowed: bool = False
    human_required: bool = True


@dataclass(frozen=True)
class StrategyStyleDefinition:
    spec: StrategyStyleSpec
    min_bars: int


def default_cost_models() -> list[CostModel]:
    return [
        CostModel(name="low_cost", fee_bps=5, slippage_bps=2),
        CostModel(name="medium_cost", fee_bps=10, slippage_bps=5),
        CostModel(name="high_cost", fee_bps=20, slippage_bps=10),
    ]


def default_walk_forward_splits() -> list[WalkForwardSplit]:
    return [
        WalkForwardSplit(
            name="window_1",
            train_start="2020-01-01",
            train_end="2021-12-31",
            validation_start="2022-01-01",
            validation_end="2022-06-30",
            test_start="2022-07-01",
            test_end="2022-12-31",
        ),
        WalkForwardSplit(
            name="window_2",
            train_start="2021-01-01",
            train_end="2022-12-31",
            validation_start="2023-01-01",
            validation_end="2023-06-30",
            test_start="2023-07-01",
            test_end="2023-12-31",
        ),
        WalkForwardSplit(
            name="window_3",
            train_start="2022-01-01",
            train_end="2023-12-31",
            validation_start="2024-01-01",
            validation_end="2024-06-30",
            test_start="2024-07-01",
            test_end="2024-12-31",
        ),
        WalkForwardSplit(
            name="window_4",
            train_start="2023-01-01",
            train_end="2024-12-31",
            validation_start="2025-01-01",
            validation_end="2025-06-30",
            test_start="2025-07-01",
            test_end="2025-12-31",
        ),
    ]


def default_strategy_style_registry() -> list[StrategyStyleDefinition]:
    return [
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="trend_following",
                family="trend",
                parameters={"fast_window": 30, "slow_window": 120},
            ),
            min_bars=120,
        ),
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="breakout",
                family="breakout",
                parameters={"breakout_window": 55},
            ),
            min_bars=55,
        ),
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="mean_reversion",
                family="mean_reversion",
                parameters={"lookback_window": 20, "entry_threshold": 0.035},
            ),
            min_bars=20,
        ),
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="volatility_regime",
                family="volatility",
                parameters={"lookback_window": 30, "max_volatility": 0.035},
            ),
            min_bars=30,
        ),
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="defensive_vol_target",
                family="defensive",
                parameters={"fast_window": 20, "slow_window": 100, "target_daily_vol": 0.014},
            ),
            min_bars=100,
        ),
        StrategyStyleDefinition(
            spec=StrategyStyleSpec(
                style_name="momentum",
                family="momentum",
                parameters={"lookback_window": 45, "activation_threshold": 0.02},
            ),
            min_bars=45,
        ),
    ]


def generate_phase10_daily_bars(symbol: str = "BTC-USDT") -> list[Bar]:
    bars: list[Bar] = []
    current = datetime(2020, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, tzinfo=timezone.utc)
    close = 7200.0
    index = 0
    while current <= end:
        year = current.year
        if year == 2020:
            drift = 0.0018
        elif year == 2021:
            drift = 0.0012
        elif year == 2022:
            drift = -0.0014
        elif year == 2023:
            drift = 0.0009
        elif year == 2024:
            drift = 0.0014
        else:
            drift = 0.0003
        cycle = 0.012 * sin(index / 17.0) + 0.006 * sin(index / 5.0)
        shock = -0.075 if index in {790, 1040, 1550} else 0.0
        daily_return = drift + cycle + shock
        open_price = close
        close = max(1000.0, close * (1 + daily_return))
        high = max(open_price, close) * (1 + 0.006 + abs(cycle) * 0.2)
        low = min(open_price, close) * (1 - 0.006 - abs(cycle) * 0.2)
        volume = 8000 + 1200 * abs(sin(index / 11.0)) + (3000 if abs(daily_return) > 0.04 else 0)
        bars.append(
            Bar(
                symbol=symbol,
                timeframe="1d",
                ts=current,
                open=round(open_price, 8),
                high=round(high, 8),
                low=round(low, 8),
                close=round(close, 8),
                volume=round(volume, 8),
                source="phase10_deterministic_sample",
                evidence_id=evidence_id("phase10", symbol, "1d", current.date().isoformat()),
            )
        )
        current += timedelta(days=1)
        index += 1
    return bars


def generate_phase10_hourly_adapter_sample(symbol: str = "BTC-USDT") -> list[Bar]:
    bars: list[Bar] = []
    current = datetime(2025, 12, 30, tzinfo=timezone.utc)
    close = 56000.0
    for index in range(48):
        ts = current + timedelta(hours=index)
        hourly_return = 0.0002 + 0.004 * sin(index / 4.0)
        open_price = close
        close = max(1000.0, close * (1 + hourly_return))
        bars.append(
            Bar(
                symbol=symbol,
                timeframe="1h",
                ts=ts,
                open=round(open_price, 8),
                high=round(max(open_price, close) * 1.002, 8),
                low=round(min(open_price, close) * 0.998, 8),
                close=round(close, 8),
                volume=round(300 + 25 * abs(sin(index)), 8),
                source="phase10_adapter_sample",
                evidence_id=evidence_id("phase10", symbol, "1h", ts.isoformat()),
            )
        )
    return bars


def _parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _slice_bars(bars: list[Bar], start: str, end: str, *, warmup_bars: int = 130) -> list[Bar]:
    start_dt = _parse_date(start)
    end_dt = _parse_date(end) + timedelta(hours=23, minutes=59, seconds=59)
    ordered = sorted(bars, key=lambda item: item.ts)
    start_index = next(index for index, bar in enumerate(ordered) if bar.ts >= start_dt)
    warmup_index = max(0, start_index - warmup_bars)
    return [bar for bar in ordered[warmup_index:] if bar.ts <= end_dt]


def _daily_returns(closes: list[float]) -> list[float]:
    return [right / left - 1 for left, right in zip(closes, closes[1:]) if left > 0]


def _window(values: list[float], index: int, length: int) -> list[float]:
    return values[index - length + 1 : index + 1]


def _position_for_style(
    definition: StrategyStyleDefinition,
    bars: list[Bar],
    index: int,
    *,
    parameter_scale: float = 1.0,
) -> float:
    closes = [bar.close for bar in bars]
    style = definition.spec.style_name
    params = definition.spec.parameters
    if style == "trend_following":
        fast = max(2, int(params["fast_window"] * parameter_scale))
        slow = max(fast + 1, int(params["slow_window"] * parameter_scale))
        fast_ma = mean(_window(closes, index, fast))
        slow_ma = mean(_window(closes, index, slow))
        return 1.0 if fast_ma > slow_ma else -0.35 if fast_ma < slow_ma * 0.985 else 0.0
    if style == "breakout":
        length = max(5, int(params["breakout_window"] * parameter_scale))
        history = closes[index - length : index]
        if closes[index] > max(history):
            return 1.0
        if closes[index] < min(history):
            return -0.5
        return 0.0
    if style == "mean_reversion":
        length = max(5, int(params["lookback_window"] * parameter_scale))
        threshold = float(params["entry_threshold"])
        avg = mean(_window(closes, index, length))
        deviation = closes[index] / avg - 1
        if deviation < -threshold:
            return 0.7
        if deviation > threshold:
            return -0.4
        return 0.0
    if style == "volatility_regime":
        length = max(5, int(params["lookback_window"] * parameter_scale))
        returns = _daily_returns(_window(closes, index, length))
        vol = pstdev(returns) if len(returns) > 1 else 0.0
        drift = closes[index] / closes[index - length + 1] - 1
        max_vol = float(params["max_volatility"]) * parameter_scale
        if vol <= max_vol and drift > 0:
            return 0.8
        if vol > max_vol * 1.5:
            return -0.3
        return 0.0
    if style == "defensive_vol_target":
        fast = max(2, int(params["fast_window"] * parameter_scale))
        slow = max(fast + 1, int(params["slow_window"] * parameter_scale))
        returns = _daily_returns(_window(closes, index, fast))
        vol = pstdev(returns) if len(returns) > 1 else 0.0
        trend_ok = mean(_window(closes, index, fast)) > mean(_window(closes, index, slow))
        if not trend_ok:
            return 0.0
        target = float(params["target_daily_vol"])
        return round(min(0.75, target / max(vol, 0.004)), 4)
    if style == "momentum":
        length = max(5, int(params["lookback_window"] * parameter_scale))
        momentum = closes[index] / closes[index - length] - 1
        threshold = float(params["activation_threshold"])
        if momentum > threshold:
            return 0.9
        if momentum < -threshold:
            return -0.45
        return 0.0
    raise ValueError(f"unsupported style: {style}")


def _max_drawdown_and_duration(returns: list[float]) -> tuple[float, int]:
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    duration = 0
    max_duration = 0
    for value in returns:
        equity *= 1 + value
        if equity >= peak:
            peak = equity
            duration = 0
        else:
            duration += 1
            max_duration = max(max_duration, duration)
            max_drawdown = max(max_drawdown, (peak - equity) / peak)
    return max_drawdown, max_duration


def _metrics(
    returns: list[float],
    *,
    turnover: float,
    trade_count: int,
    fee_paid: float,
    slippage_cost: float,
    scored_at: list[datetime] | None = None,
    parameter_stability: float = 1.0,
) -> BacktestMetrics:
    scored_at = scored_at or []
    scored_return_count = len(returns)
    if not returns:
        returns = [0.0]
    cumulative = 1.0
    for value in returns:
        cumulative *= 1 + value
    total_return = cumulative - 1
    years = max(len(returns) / 365.0, 1 / 365.0)
    cagr = cumulative ** (1 / years) - 1 if cumulative > 0 else -1.0
    vol = pstdev(returns) * sqrt(252) if len(returns) > 1 else 0.0
    avg = mean(returns)
    stdev = pstdev(returns) if len(returns) > 1 else 0.0
    downside = [value for value in returns if value < 0]
    downside_stdev = pstdev(downside) if len(downside) > 1 else 0.0
    sharpe = (avg / stdev) * sqrt(252) if stdev else 0.0
    sortino = (avg / downside_stdev) * sqrt(252) if downside_stdev else 0.0
    max_dd, dd_duration = _max_drawdown_and_duration(returns)
    calmar = cagr / max_dd if max_dd else 0.0
    ordered = sorted(returns)
    cutoff = max(1, int(len(ordered) * 0.05))
    cvar = mean(ordered[:cutoff])
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    profit_factor = sum(wins) / abs(sum(losses)) if losses else 0.0
    nonzero = len(wins) + len(losses)
    return BacktestMetrics(
        scored_return_count=scored_return_count,
        first_scored_at=scored_at[0].date().isoformat() if scored_at else None,
        last_scored_at=scored_at[-1].date().isoformat() if scored_at else None,
        total_return=round(total_return, 8),
        cagr=round(cagr, 8),
        volatility=round(vol, 8),
        sharpe=round(sharpe, 8),
        sortino=round(sortino, 8),
        calmar=round(calmar, 8),
        max_drawdown=round(max_dd, 8),
        drawdown_duration=dd_duration,
        cvar_95=round(cvar, 8),
        turnover=round(turnover, 8),
        trade_count=trade_count,
        fee_paid=round(fee_paid, 8),
        slippage_cost=round(slippage_cost, 8),
        win_rate=round(len(wins) / nonzero, 8) if nonzero else 0.0,
        profit_factor=round(profit_factor, 8),
        out_of_sample_return=round(total_return, 8),
        out_of_sample_sharpe=round(sharpe, 8),
        parameter_stability=round(parameter_stability, 8),
    )


def run_style_backtest(
    bars: list[Bar],
    definition: StrategyStyleDefinition,
    *,
    cost_model: CostModel,
    parameter_scale: float = 1.0,
    execution_delay_bars: int = 1,
    missing_fragment: bool = False,
    shock_multiplier: float = 1.0,
    score_start: str | None = None,
    score_end: str | None = None,
) -> BacktestMetrics:
    ordered = sorted(bars, key=lambda item: item.ts)
    if missing_fragment and len(ordered) > 80:
        start = len(ordered) // 2
        ordered = ordered[:start] + ordered[start + 5 :]
    scaled_min_bars = max(definition.min_bars, int(definition.min_bars * parameter_scale) + 2)
    if len(ordered) <= scaled_min_bars + execution_delay_bars + 2:
        return _metrics([], turnover=0, trade_count=0, fee_paid=0, slippage_cost=0)
    score_start_dt = _parse_date(score_start) if score_start else None
    score_end_dt = _parse_date(score_end) + timedelta(hours=23, minutes=59, seconds=59) if score_end else None

    desired_positions: list[float] = []
    returns: list[float] = []
    scored_at: list[datetime] = []
    previous_scored_position = 0.0
    turnover = 0.0
    trade_count = 0
    fee_paid = 0.0
    slippage_cost = 0.0
    start_index = scaled_min_bars
    for index in range(start_index, len(ordered) - 1):
        desired_positions.append(
            _position_for_style(definition, ordered, index, parameter_scale=parameter_scale)
        )
        delayed_index = len(desired_positions) - 1 - execution_delay_bars
        position = desired_positions[delayed_index] if delayed_index >= 0 else 0.0
        raw_return = ordered[index + 1].close / ordered[index].close - 1
        period_start = ordered[index].ts
        in_scoring_window = True
        if score_start_dt is not None and period_start < score_start_dt:
            in_scoring_window = False
        if score_end_dt is not None and period_start > score_end_dt:
            in_scoring_window = False
        if in_scoring_window:
            delta = abs(position - previous_scored_position)
            fee = delta * cost_model.fee_bps / 10000
            slippage = delta * cost_model.slippage_bps / 10000
            if delta > 1e-9:
                trade_count += 1
            turnover += delta
            fee_paid += fee
            slippage_cost += slippage
            returns.append(position * raw_return * shock_multiplier - fee - slippage)
            scored_at.append(period_start)
            previous_scored_position = position

    if parameter_scale == 1.0:
        parameter_stability = 1.0
    else:
        parameter_stability = max(0.0, 1.0 - abs(parameter_scale - 1.0) * 2)
    return _metrics(
        returns,
        turnover=turnover,
        trade_count=trade_count,
        fee_paid=fee_paid,
        slippage_cost=slippage_cost,
        scored_at=scored_at,
        parameter_stability=parameter_stability,
    )


def _average_metric(metrics: list[BacktestMetrics], attr: str) -> float:
    return round(mean(float(getattr(metric, attr)) for metric in metrics), 8) if metrics else 0.0


def _normalized(values: dict[str, float], *, higher: bool = True) -> dict[str, float]:
    low = min(values.values())
    high = max(values.values())
    if high == low:
        return {key: 1.0 for key in values}
    if higher:
        return {key: round((value - low) / (high - low), 8) for key, value in values.items()}
    return {key: round((high - value) / (high - low), 8) for key, value in values.items()}


def _aggregate_style_metrics(results: list[WalkForwardStyleResult]) -> dict[str, BacktestMetrics]:
    by_style: dict[str, list[BacktestMetrics]] = {}
    for result in results:
        by_style.setdefault(result.style_name, []).append(result.test)
    aggregate: dict[str, BacktestMetrics] = {}
    for style, metrics in by_style.items():
        aggregate[style] = BacktestMetrics(
            scored_return_count=int(round(_average_metric(metrics, "scored_return_count"))),
            first_scored_at=min(
                (metric.first_scored_at for metric in metrics if metric.first_scored_at),
                default=None,
            ),
            last_scored_at=max(
                (metric.last_scored_at for metric in metrics if metric.last_scored_at),
                default=None,
            ),
            total_return=_average_metric(metrics, "total_return"),
            cagr=_average_metric(metrics, "cagr"),
            volatility=_average_metric(metrics, "volatility"),
            sharpe=_average_metric(metrics, "sharpe"),
            sortino=_average_metric(metrics, "sortino"),
            calmar=_average_metric(metrics, "calmar"),
            max_drawdown=_average_metric(metrics, "max_drawdown"),
            drawdown_duration=int(round(_average_metric(metrics, "drawdown_duration"))),
            cvar_95=_average_metric(metrics, "cvar_95"),
            turnover=_average_metric(metrics, "turnover"),
            trade_count=int(round(_average_metric(metrics, "trade_count"))),
            fee_paid=_average_metric(metrics, "fee_paid"),
            slippage_cost=_average_metric(metrics, "slippage_cost"),
            win_rate=_average_metric(metrics, "win_rate"),
            profit_factor=_average_metric(metrics, "profit_factor"),
            out_of_sample_return=_average_metric(metrics, "out_of_sample_return"),
            out_of_sample_sharpe=_average_metric(metrics, "out_of_sample_sharpe"),
            parameter_stability=_average_metric(metrics, "parameter_stability"),
        )
    return aggregate


def _build_cost_sensitivity(
    bars: list[Bar],
    registry: list[StrategyStyleDefinition],
    splits: list[WalkForwardSplit],
    cost_models: list[CostModel],
) -> list[CostSensitivityResult]:
    rows: list[CostSensitivityResult] = []
    low_returns: dict[str, float] = {}
    high_returns: dict[str, float] = {}
    for definition in registry:
        for cost_model in cost_models:
            metrics = [
                run_style_backtest(
                    _slice_bars(bars, split.test_start, split.test_end),
                    definition,
                    cost_model=cost_model,
                    score_start=split.test_start,
                    score_end=split.test_end,
                )
                for split in splits
            ]
            average_return = _average_metric(metrics, "out_of_sample_return")
            if cost_model.name == "low_cost":
                low_returns[definition.spec.style_name] = average_return
            if cost_model.name == "high_cost":
                high_returns[definition.spec.style_name] = average_return
            rows.append(
                CostSensitivityResult(
                    style_name=definition.spec.style_name,
                    cost_model=cost_model,
                    average_oos_return=average_return,
                    average_oos_sharpe=_average_metric(metrics, "out_of_sample_sharpe"),
                    average_max_drawdown=_average_metric(metrics, "max_drawdown"),
                    cost_sensitive=False,
                )
            )
    sensitive = {
        style
        for style, low_value in low_returns.items()
        if low_value > 0 and high_returns.get(style, 0.0) <= low_value * 0.5
    }
    return [
        row.model_copy(update={"cost_sensitive": row.style_name in sensitive})
        for row in rows
    ]


def _build_stress_tests(
    bars: list[Bar],
    registry: list[StrategyStyleDefinition],
    splits: list[WalkForwardSplit],
    cost_model: CostModel,
) -> list[StressTestResult]:
    scenarios = {
        "cost_up": {"cost_model": CostModel(name="high_cost", fee_bps=20, slippage_bps=10)},
        "random_slippage_perturbation": {"cost_model": CostModel(name="high_cost", fee_bps=10, slippage_bps=12)},
        "missing_data_fragment": {"missing_fragment": True},
        "extreme_volatility": {"shock_multiplier": 1.6},
        "single_day_crash_shock": {"shock_multiplier": 1.35},
        "one_bar_execution_delay": {"execution_delay_bars": 2},
        "signal_lag": {"execution_delay_bars": 3},
        "parameter_perturbation": {"parameter_scale": 1.08},
    }
    rows: list[StressTestResult] = []
    for scenario, options in scenarios.items():
        for definition in registry:
            metrics = [
                run_style_backtest(
                    _slice_bars(bars, split.test_start, split.test_end),
                    definition,
                    cost_model=options.get("cost_model", cost_model),
                    parameter_scale=float(options.get("parameter_scale", 1.0)),
                    execution_delay_bars=int(options.get("execution_delay_bars", 1)),
                    missing_fragment=bool(options.get("missing_fragment", False)),
                    shock_multiplier=float(options.get("shock_multiplier", 1.0)),
                    score_start=split.test_start,
                    score_end=split.test_end,
                )
                for split in splits
            ]
            avg_return = _average_metric(metrics, "out_of_sample_return")
            avg_drawdown = _average_metric(metrics, "max_drawdown")
            rows.append(
                StressTestResult(
                    scenario=scenario,
                    style_name=definition.spec.style_name,
                    average_oos_return=avg_return,
                    average_oos_sharpe=_average_metric(metrics, "out_of_sample_sharpe"),
                    average_max_drawdown=avg_drawdown,
                    passed=avg_drawdown <= 0.35,
                    notes=[] if avg_drawdown <= 0.35 else ["drawdown exceeded Phase 10 stress threshold"],
                )
            )
    return rows


def _build_ranking(
    aggregate: dict[str, BacktestMetrics],
    cost_sensitivity: list[CostSensitivityResult],
) -> list[StyleRankingRow]:
    cagr = {style: metric.cagr for style, metric in aggregate.items()}
    sharpe = {style: metric.sharpe for style, metric in aggregate.items()}
    calmar = {style: metric.calmar for style, metric in aggregate.items()}
    drawdown = {style: metric.max_drawdown for style, metric in aggregate.items()}
    downside = {style: abs(metric.cvar_95) for style, metric in aggregate.items()}
    stability = {style: metric.parameter_stability for style, metric in aggregate.items()}
    turnover = {style: metric.turnover + metric.fee_paid + metric.slippage_cost for style, metric in aggregate.items()}
    cost_sensitive_styles = {row.style_name for row in cost_sensitivity if row.cost_sensitive}
    components = {
        style: {
            "cagr_rank": _normalized(cagr)[style],
            "sharpe_rank": _normalized(sharpe)[style],
            "calmar_rank": _normalized(calmar)[style],
            "max_drawdown_inverse_rank": _normalized(drawdown, higher=False)[style],
            "downside_volatility_inverse_rank": _normalized(downside, higher=False)[style],
            "stability_rank": _normalized(stability)[style],
            "turnover_cost_inverse_rank": _normalized(turnover, higher=False)[style],
        }
        for style in aggregate
    }
    rows: list[StyleRankingRow] = []
    for style, metric in aggregate.items():
        score_parts = components[style]
        robust_score = round(
            0.20 * score_parts["cagr_rank"]
            + 0.20 * score_parts["sharpe_rank"]
            + 0.20 * score_parts["calmar_rank"]
            + 0.15 * score_parts["max_drawdown_inverse_rank"]
            + 0.10 * score_parts["downside_volatility_inverse_rank"]
            + 0.10 * score_parts["stability_rank"]
            + 0.05 * score_parts["turnover_cost_inverse_rank"],
            8,
        )
        rows.append(
            StyleRankingRow(
                style_name=style,  # type: ignore[arg-type]
                robust_score=robust_score,
                total_return=metric.total_return,
                cagr=metric.cagr,
                volatility=metric.volatility,
                sharpe=metric.sharpe,
                sortino=metric.sortino,
                calmar=metric.calmar,
                max_drawdown=metric.max_drawdown,
                drawdown_duration=metric.drawdown_duration,
                cvar_95=metric.cvar_95,
                turnover=metric.turnover,
                trade_count=metric.trade_count,
                fee_paid=metric.fee_paid,
                slippage_cost=metric.slippage_cost,
                win_rate=metric.win_rate,
                profit_factor=metric.profit_factor,
                out_of_sample_return=metric.out_of_sample_return,
                out_of_sample_sharpe=metric.out_of_sample_sharpe,
                parameter_stability=metric.parameter_stability,
                cost_sensitive=style in cost_sensitive_styles,
                score_components=score_parts,
            )
        )
    return sorted(rows, key=lambda row: row.robust_score, reverse=True)


def _blind_preference(
    walk_forward: list[WalkForwardStyleResult],
    ranking: list[StyleRankingRow],
) -> AIBlindPreferenceCheck:
    by_style: dict[str, list[BacktestMetrics]] = {}
    for result in walk_forward:
        by_style.setdefault(result.style_name, []).append(result.validation)
    validation_scores = {
        style: _average_metric(metrics, "sharpe") - _average_metric(metrics, "max_drawdown")
        for style, metrics in by_style.items()
    }
    preferred = max(validation_scores, key=validation_scores.get)
    best = ranking[0].style_name
    rank = next(index + 1 for index, row in enumerate(ranking) if row.style_name == preferred)
    return AIBlindPreferenceCheck(
        ai_preferred_style_before_test=preferred,  # type: ignore[arg-type]
        reason=[
            "selected from train/validation summary only",
            "higher validation risk-adjusted score",
            "test period locked before preference",
        ],
        actual_best_oos_style_by_robust_score=best,
        ai_preferred_style_rank_oos=rank,
        match=preferred == best,
    )


def _render_markdown(report: StrategyStyleTournamentReport) -> str:
    rows = "\n".join(
        "| {style} | {score:.2%} | {ret:.2%} | {sharpe:.3f} | {dd:.2%} | `{deploy}` |".format(
            style=row.style_name,
            score=row.robust_score,
            ret=row.total_return,
            sharpe=row.sharpe,
            dd=row.max_drawdown,
            deploy=row.deployability,
        )
        for row in report.ranking
    )
    return f"""# Strategy Style Tournament

Schema: `{report.schema_version}`
Symbol: `{report.symbol}`
Generated at: `{report.generated_at.isoformat()}`

## Ranking

Robust score uses CAGR, Sharpe, Calmar, drawdown inverse, downside risk inverse,
stability, and turnover/cost inverse ranks. It is not a deployability score.

| Style | Robust score | Avg OOS return | Avg OOS Sharpe | Avg max drawdown | Deployability |
| --- | ---: | ---: | ---: | ---: | --- |
{rows}

## Winners

- Best total return style: `{report.best_total_return_style}`
- Best risk-adjusted style: `{report.best_risk_adjusted_style}`
- Lowest drawdown style: `{report.lowest_drawdown_style}`
- Most stable OOS style: `{report.most_stable_oos_style}`
- Recommended next research style: `{report.recommended_next_research_style}`

## AI Blind Preference Check

- Preferred before test: `{report.ai_blind_preference_check.ai_preferred_style_before_test}`
- Actual best OOS by robust score: `{report.ai_blind_preference_check.actual_best_oos_style_by_robust_score}`
- Preferred style OOS rank: `{report.ai_blind_preference_check.ai_preferred_style_rank_oos}`
- Match: `{str(report.ai_blind_preference_check.match).lower()}`
- Visible data: `{report.ai_blind_preference_check.data_visible_to_ai}`

## Boundary

- Research-only: `{str(report.research_only).lower()}`
- Deployable: `{str(report.deployable).lower()}`
- Order allowed: `{str(report.order_allowed).lower()}`
- Human required: `{str(report.human_required).lower()}`
- Human intervention during run: `{str(report.human_intervention_during_run).lower()}`

Reasons not deployable:

{chr(10).join(f"- {reason}" for reason in report.reason_not_deployable)}

Note: Phase 10 is offline research and adapter preparation only. It is not a
paper trading, live trading, broker, or order-routing system.
"""


def _adapter_input_sample(symbol: str, daily_bars: list[Bar], hourly_bars: list[Bar]) -> dict:
    return {
        "schema_version": "phase10.nautilus_adapter_input_sample.v1",
        "adapter_scope": "read_only_backtest_input_spike",
        "target_engine": "NautilusTrader",
        "symbol": symbol,
        "instrument_hint": {
            "venue": "BINANCE",
            "base": symbol.split("-")[0],
            "quote": symbol.split("-")[1] if "-" in symbol else "USDT",
            "bar_types": ["1-HOUR", "1-DAY"],
        },
        "bars_1d_sample": [bar.model_dump(mode="json") for bar in daily_bars[-5:]],
        "bars_1h_sample": [bar.model_dump(mode="json") for bar in hourly_bars[:24]],
        "deployable": False,
        "order_allowed": False,
        "human_required": True,
        "notes": [
            "read-only adapter sample",
            "no paper trading",
            "no live trading",
            "no broker credentials",
        ],
    }


def run_strategy_style_tournament(
    *,
    research_output_dir: Path,
    audit_output_dir: Path,
    adapter_output_dir: Path,
    symbol: str = "BTC-USDT",
) -> StrategyStyleTournamentReport:
    bars = generate_phase10_daily_bars(symbol)
    hourly_bars = generate_phase10_hourly_adapter_sample(symbol)
    registry = default_strategy_style_registry()
    splits = default_walk_forward_splits()
    cost_models = default_cost_models()
    medium_cost = next(cost for cost in cost_models if cost.name == "medium_cost")

    walk_forward: list[WalkForwardStyleResult] = []
    for split in splits:
        for definition in registry:
            walk_forward.append(
                WalkForwardStyleResult(
                    split_name=split.name,
                    style_name=definition.spec.style_name,
                    train=run_style_backtest(
                        _slice_bars(bars, split.train_start, split.train_end),
                        definition,
                        cost_model=medium_cost,
                        score_start=split.train_start,
                        score_end=split.train_end,
                    ),
                    validation=run_style_backtest(
                        _slice_bars(bars, split.validation_start, split.validation_end),
                        definition,
                        cost_model=medium_cost,
                        score_start=split.validation_start,
                        score_end=split.validation_end,
                    ),
                    test=run_style_backtest(
                        _slice_bars(bars, split.test_start, split.test_end),
                        definition,
                        cost_model=medium_cost,
                        score_start=split.test_start,
                        score_end=split.test_end,
                    ),
                )
            )

    cost_sensitivity = _build_cost_sensitivity(bars, registry, splits, cost_models)
    stress_tests = _build_stress_tests(bars, registry, splits, medium_cost)
    ranking = _build_ranking(_aggregate_style_metrics(walk_forward), cost_sensitivity)
    blind_check = _blind_preference(walk_forward, ranking)
    report = StrategyStyleTournamentReport(
        generated_at=bars[-1].ts,
        symbol=symbol,
        data_start=bars[0].ts.date().isoformat(),
        data_end=bars[-1].ts.date().isoformat(),
        styles_tested=[definition.spec.style_name for definition in registry],
        ranking=ranking,
        best_total_return_style=max(ranking, key=lambda row: row.total_return).style_name,
        best_risk_adjusted_style=max(ranking, key=lambda row: row.sharpe).style_name,
        lowest_drawdown_style=min(ranking, key=lambda row: row.max_drawdown).style_name,
        most_stable_oos_style=max(ranking, key=lambda row: row.parameter_stability).style_name,
        recommended_next_research_style=blind_check.ai_preferred_style_before_test,
        ai_blind_preference_check=blind_check,
        reason_not_deployable=[
            "research-only phase",
            "no paper trading validation",
            "single venue deterministic sample data",
            "limited cost model",
            "requires human review",
        ],
    )

    research_output_dir.mkdir(parents=True, exist_ok=True)
    audit_output_dir.mkdir(parents=True, exist_ok=True)
    adapter_output_dir.mkdir(parents=True, exist_ok=True)
    tournament_json = write_json(
        research_output_dir / "strategy_style_tournament.json",
        report.model_dump(mode="json"),
    )
    tournament_md = research_output_dir / "strategy_style_tournament.md"
    tournament_md.write_text(_render_markdown(report), encoding="utf-8")
    walk_forward_json = write_json(
        research_output_dir / "walk_forward_results.json",
        [row.model_dump(mode="json") for row in walk_forward],
    )
    stress_json = write_json(
        research_output_dir / "stress_test_results.json",
        [row.model_dump(mode="json") for row in stress_tests],
    )
    cost_json = write_json(
        research_output_dir / "cost_sensitivity_results.json",
        [row.model_dump(mode="json") for row in cost_sensitivity],
    )
    registry_json = write_json(
        research_output_dir / "strategy-style-registry.json",
        [definition.spec.model_dump(mode="json") for definition in registry],
    )
    adapter_json = write_json(
        adapter_output_dir / "adapter_input_sample.json",
        _adapter_input_sample(symbol, bars, hourly_bars),
    )
    artifact_paths = {
        "strategy_style_tournament_md": tournament_md,
        "strategy_style_tournament_json": tournament_json,
        "walk_forward_results": walk_forward_json,
        "stress_test_results": stress_json,
        "cost_sensitivity_results": cost_json,
        "strategy_style_registry": registry_json,
        "adapter_input_sample": adapter_json,
    }
    manifest = SimulationManifest(
        generated_at=report.generated_at,
        symbol=symbol,
        data_start=report.data_start,
        data_end=report.data_end,
        data_hash=stable_hash([bar.model_dump(mode="json") for bar in bars]),
        strategy_registry_hash=stable_hash([definition.spec.model_dump(mode="json") for definition in registry]),
        risk_config_hash=stable_hash({"position_source": "style_signal", "execution_delay_bars": 1}),
        walk_forward_split_hash=stable_hash([split.model_dump(mode="json") for split in splits]),
        cost_model_hash=stable_hash([cost.model_dump(mode="json") for cost in cost_models]),
        artifacts={key: str(path) for key, path in artifact_paths.items()},
        artifact_hashes={key: file_sha256(path) for key, path in artifact_paths.items()},
    )
    manifest_path = write_json(audit_output_dir / "simulation_manifest.json", manifest.model_dump(mode="json"))
    write_artifact_catalog(
        research_output_dir,
        run_id="phase10-strategy-style-tournament",
        artifacts=[
            ("strategy_style_tournament_md", tournament_md),
            ("strategy_style_tournament_json", tournament_json),
            ("walk_forward_results", walk_forward_json),
            ("stress_test_results", stress_json),
            ("cost_sensitivity_results", cost_json),
            ("strategy_style_registry", registry_json),
        ],
        created_at=report.generated_at,
    )
    manifest_hash_path = research_output_dir / "simulation_manifest.sha256"
    manifest_hash_path.write_text(file_sha256(manifest_path), encoding="utf-8")
    return report
