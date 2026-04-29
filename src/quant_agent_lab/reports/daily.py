from __future__ import annotations

from quant_agent_lab.core.schemas import (
    AgentOpinion,
    DataValidationResult,
    RecommendationDraft,
    RiskDecision,
    SignalBundle,
)


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
    evidence = "\n".join(f"- `{item}`" for item in recommendation.evidence_ids[:20])
    return f"""# Daily Advisory Report

Run: `{run_id}`
Symbol: `{recommendation.symbol}`
As of: `{signals.as_of.isoformat()}`

## Data Gate

Status: `{data_validation.status}`
Quality: `{data_validation.data_quality}`
Reasons: `{data_validation.reasons or []}`

## Deterministic Signals

{signal_lines}

## Agent Opinions

{opinion_lines}

## Recommendation Draft

- Action: `{recommendation.action}`
- Target position pct: `{recommendation.target_position_pct}`
- Max loss budget pct: `{recommendation.max_loss_budget_pct}`
- Confidence: `{recommendation.confidence}`
- Model disagreement: `{recommendation.model_disagreement}`
- Human required: `{recommendation.human_required}`
- Order allowed: `{recommendation.order_allowed}`

## Risk Gate

- Status: `{risk_decision.status}`
- Final action: `{risk_decision.final_action}`
- Order allowed: `{risk_decision.order_allowed}`

Reasons:

{risk_reasons}

## Evidence

{evidence}
"""
