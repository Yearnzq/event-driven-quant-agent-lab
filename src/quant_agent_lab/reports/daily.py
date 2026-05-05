from __future__ import annotations

from quant_agent_lab.core.schemas import (
    AgentOpinion,
    DataValidationResult,
    RecommendationDraft,
    RiskDecision,
    SignalBundle,
)


def _value(item: object) -> object:
    return getattr(item, "value", item)


def _interpretation(recommendation: RecommendationDraft, risk_decision: RiskDecision) -> str:
    if risk_decision.final_action.value == "insufficient_evidence":
        return "Data quality is insufficient. The system refuses to infer missing evidence."
    if risk_decision.final_action.value == "no_trade":
        return "Risk rules block this draft. No order can be created."
    if risk_decision.final_action.value == "review_required":
        return "Directional evidence exists, but Phase 1 requires human review before any action."
    if recommendation.action.value == "hold":
        return "Current evidence supports waiting rather than changing exposure."
    return "Advisory output only. Human approval and deterministic gates remain mandatory."


def render_daily_report(
    *,
    run_id: str,
    signals: SignalBundle,
    data_validation: DataValidationResult,
    opinions: list[AgentOpinion],
    recommendation: RecommendationDraft,
    risk_decision: RiskDecision,
) -> str:
    signal_lines = "\n".join(
        f"- `{signal.name}`: {signal.direction}, strength={signal.strength}"
        for signal in signals.signals
    )
    opinion_lines = "\n".join(
        f"- `{opinion.agent_name}`: {opinion.action_bias}, confidence={opinion.confidence}"
        for opinion in opinions
    )
    risk_reasons = "\n".join(f"- {reason}" for reason in risk_decision.reasons) or "- none"
    risk_metrics = (
        "\n".join(f"- `{key}`: {value}" for key, value in sorted(risk_decision.risk_metrics.items()))
        or "- none"
    )
    evidence = "\n".join(f"- `{item}`" for item in recommendation.evidence_ids[:20])
    rationale = "\n".join(f"- {item}" for item in recommendation.rationale) or "- none"
    risk_flags = "\n".join(f"- {item}" for item in recommendation.risk_flags) or "- none"
    return f"""# Daily Advisory Report

Run: `{run_id}`
Symbol: `{recommendation.symbol}`
As of: `{signals.as_of.isoformat()}`

## Data Gate

Status: `{_value(data_validation.status)}`
Quality: `{_value(data_validation.data_quality)}`
Reasons: `{data_validation.reasons or []}`

## Deterministic Signals

{signal_lines}

## Agent Opinions

{opinion_lines}

## Recommendation Draft

- Action: `{_value(recommendation.action)}`
- Target position pct: `{recommendation.target_position_pct}`
- Max loss budget pct: `{recommendation.max_loss_budget_pct}`
- Confidence: `{recommendation.confidence}`
- Data quality: `{_value(recommendation.data_quality)}`
- Model disagreement: `{_value(recommendation.model_disagreement)}`
- Human required: `{recommendation.human_required}`
- Order allowed: `{recommendation.order_allowed}`

Rationale:

{rationale}

Risk flags:

{risk_flags}

## Risk Gate

- Status: `{_value(risk_decision.status)}`
- Final action: `{_value(risk_decision.final_action)}`
- Order allowed: `{risk_decision.order_allowed}`

Reasons:

{risk_reasons}

Metrics:

{risk_metrics}

## Advisory Interpretation

{_interpretation(recommendation, risk_decision)}

## Evidence

{evidence}

Note: This report is decision support only. It is not an automated trading instruction.
"""
