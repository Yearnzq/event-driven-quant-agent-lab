from __future__ import annotations

import pytest
from pydantic import ValidationError

from quant_agent_lab.core.schemas import Action, DataQuality, ModelDisagreement, RecommendationDraft
from quant_agent_lab.core.schemas import utc_now


def test_recommendation_cannot_allow_orders_in_phase1() -> None:
    with pytest.raises(ValidationError):
        RecommendationDraft(
            recommendation_id="rec-1",
            symbol="BTC-USDT",
            action=Action.BUY,
            target_position_pct=0.05,
            max_loss_budget_pct=0.01,
            confidence=0.5,
            evidence_ids=["e1"],
            data_quality=DataQuality.PASS,
            model_disagreement=ModelDisagreement.LOW,
            rationale=["test"],
            order_allowed=True,
            generated_at=utc_now(),
        )


def test_hold_must_have_zero_target_position() -> None:
    with pytest.raises(ValidationError):
        RecommendationDraft(
            recommendation_id="rec-1",
            symbol="BTC-USDT",
            action=Action.HOLD,
            target_position_pct=0.05,
            max_loss_budget_pct=0.0,
            confidence=0.5,
            evidence_ids=["e1"],
            data_quality=DataQuality.PASS,
            model_disagreement=ModelDisagreement.LOW,
            rationale=["test"],
            generated_at=utc_now(),
        )
