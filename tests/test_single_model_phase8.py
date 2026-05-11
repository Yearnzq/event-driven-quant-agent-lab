from __future__ import annotations

import json

from quant_agent_lab.agents.model import SingleModelRecommendationAgent
from quant_agent_lab.app.cli import main
from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import ModelProviderConfig, PipelineConfig
from quant_agent_lab.core.schemas import Action, GateStatus, ModelCallAuditRecord
from quant_agent_lab.data.audit import validate_run_manifest


def test_single_fake_model_agent_writes_model_audit(tmp_path) -> None:
    output_dir = tmp_path / "single-model-fake"
    config = PipelineConfig(output_dir=output_dir)
    result = run_daily_pipeline(
        config=config,
        agents=[SingleModelRecommendationAgent(config.model_provider)],
    )

    assert result.model_call_audits
    assert result.model_call_audits[0].provider == "fake"
    assert result.model_call_audits[0].status == GateStatus.PASS
    assert result.model_call_audits[0].order_allowed is False
    assert "Model Call Audit" in result.report_markdown
    assert "estimated_cost_usd" in result.report_markdown
    assert result.recommendation.order_allowed is False
    assert result.risk_decision.order_allowed is False
    audit_path = output_dir / "model-call-audit.json"
    assert audit_path.exists()
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    assert payload[0]["schema_version"] == "phase7.model_call_audit.v1"
    manifest_payload = json.loads((output_dir / "run-manifest.json").read_text(encoding="utf-8"))
    audit_payload = json.loads((output_dir / f"{result.run_id}.audit.json").read_text(encoding="utf-8"))
    assert manifest_payload["model_provider"] == "fake"
    assert manifest_payload["model_name"] == "fake-structured-advisory-v1"
    assert audit_payload["model_provider"] == "fake"
    assert audit_payload["model_name"] == "fake-structured-advisory-v1"
    assert validate_run_manifest(output_dir, required_roles={"model_call_audit"}).status == "pass"


def test_openai_provider_missing_key_fails_closed(tmp_path, monkeypatch) -> None:
    missing_key_env = "QAL_TEST_MISSING_OPENAI_API_KEY"
    monkeypatch.delenv(missing_key_env, raising=False)
    monkeypatch.setenv("QAL_ENABLE_OPENAI_PROVIDER", "1")
    config = PipelineConfig(
        output_dir=tmp_path / "single-model-openai-missing-key",
        model_provider=ModelProviderConfig(
            provider="openai",
            model_name="gpt-5.4-mini",
            allow_network=True,
            api_key_env=missing_key_env,
        ),
    )
    result = run_daily_pipeline(config=config, agents=[SingleModelRecommendationAgent(config.model_provider)])

    assert result.agent_opinions[0].status == GateStatus.FAIL
    assert result.agent_opinions[0].action_bias == Action.INSUFFICIENT_EVIDENCE
    assert result.agent_opinions[0].error_message == "RuntimeError: redacted"
    assert result.recommendation.action == Action.INSUFFICIENT_EVIDENCE
    assert result.risk_decision.final_action == Action.INSUFFICIENT_EVIDENCE
    assert result.risk_decision.order_allowed is False
    assert result.model_call_audits[0].provider == "openai"
    assert result.model_call_audits[0].status == GateStatus.FAIL
    assert result.model_call_audits[0].error_message == "RuntimeError: redacted"


def test_openai_provider_network_disabled_fails_closed(tmp_path) -> None:
    config = PipelineConfig(
        output_dir=tmp_path / "single-model-openai-network-disabled",
        model_provider=ModelProviderConfig(
            provider="openai",
            model_name="gpt-5.4-mini",
            allow_network=False,
        ),
    )
    result = run_daily_pipeline(config=config, agents=[SingleModelRecommendationAgent(config.model_provider)])

    assert result.agent_opinions[0].status == GateStatus.FAIL
    assert result.model_call_audits[0].provider == "openai"
    assert result.model_call_audits[0].status == GateStatus.FAIL
    assert result.model_call_audits[0].error_message == "ValueError: redacted"
    assert result.risk_decision.order_allowed is False


def test_model_call_audit_cannot_allow_orders() -> None:
    audit = ModelCallAuditRecord(
        provider="fake",
        model_name="fake",
        prompt_id="prompt",
        prompt_version="v1",
        input_hash="in",
        prompt_hash="prompt",
        output_hash="out",
        output_schema="AgentOpinion",
        status=GateStatus.PASS,
        latency_ms=0,
        estimated_input_tokens=1,
        estimated_output_tokens=1,
        estimated_cost_usd=0,
        called_at=PipelineConfig().as_of,
    )

    assert audit.order_allowed is False
    assert audit.human_required is True


def test_cli_single_model_advisory_fake(tmp_path) -> None:
    output_dir = tmp_path / "cli-single-model"

    assert main(["--run-single-model-advisory", "--output-dir", str(output_dir)]) == 0
    assert (output_dir / "model-call-audit.json").exists()
