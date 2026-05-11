from __future__ import annotations

import json

import pytest

from quant_agent_lab.app.cli import main
from quant_agent_lab.core.config import ModelProviderConfig, PipelineConfig
from quant_agent_lab.core.schemas import GateStatus, ModelCallAuditRecord
from quant_agent_lab.models.fake_provider import FakeStructuredModelProvider, run_fake_model_boundary_check
from quant_agent_lab.models.prompts import default_prompt_registry, render_recommendation_prompt
from quant_agent_lab.strategy.signals import build_signal_bundle
from quant_agent_lab.data.mock import load_mock_market_snapshot


def test_prompt_registry_is_advisory_only() -> None:
    registry = default_prompt_registry()

    assert registry
    assert registry[0].schema_version == "phase7.prompt_spec.v1"
    assert registry[0].output_schema == "AgentOpinion"
    assert registry[0].advisory_only is True
    assert "Never create orders" in registry[0].template
    assert "risk_limits_mutable_by_model" in registry[0].input_contract


def test_rendered_prompt_records_hashes_without_raw_text_artifact() -> None:
    market = load_mock_market_snapshot()
    signals = build_signal_bundle(market)
    rendered = render_recommendation_prompt(
        signals=signals,
        provider_config=ModelProviderConfig(),
    )

    assert rendered.schema_version == "phase7.rendered_prompt.v1"
    assert rendered.provider == "fake"
    assert rendered.input_hash
    assert rendered.prompt_hash
    assert "INPUT_JSON" in rendered.rendered_prompt


def test_fake_provider_rejects_network_enabled_config() -> None:
    with pytest.raises(ValueError, match="must not allow network"):
        FakeStructuredModelProvider(ModelProviderConfig(allow_network=True))


def test_phase7_default_model_provider_config_remains_fake() -> None:
    config = ModelProviderConfig()
    assert config.provider == "fake"
    assert config.allow_network is False
    dumped = ModelProviderConfig().model_dump()
    assert dumped["provider"] == "fake"
    assert dumped["api_key_env"] == "OPENAI_API_KEY"


def test_fake_model_boundary_writes_audited_artifacts(tmp_path) -> None:
    output_dir = tmp_path / "model-boundary"
    result = run_fake_model_boundary_check(config=PipelineConfig(output_dir=tmp_path), output_dir=output_dir)

    assert result.audit_record.schema_version == "phase7.model_call_audit.v1"
    assert result.audit_record.provider == "fake"
    assert result.audit_record.status == GateStatus.PASS
    assert result.audit_record.estimated_input_tokens > 0
    assert result.audit_record.estimated_output_tokens > 0
    assert result.audit_record.estimated_cost_usd == 0
    assert result.audit_record.latency_ms == 0
    assert result.audit_record.order_allowed is False
    assert result.audit_record.human_required is True
    assert result.opinion.status == GateStatus.PASS

    audit_payload = json.loads((output_dir / "model-call-audit.json").read_text(encoding="utf-8"))
    ModelCallAuditRecord.model_validate(audit_payload)
    prompt_meta = json.loads((output_dir / "rendered-prompt-meta.json").read_text(encoding="utf-8"))
    assert "rendered_prompt" not in prompt_meta
    assert prompt_meta["prompt_hash"] == result.audit_record.prompt_hash
    assert (output_dir / "artifact-catalog.json").exists()


def test_cli_fake_model_call(tmp_path) -> None:
    output_dir = tmp_path / "cli-model-boundary"

    assert main(["--run-fake-model-call", "--output-dir", str(output_dir)]) == 0
    assert (output_dir / "model-call-audit.json").exists()
