from __future__ import annotations

from math import ceil
from pathlib import Path

from quant_agent_lab.app.pipeline import load_market
from quant_agent_lab.core.config import PipelineConfig
from quant_agent_lab.core.schemas import (
    Action,
    AgentOpinion,
    GateStatus,
    ModelBoundaryResult,
    ModelCallAuditRecord,
    RenderedPrompt,
)
from quant_agent_lab.data.audit import stable_hash, write_artifact_catalog, write_json
from quant_agent_lab.data.validation import validate_market_snapshot
from quant_agent_lab.models.prompts import default_prompt_registry, render_recommendation_prompt
from quant_agent_lab.strategy.signals import build_signal_bundle


def _estimate_tokens(text: str) -> int:
    return max(1, ceil(len(text) / 4))


class FakeStructuredModelProvider:
    name = "fake"

    def __init__(self, config) -> None:
        if config.provider != "fake":
            raise ValueError("Phase 7 only supports the fake provider")
        if config.allow_network:
            raise ValueError("Phase 7 fake provider must not allow network access")
        self.config = config

    def invoke(self, prompt: RenderedPrompt) -> tuple[AgentOpinion, ModelCallAuditRecord]:
        if prompt.provider != "fake":
            raise ValueError("Phase 7 fake provider received a non-fake prompt")
        prompt_text = prompt.rendered_prompt.lower()
        if '"direction": "bullish"' in prompt_text:
            action = Action.BUY
            rationale = ["fake provider sees bullish deterministic signal summary"]
        elif '"direction": "bearish"' in prompt_text:
            action = Action.SELL
            rationale = ["fake provider sees bearish deterministic signal summary"]
        else:
            action = Action.REVIEW_REQUIRED
            rationale = ["fake provider found no clear directional signal"]

        opinion = AgentOpinion(
            agent_name="fake_model_recommendation_draft",
            status=GateStatus.PASS,
            action_bias=action,
            confidence=0.57,
            rationale=rationale,
            risk_flags=["fake_provider_only"],
            evidence_ids=[prompt.prompt_hash],
            generated_at=prompt.created_at,
        )
        output_payload = opinion.model_dump(mode="json")
        output_text = opinion.model_dump_json()
        audit = ModelCallAuditRecord(
            provider="fake",
            model_name=self.config.model_name,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            input_hash=prompt.input_hash,
            prompt_hash=prompt.prompt_hash,
            output_hash=stable_hash(output_payload),
            output_schema=prompt.output_schema,
            status=GateStatus.PASS,
            latency_ms=0.0,
            estimated_input_tokens=_estimate_tokens(prompt.rendered_prompt),
            estimated_output_tokens=_estimate_tokens(output_text),
            estimated_cost_usd=0.0,
            called_at=prompt.created_at,
        )
        return opinion, audit


def run_fake_model_boundary_check(
    *,
    config: PipelineConfig,
    output_dir: Path,
) -> ModelBoundaryResult:
    market = load_market(config)
    data_validation = validate_market_snapshot(market)
    if data_validation.status == GateStatus.FAIL:
        raise ValueError("model boundary check requires passing market data validation")
    signals = build_signal_bundle(market)
    prompt = render_recommendation_prompt(
        signals=signals,
        provider_config=config.model_provider,
    )
    provider = FakeStructuredModelProvider(config.model_provider)
    opinion, audit = provider.invoke(prompt)
    result = ModelBoundaryResult(
        opinion=opinion,
        audit_record=audit,
        prompt_registry=default_prompt_registry(),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    registry_path = write_json(
        output_dir / "prompt-registry.json",
        [spec.model_dump(mode="json") for spec in result.prompt_registry],
    )
    prompt_meta_path = write_json(
        output_dir / "rendered-prompt-meta.json",
        prompt.model_dump(mode="json", exclude={"rendered_prompt"}),
    )
    opinion_path = write_json(output_dir / "fake-agent-opinion.json", opinion.model_dump(mode="json"))
    audit_path = write_json(output_dir / "model-call-audit.json", audit.model_dump(mode="json"))
    result_path = write_json(output_dir / "model-boundary-result.json", result.model_dump(mode="json"))
    write_artifact_catalog(
        output_dir,
        run_id=f"phase7-model-boundary-{signals.symbol.lower().replace('-', '-')}",
        artifacts=[
            ("prompt_registry", registry_path),
            ("rendered_prompt_meta", prompt_meta_path),
            ("fake_agent_opinion", opinion_path),
            ("model_call_audit", audit_path),
            ("model_boundary_result", result_path),
        ],
        created_at=signals.as_of,
    )
    return result
