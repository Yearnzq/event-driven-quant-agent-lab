from __future__ import annotations

from collections import Counter

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import (
    Action,
    AgentOpinion,
    DataQuality,
    DataValidationResult,
    GateStatus,
    ModelDisagreement,
    RecommendationDraft,
    SignalBundle,
)


TRADING_ACTIONS = {Action.BUY, Action.SELL}


def disagreement_level(opinions: list[AgentOpinion]) -> ModelDisagreement:
    actions = {opinion.action_bias for opinion in opinions}
    if not opinions:
        return ModelDisagreement.UNKNOWN
    if len(actions) == 1:
        return ModelDisagreement.LOW
    if Action.REVIEW_REQUIRED in actions or len(actions & TRADING_ACTIONS) > 1:
        return ModelDisagreement.HIGH
    return ModelDisagreement.MEDIUM


def build_recommendation_draft(
    signals: SignalBundle,
    data_validation: DataValidationResult,
    opinions: list[AgentOpinion],
) -> RecommendationDraft:
    if data_validation.status == GateStatus.FAIL:
        action = Action.INSUFFICIENT_EVIDENCE
        target_position_pct = 0.0
        rationale = ["data validation failed; system will not infer missing evidence"]
        risk_flags = data_validation.reasons
        disagreement = ModelDisagreement.UNKNOWN
    else:
        counts = Counter(opinion.action_bias for opinion in opinions)
        disagreement = disagreement_level(opinions)
        if disagreement == ModelDisagreement.HIGH:
            action = Action.REVIEW_REQUIRED
            target_position_pct = 0.0
        else:
            action = counts.most_common(1)[0][0] if counts else Action.HOLD
            if action in {Action.BUY, Action.SELL}:
                target_position_pct = 0.05
            else:
                target_position_pct = 0.0
        rationale = [item for opinion in opinions for item in opinion.rationale]
        risk_flags = sorted({flag for opinion in opinions for flag in opinion.risk_flags})

    evidence_ids = sorted(set(data_validation.evidence_ids + signals.evidence_ids + [
        opinion.agent_name for opinion in opinions
    ]))
    confidence = round(sum(opinion.confidence for opinion in opinions) / len(opinions), 4) if opinions else 0
    return RecommendationDraft(
        recommendation_id=evidence_id("recommendation", signals.symbol, signals.as_of.isoformat()),
        symbol=signals.symbol,
        action=action,
        target_position_pct=target_position_pct,
        max_loss_budget_pct=0.01 if target_position_pct else 0.0,
        confidence=confidence,
        evidence_ids=evidence_ids,
        data_quality=DataQuality.FAIL if data_validation.status == GateStatus.FAIL else DataQuality.PASS,
        model_disagreement=disagreement,
        rationale=rationale or ["no actionable rationale"],
        risk_flags=risk_flags,
        generated_at=signals.as_of,
    )
