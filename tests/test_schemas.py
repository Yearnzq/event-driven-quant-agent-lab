from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from quant_agent_lab.core.schemas import (
    Action,
    CleanedTextEvidence,
    DataQuality,
    ModelDisagreement,
    NewsEvent,
    RecommendationDraft,
)
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


def test_news_event_requires_published_timestamp() -> None:
    with pytest.raises(ValidationError):
        NewsEvent(
            source="news",
            published_at=datetime(2026, 4, 29),
            title="Macro calendar",
            summary="A cleaned summary only.",
            market_relevance=0.4,
            content_hash="abc",
            evidence_id="news:macro:1",
        )


def test_news_event_can_be_cleaned_text_evidence() -> None:
    event = NewsEvent(
        source="news",
        published_at=datetime(2026, 4, 29, tzinfo=timezone.utc),
        title="BTC liquidity improves",
        summary="A cleaned summary without raw article body.",
        entities=["BTC", "USDT"],
        market_relevance=0.8,
        content_hash="hash",
        evidence_id="news:btc:1",
    )
    cleaned = CleanedTextEvidence.from_news_event(event)
    assert cleaned.evidence_id == event.evidence_id
    assert cleaned.summary == event.summary
