from __future__ import annotations

import json

from quant_agent_lab.core.config import ModelProviderConfig
from quant_agent_lab.core.schemas import PromptSpec, RenderedPrompt, SignalBundle
from quant_agent_lab.data.audit import stable_hash


RECOMMENDATION_PROMPT_ID = "phase7.fake_recommendation_draft"
RECOMMENDATION_PROMPT_VERSION = "v1"


def default_prompt_registry() -> list[PromptSpec]:
    return [
        PromptSpec(
            prompt_id=RECOMMENDATION_PROMPT_ID,
            version=RECOMMENDATION_PROMPT_VERSION,
            purpose="Prepare a bounded recommendation draft opinion from deterministic signal summaries.",
            template=(
                "You are a bounded advisory draft agent. Use only the supplied JSON summary. "
                "Return structured output matching AgentOpinion. Never create orders. "
                "Never modify risk limits. If evidence is weak or conflicting, choose review_required.\n\n"
                "INPUT_JSON:\n{input_json}\n\n"
                "OUTPUT_SCHEMA: AgentOpinion"
            ),
            input_contract=[
                "symbol",
                "as_of",
                "signals[].name",
                "signals[].direction",
                "signals[].strength",
                "advisory_boundary",
                "risk_limits_mutable_by_model",
                "advisory_boundary.risk_limits_mutable_by_model",
            ],
            output_schema="AgentOpinion",
        )
    ]


def get_prompt_spec(prompt_id: str = RECOMMENDATION_PROMPT_ID) -> PromptSpec:
    for spec in default_prompt_registry():
        if spec.prompt_id == prompt_id:
            return spec
    raise KeyError(f"unknown prompt_id: {prompt_id}")


def render_recommendation_prompt(
    *,
    signals: SignalBundle,
    provider_config: ModelProviderConfig,
) -> RenderedPrompt:
    spec = get_prompt_spec(RECOMMENDATION_PROMPT_ID)
    input_payload = {
        "symbol": signals.symbol,
        "as_of": signals.as_of.isoformat(),
        "signals": [
            {
                "name": signal.name,
                "direction": signal.direction,
                "strength": signal.strength,
            }
            for signal in signals.signals
        ],
        "advisory_boundary": {
            "order_allowed": False,
            "human_required": True,
            "risk_limits_mutable_by_model": False,
            "raw_text_allowed": False,
        },
    }
    input_json = json.dumps(input_payload, ensure_ascii=False, sort_keys=True)
    rendered_prompt = spec.template.format(input_json=input_json)
    if len(rendered_prompt) > provider_config.max_prompt_chars:
        raise ValueError("rendered prompt exceeds model_provider.max_prompt_chars")
    return RenderedPrompt(
        prompt_id=spec.prompt_id,
        prompt_version=spec.version,
        provider=provider_config.provider,
        model_name=provider_config.model_name,
        input_hash=stable_hash(input_payload),
        prompt_hash=stable_hash(rendered_prompt),
        output_schema=spec.output_schema,
        rendered_prompt=rendered_prompt,
        created_at=signals.as_of,
    )
