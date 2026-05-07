from __future__ import annotations

from collections import Counter

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import (
    Action,
    AgentOpinion,
    DataQuality,
    DataValidationResult,
    DecisionTrace,
    GateStatus,
    ModelDisagreement,
    RecommendationDraft,
    SignalBundle,
)


TRADING_ACTIONS = {Action.BUY, Action.SELL}


def disagreement_level(opinions: list[AgentOpinion]) -> ModelDisagreement:
    if not opinions:
        return ModelDisagreement.UNKNOWN
    if any(opinion.status == GateStatus.FAIL for opinion in opinions):
        return ModelDisagreement.HIGH
    actions = {opinion.action_bias for opinion in opinions}
    if len(actions) == 1:
        return ModelDisagreement.LOW
    if Action.REVIEW_REQUIRED in actions or len(actions & TRADING_ACTIONS) > 1:
        return ModelDisagreement.HIGH
    return ModelDisagreement.MEDIUM


def _decision_trace(
    *,
    opinions: list[AgentOpinion],
    data_validation: DataValidationResult,
    disagreement: ModelDisagreement,
) -> DecisionTrace:
    vote_counts = Counter(opinion.action_bias.value for opinion in opinions)
    failed = [opinion for opinion in opinions if opinion.status == GateStatus.FAIL]
    passed = [opinion for opinion in opinions if opinion.status != GateStatus.FAIL]
    actions = {opinion.action_bias for opinion in passed}
    disagreement_reasons: list[str] = []
    fallback_reasons: list[str] = []

    if data_validation.status == GateStatus.FAIL:
        fallback_reasons.append("data_validation_failed")
    if not opinions:
        fallback_reasons.append("no_agent_opinions")
    if failed:
        fallback_reasons.extend(f"agent_failed:{opinion.agent_name}" for opinion in failed)
    if len(actions & TRADING_ACTIONS) > 1:
        disagreement_reasons.append("conflicting_directional_actions")
    if Action.REVIEW_REQUIRED in actions:
        disagreement_reasons.append("review_required_vote_present")
    if Action.NO_TRADE in actions:
        disagreement_reasons.append("no_trade_vote_present")
    if actions & TRADING_ACTIONS and Action.HOLD in actions:
        disagreement_reasons.append("directional_and_hold_votes_mixed")
    if disagreement == ModelDisagreement.HIGH and not disagreement_reasons and failed:
        disagreement_reasons.append("agent_failure_forces_high_disagreement")

    return DecisionTrace(
        opinion_count=len(opinions),
        passed_agent_count=len(passed),
        failed_agent_count=len(failed),
        action_vote_counts=dict(sorted(vote_counts.items())),
        disagreement_reasons=sorted(set(disagreement_reasons)),
        fallback_reasons=sorted(set(fallback_reasons)),
    )


def build_recommendation_draft(
    signals: SignalBundle,
    data_validation: DataValidationResult,
    opinions: list[AgentOpinion],
) -> RecommendationDraft:
    passed_opinions = [opinion for opinion in opinions if opinion.status != GateStatus.FAIL]
    failed_opinions = [opinion for opinion in opinions if opinion.status == GateStatus.FAIL]
    if data_validation.status == GateStatus.FAIL:
        action = Action.INSUFFICIENT_EVIDENCE
        target_position_pct = 0.0
        rationale = ["data validation failed; system will not infer missing evidence"]
        risk_flags = data_validation.reasons
        disagreement = ModelDisagreement.UNKNOWN
    else:
        counts = Counter(opinion.action_bias for opinion in passed_opinions)
        disagreement = disagreement_level(opinions)
        if not opinions or not passed_opinions:
            action = Action.INSUFFICIENT_EVIDENCE
            target_position_pct = 0.0
        elif failed_opinions or disagreement == ModelDisagreement.HIGH:
            action = Action.REVIEW_REQUIRED
            target_position_pct = 0.0
        else:
            action = counts.most_common(1)[0][0]
            if action in {Action.BUY, Action.SELL}:
                target_position_pct = 0.05
            else:
                target_position_pct = 0.0
        rationale = [item for opinion in opinions for item in opinion.rationale]
        risk_flags = sorted({flag for opinion in opinions for flag in opinion.risk_flags})

    trace = _decision_trace(
        opinions=opinions,
        data_validation=data_validation,
        disagreement=disagreement,
    )
    evidence_ids = sorted(
        set(
            data_validation.evidence_ids
            + signals.evidence_ids
            + [opinion.agent_name for opinion in opinions]
        )
    )
    confidence = (
        round(sum(opinion.confidence for opinion in passed_opinions) / len(passed_opinions), 4)
        if passed_opinions
        else 0
    )
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
        decision_trace=trace,
        generated_at=signals.as_of,
    )
