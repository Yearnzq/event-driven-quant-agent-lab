from __future__ import annotations

from quant_agent_lab.agents.mock import (
    MockContrarianAgent,
    MockFailingAgent,
    MockHistoricalContextAgent,
    MockNoTradeAgent,
    MockRecommendationDraftAgent,
)
from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.schemas import Action, GateStatus, ModelDisagreement


def test_agent_failure_degrades_to_review_required() -> None:
    result = run_daily_pipeline(
        agents=[
            MockHistoricalContextAgent(),
            MockRecommendationDraftAgent(),
            MockFailingAgent(),
        ]
    )

    failed = [opinion for opinion in result.agent_opinions if opinion.status == GateStatus.FAIL]
    assert len(failed) == 1
    assert failed[0].action_bias == Action.INSUFFICIENT_EVIDENCE
    assert failed[0].error_message == "RuntimeError: redacted"
    assert result.recommendation.action == Action.REVIEW_REQUIRED
    assert result.recommendation.target_position_pct == 0
    assert result.recommendation.model_disagreement == ModelDisagreement.HIGH
    assert result.recommendation.decision_trace.failed_agent_count == 1
    assert "agent_failed:mock_failing_agent" in result.recommendation.decision_trace.fallback_reasons
    assert result.risk_decision.order_allowed is False


def test_all_agent_failures_force_insufficient_evidence() -> None:
    result = run_daily_pipeline(agents=[MockFailingAgent()])

    assert result.recommendation.action == Action.INSUFFICIENT_EVIDENCE
    assert result.recommendation.confidence == 0
    assert result.recommendation.decision_trace.passed_agent_count == 0
    assert result.recommendation.decision_trace.failed_agent_count == 1
    assert result.risk_decision.final_action == Action.INSUFFICIENT_EVIDENCE


def test_conflicting_directional_agents_force_review_required() -> None:
    result = run_daily_pipeline(
        agents=[
            MockRecommendationDraftAgent(),
            MockContrarianAgent(),
        ]
    )

    assert result.recommendation.action == Action.REVIEW_REQUIRED
    assert result.recommendation.model_disagreement == ModelDisagreement.HIGH
    assert "conflicting_directional_actions" in result.recommendation.decision_trace.disagreement_reasons
    assert result.recommendation.decision_trace.action_vote_counts["buy"] == 1
    assert result.recommendation.decision_trace.action_vote_counts["sell"] == 1


def test_no_trade_agent_remains_advisory_only() -> None:
    result = run_daily_pipeline(agents=[MockNoTradeAgent()])

    assert result.recommendation.action == Action.NO_TRADE
    assert result.recommendation.target_position_pct == 0
    assert "no_trade_vote_present" in result.recommendation.decision_trace.disagreement_reasons
    assert result.risk_decision.final_action == Action.NO_TRADE
    assert result.risk_decision.order_allowed is False


def test_report_includes_phase6_decision_trace() -> None:
    result = run_daily_pipeline(agents=[MockRecommendationDraftAgent(), MockFailingAgent()])

    assert "Decision Trace" in result.report_markdown
    assert "phase6.decision_trace.v1" in result.report_markdown
    assert "Agent failures" in result.report_markdown
    assert "RuntimeError: redacted" in result.report_markdown
    assert "deterministic mock failure" not in result.report_markdown
