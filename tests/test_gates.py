from __future__ import annotations

from quant_agent_lab.core.schemas import Action, GateStatus
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.data.validation import validate_market_snapshot
from quant_agent_lab.decision.committee import build_recommendation_draft
from quant_agent_lab.risk.gate import RiskGate
from quant_agent_lab.strategy.signals import build_signal_bundle


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
