from __future__ import annotations

from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import PipelineConfig, RiskConfig
from quant_agent_lab.core.schemas import GateStatus


def test_daily_pipeline_is_deterministic() -> None:
    first = run_daily_pipeline()
    second = run_daily_pipeline()
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_daily_pipeline_generates_report_and_audit_fields() -> None:
    result = run_daily_pipeline()
    assert result.data_validation.status == GateStatus.PASS
    assert result.recommendation.human_required is True
    assert result.recommendation.order_allowed is False
    assert result.risk_decision.order_allowed is False
    assert result.recommendation.evidence_ids
    assert "Daily Advisory Report" in result.report_markdown


def test_strict_risk_config_blocks_directional_draft() -> None:
    result = run_daily_pipeline(
        config=PipelineConfig(
            risk=RiskConfig(max_position_pct=0.01, max_loss_budget_pct=0.02),
        )
    )
    assert result.risk_decision.status == GateStatus.FAIL
    assert "target_position_pct exceeds limit" in result.risk_decision.reasons
