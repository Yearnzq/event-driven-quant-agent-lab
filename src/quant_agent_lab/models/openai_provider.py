from __future__ import annotations

import json
import os
import time
from urllib import request

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from quant_agent_lab.core.config import ModelProviderConfig
from quant_agent_lab.core.schemas import (
    Action,
    AgentOpinion,
    GateStatus,
    ModelCallAuditRecord,
    RenderedPrompt,
)
from quant_agent_lab.data.audit import stable_hash
from quant_agent_lab.models.fake_provider import _estimate_tokens


OPENAI_PROVIDER_ENABLE_ENV = "QAL_ENABLE_OPENAI_PROVIDER"
CODEX_PROVIDER_ENABLE_ENV = "QAL_ENABLE_CODEX_PROVIDER"


class AgentOpinionPayload(BaseModel):
    model_config = ConfigDict(frozen=True)

    action_bias: Action
    confidence: float = Field(ge=0, le=1)
    rationale: list[str] = Field(min_length=1)
    risk_flags: list[str] = Field(default_factory=list)


def _redact_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: redacted"


def _output_text(response_payload: dict) -> str:
    if isinstance(response_payload.get("output_text"), str):
        return response_payload["output_text"]
    chunks: list[str] = []
    for output_item in response_payload.get("output", []):
        for content in output_item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)


def _chat_completion_text(response_payload: dict) -> str:
    choices = response_payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


class OpenAIResponsesProvider:
    name = "openai"

    def __init__(self, config: ModelProviderConfig) -> None:
        if config.provider not in {"openai", "codex"}:
            raise ValueError("OpenAIResponsesProvider requires provider='openai' or provider='codex'")
        if not config.allow_network:
            raise ValueError(f"{config.provider} provider requires allow_network=true")
        enable_env = CODEX_PROVIDER_ENABLE_ENV if config.provider == "codex" else OPENAI_PROVIDER_ENABLE_ENV
        if os.environ.get(enable_env) != "1":
            raise RuntimeError(f"{config.provider} provider is disabled by default")
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing API key env: {config.api_key_env}")
        self.config = config
        self.api_key = api_key

    @staticmethod
    def _json_schema() -> dict:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action_bias": {
                    "type": "string",
                    "enum": [
                        Action.BUY.value,
                        Action.SELL.value,
                        Action.HOLD.value,
                        Action.REVIEW_REQUIRED.value,
                        Action.NO_TRADE.value,
                        Action.INSUFFICIENT_EVIDENCE.value,
                    ],
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "rationale": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 5,
                },
                "risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 8,
                },
            },
            "required": ["action_bias", "confidence", "rationale", "risk_flags"],
        }

    def invoke(self, prompt: RenderedPrompt) -> tuple[AgentOpinion, ModelCallAuditRecord]:
        started = time.perf_counter()
        is_chat_completions = self.config.api_base_url.rstrip("/").endswith("/chat/completions")
        if is_chat_completions:
            payload = {
                "model": self.config.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Return exactly one valid JSON object and no markdown. "
                            "The only allowed keys are action_bias, confidence, rationale, risk_flags. "
                            "action_bias must be one of buy, sell, hold, review_required, no_trade, "
                            "insufficient_evidence. confidence must be a number from 0 to 1. "
                            "rationale and risk_flags must be arrays of strings. "
                            "Never create orders and never set order_allowed."
                        ),
                    },
                    {"role": "user", "content": prompt.rendered_prompt},
                ],
                "max_completion_tokens": 512,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "agent_opinion_payload",
                        "strict": True,
                        "schema": self._json_schema(),
                    },
                },
            }
        else:
            payload = {
                "model": self.config.model_name,
                "input": prompt.rendered_prompt,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "agent_opinion_payload",
                        "strict": True,
                        "schema": self._json_schema(),
                    }
                },
            }
        encoded = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.config.api_base_url,
            data=encoded,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:  # noqa: S310 - endpoint is explicit config.
                response_payload = json.loads(response.read().decode("utf-8"))
            output_text = _chat_completion_text(response_payload) if is_chat_completions else _output_text(response_payload)
            parsed = AgentOpinionPayload.model_validate_json(output_text)
            opinion = AgentOpinion(
                agent_name="single_model_recommendation_draft",
                status=GateStatus.PASS,
                action_bias=parsed.action_bias,
                confidence=parsed.confidence,
                rationale=parsed.rationale,
                risk_flags=parsed.risk_flags,
                evidence_ids=[prompt.prompt_hash],
                generated_at=prompt.created_at,
            )
            status = GateStatus.PASS
            error_message = None
        except (OSError, TimeoutError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            opinion = AgentOpinion(
                agent_name="single_model_recommendation_draft",
                status=GateStatus.FAIL,
                action_bias=Action.INSUFFICIENT_EVIDENCE,
                confidence=0.0,
                rationale=["single model provider failed; degraded to insufficient evidence"],
                risk_flags=["model_provider_failed"],
                evidence_ids=[prompt.prompt_hash],
                error_message=_redact_error(exc),
                generated_at=prompt.created_at,
            )
            output_text = opinion.model_dump_json()
            status = GateStatus.FAIL
            error_message = _redact_error(exc)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        usage = locals().get("response_payload", {}).get("usage", {})
        input_tokens = int(
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or _estimate_tokens(prompt.rendered_prompt)
        )
        output_tokens = int(
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or _estimate_tokens(output_text)
        )
        estimated_cost = (
            (input_tokens / 1_000_000) * self.config.input_cost_per_million_tokens
            + (output_tokens / 1_000_000) * self.config.output_cost_per_million_tokens
        )
        audit = ModelCallAuditRecord(
            provider=self.config.provider,
            model_name=self.config.model_name,
            prompt_id=prompt.prompt_id,
            prompt_version=prompt.prompt_version,
            input_hash=prompt.input_hash,
            prompt_hash=prompt.prompt_hash,
            output_hash=stable_hash(opinion.model_dump(mode="json")),
            output_schema=prompt.output_schema,
            status=status,
            latency_ms=elapsed_ms,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=round(estimated_cost, 8),
            error_message=error_message,
            called_at=prompt.created_at,
        )
        return opinion, audit
