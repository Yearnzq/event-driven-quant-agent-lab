from __future__ import annotations

from quant_agent_lab.core.schemas import Action, GateStatus
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.data.validation import validate_market_snapshot
from quant_agent_lab.decision.committee import build_recommendation_draft
from quant_agent_lab.risk.gate import RiskGate
from quant_agent_lab.strategy.signals import build_signal_bundle


def _with_hourly_closes(snapshot, closes: list[float]):
    bars = []
    for bar, close in zip(snapshot.bars_1h, closes):
        bars.append(
            bar.model_copy(
                update={
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                }
            )
        )
    return snapshot.model_copy(update={"bars_1h": bars})


def test_data_gate_fails_on_missing_daily_history() -> None:
    snapshot = load_mock_market_snapshot(bars_1d_count=10)
    result = validate_market_snapshot(snapshot)
    assert result.status == GateStatus.FAIL
    assert "fewer than 30 daily bars" in result.reasons


def test_data_gate_fails_on_hourly_gap() -> None:
    snapshot = load_mock_market_snapshot()
    broken = snapshot.model_copy(update={"bars_1h": snapshot.bars_1h[:10] + snapshot.bars_1h[11:]})
    result = validate_market_snapshot(broken)
    assert result.status == GateStatus.FAIL
    assert "hourly bars contain gaps" in result.reasons


def test_data_gate_fails_on_duplicate_timestamp() -> None:
    snapshot = load_mock_market_snapshot()
    duplicate = snapshot.bars_1h[0].model_copy(update={"ts": snapshot.bars_1h[1].ts})
    broken = snapshot.model_copy(update={"bars_1h": [duplicate] + snapshot.bars_1h[1:]})
    result = validate_market_snapshot(broken)
    assert result.status == GateStatus.FAIL
    assert "hourly bars contain duplicate timestamps" in result.reasons


def test_data_failure_forces_insufficient_evidence() -> None:
    snapshot = load_mock_market_snapshot(bars_1d_count=10)
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])
    risk = RiskGate().evaluate(draft)
    assert draft.action == Action.INSUFFICIENT_EVIDENCE
    assert risk.final_action == Action.INSUFFICIENT_EVIDENCE
    assert risk.order_allowed is False


def test_risk_gate_blocks_large_existing_position() -> None:
    snapshot = load_mock_market_snapshot()
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate(max_existing_position_pct=0.05).evaluate(
        draft,
        market=snapshot,
        signals=signals,
    )

    assert risk.status == GateStatus.FAIL
    assert "existing position exceeds limit" in risk.reasons


def test_risk_gate_blocks_low_cash_buffer() -> None:
    snapshot = load_mock_market_snapshot()
    low_cash_portfolio = snapshot.portfolio.model_copy(update={"cash": 1000})
    snapshot = snapshot.model_copy(update={"portfolio": low_cash_portfolio})
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate(min_cash_pct=0.05).evaluate(draft, market=snapshot, signals=signals)

    assert risk.status == GateStatus.FAIL
    assert "cash buffer is below minimum" in risk.reasons


def test_risk_gate_records_portfolio_risk_metrics() -> None:
    snapshot = load_mock_market_snapshot()
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate().evaluate(draft, market=snapshot, signals=signals)

    assert "existing_position_pct" in risk.risk_metrics
    assert "cash_pct" in risk.risk_metrics
    assert "recent_drawdown_pct" in risk.risk_metrics
    assert "downside_volatility" in risk.risk_metrics
    assert "portfolio_risk_budget_pct" in risk.risk_metrics
    assert "hourly_return_vol" in risk.risk_metrics


def test_risk_gate_blocks_recent_drawdown() -> None:
    snapshot = load_mock_market_snapshot()
    closes = [100.0 + index for index in range(60)] + [158.0, 150.0, 140.0, 132.0, 126.0, 120.0, 118.0, 116.0, 114.0, 112.0, 110.0, 108.0]
    snapshot = _with_hourly_closes(snapshot, closes)
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate(max_recent_drawdown_pct=0.05).evaluate(draft, market=snapshot, signals=signals)

    assert risk.status == GateStatus.FAIL
    assert "recent drawdown exceeds limit" in risk.reasons


def test_risk_gate_blocks_downside_volatility_and_single_hour_loss() -> None:
    snapshot = load_mock_market_snapshot()
    closes = [100.0 + index * 0.1 for index in range(60)] + [106.0, 95.0, 96.0, 84.0, 85.0, 74.0, 75.0, 73.0, 74.0, 72.0, 73.0, 71.0]
    snapshot = _with_hourly_closes(snapshot, closes)
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate(
        max_downside_volatility=0.02,
        max_single_hour_loss_pct=0.05,
    ).evaluate(draft, market=snapshot, signals=signals)

    assert risk.status == GateStatus.FAIL
    assert "downside volatility exceeds limit" in risk.reasons
    assert "single hour loss exceeds limit" in risk.reasons


def test_risk_gate_blocks_portfolio_risk_budget() -> None:
    snapshot = load_mock_market_snapshot()
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])

    risk = RiskGate(max_portfolio_risk_budget_pct=0.000001).evaluate(
        draft,
        market=snapshot,
        signals=signals,
    )

    assert risk.status == GateStatus.FAIL
    assert "portfolio risk budget exceeds limit" in risk.reasons


def test_risk_returns_handles_empty_and_short_inputs() -> None:
    assert RiskGate._returns([]) == []
    assert RiskGate._returns([100.0]) == []
    assert RiskGate._returns([0.0, 100.0]) == []
