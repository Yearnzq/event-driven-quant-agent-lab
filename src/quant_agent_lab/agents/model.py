from __future__ import annotations

from quant_agent_lab.core.config import ModelProviderConfig
from quant_agent_lab.core.schemas import (
    Action,
    AgentOpinion,
    GateStatus,
    MarketSnapshot,
    ModelCallAuditRecord,
    SignalBundle,
)
from quant_agent_lab.data.audit import stable_hash
from quant_agent_lab.models.fake_provider import FakeStructuredModelProvider, _estimate_tokens
from quant_agent_lab.models.openai_provider import OpenAIResponsesProvider, _redact_error
from quant_agent_lab.models.prompts import render_recommendation_prompt


class SingleModelRecommendationAgent:
    name = "single_model_recommendation_draft"

    def __init__(self, provider_config: ModelProviderConfig) -> None:
        self.provider_config = provider_config
        self.last_audit_record: ModelCallAuditRecord | None = None

    def _provider(self):
        if self.provider_config.provider == "fake":
            return FakeStructuredModelProvider(self.provider_config)
        if self.provider_config.provider in {"openai", "codex"}:
            return OpenAIResponsesProvider(self.provider_config)
        raise ValueError(f"unsupported model provider: {self.provider_config.provider}")

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        prompt = render_recommendation_prompt(
            signals=signals,
            provider_config=self.provider_config,
        )
        try:
            opinion, audit = self._provider().invoke(prompt)
            opinion = opinion.model_copy(update={"agent_name": self.name})
        except Exception as exc:
            error_message = _redact_error(exc)
            opinion = AgentOpinion(
                agent_name=self.name,
                status=GateStatus.FAIL,
                action_bias=Action.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                rationale=["single model agent failed; degraded to insufficient evidence"],
                risk_flags=["single_model_agent_failed"],
                evidence_ids=[prompt.prompt_hash],
                error_message=error_message,
                generated_at=market.as_of,
            )
            audit = ModelCallAuditRecord(
                provider=self.provider_config.provider,
                model_name=self.provider_config.model_name,
                prompt_id=prompt.prompt_id,
                prompt_version=prompt.prompt_version,
                input_hash=prompt.input_hash,
                prompt_hash=prompt.prompt_hash,
                output_hash=stable_hash(opinion.model_dump(mode="json")),
                output_schema=prompt.output_schema,
                status=GateStatus.FAIL,
                latency_ms=0.0,
                estimated_input_tokens=_estimate_tokens(prompt.rendered_prompt),
                estimated_output_tokens=_estimate_tokens(opinion.model_dump_json()),
                estimated_cost_usd=0.0,
                error_message=error_message,
                called_at=market.as_of,
            )
        self.last_audit_record = audit
        return opinion
