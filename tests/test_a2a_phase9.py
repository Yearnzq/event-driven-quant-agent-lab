from __future__ import annotations

import json

import pytest

from quant_agent_lab.a2a.mock import A2AClient, A2AClientAgent, MockA2AAgentServer
from quant_agent_lab.agents.model import SingleModelRecommendationAgent
from quant_agent_lab.app.cli import main
from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import PipelineConfig
from quant_agent_lab.core.schemas import A2AAgentCard, Action, GateStatus
from quant_agent_lab.data.audit import validate_run_manifest


def _a2a_agent(config: PipelineConfig, *, timeout_seconds: float = 5.0, max_retries: int = 1) -> A2AClientAgent:
    server = MockA2AAgentServer(SingleModelRecommendationAgent(config.model_provider))
    client = A2AClient(server, timeout_seconds=timeout_seconds, max_retries=max_retries)
    return A2AClientAgent(client)


def test_a2a_fake_agent_writes_card_trace_and_report(tmp_path) -> None:
    output_dir = tmp_path / "a2a-fake"
    config = PipelineConfig(output_dir=output_dir)
    result = run_daily_pipeline(config=config, agents=[_a2a_agent(config)])

    assert result.a2a_agent_cards
    assert result.a2a_agent_cards[0].schema_version == "phase9.agent_card.v1"
    assert result.a2a_agent_cards[0].order_allowed is False
    assert result.a2a_trace_records
    assert result.a2a_trace_records[0].status == GateStatus.PASS
    assert result.a2a_trace_records[0].run_id == result.run_id
    assert result.a2a_trace_records[0].order_allowed is False
    assert "A2A Trace" in result.report_markdown
    assert result.recommendation.order_allowed is False
    assert result.risk_decision.order_allowed is False

    card_path = output_dir / "a2a-agent-card.json"
    trace_path = output_dir / "a2a-trace.json"
    assert card_path.exists()
    assert trace_path.exists()
    assert json.loads(card_path.read_text(encoding="utf-8"))[0]["schema_version"] == "phase9.agent_card.v1"
    assert json.loads(trace_path.read_text(encoding="utf-8"))[0]["schema_version"] == "phase9.a2a_trace.v1"
    validation = validate_run_manifest(output_dir, required_roles={"a2a_agent_card", "a2a_trace"})
    assert validation.status == "pass"


def test_a2a_timeout_retries_and_fails_closed(tmp_path) -> None:
    config = PipelineConfig(output_dir=tmp_path / "a2a-timeout")
    server = MockA2AAgentServer(
        SingleModelRecommendationAgent(config.model_provider),
        response_delay_seconds=0.05,
    )
    client = A2AClient(server, timeout_seconds=0.01, max_retries=1)
    result = run_daily_pipeline(config=config, agents=[A2AClientAgent(client)])

    assert result.agent_opinions[0].status == GateStatus.FAIL
    assert result.agent_opinions[0].action_bias == Action.INSUFFICIENT_EVIDENCE
    assert result.agent_opinions[0].error_message == "TimeoutError: redacted"
    assert result.a2a_trace_records[0].status == GateStatus.FAIL
    assert result.a2a_trace_records[0].attempt_count == 2
    assert result.a2a_trace_records[0].error_message == "TimeoutError: redacted"
    assert result.recommendation.action == Action.INSUFFICIENT_EVIDENCE
    assert result.risk_decision.order_allowed is False


def test_a2a_agent_card_cannot_allow_orders() -> None:
    payload = {
        "agent_id": "unsafe",
        "name": "unsafe",
        "description": "unsafe card",
    }
    payload["order_allowed"] = bool("boundary violation")

    with pytest.raises(ValueError, match="cannot allow orders"):
        A2AAgentCard(**payload)


def test_cli_a2a_advisory_fake(tmp_path) -> None:
    output_dir = tmp_path / "cli-a2a"

    assert main(["--run-a2a-advisory", "--output-dir", str(output_dir)]) == 0
    assert (output_dir / "a2a-agent-card.json").exists()
    assert (output_dir / "a2a-trace.json").exists()
