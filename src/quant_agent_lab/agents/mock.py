from __future__ import annotations

from quant_agent_lab.core.schemas import Action, AgentOpinion, GateStatus, MarketSnapshot, SignalBundle


class MockHistoricalContextAgent:
    name = "mock_historical_context"

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        trend = next(signal for signal in signals.signals if signal.name == "trend")
        bias = Action.HOLD if trend.strength < 0.1 else Action.BUY if trend.direction == "bullish" else Action.SELL
        return AgentOpinion(
            agent_name=self.name,
            status=GateStatus.PASS,
            action_bias=bias,
            confidence=0.58,
            rationale=["historical mock context sees a mild trend regime"],
            risk_flags=[],
            evidence_ids=signals.evidence_ids,
            generated_at=market.as_of,
        )


class MockCritiqueAgent:
    name = "mock_critique"

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        volatility = next(signal for signal in signals.signals if signal.name == "volatility")
        flags = ["high_volatility"] if volatility.direction == "bearish" else []
        return AgentOpinion(
            agent_name=self.name,
            status=GateStatus.PASS,
            action_bias=Action.REVIEW_REQUIRED if flags else Action.HOLD,
            confidence=0.64,
            rationale=["critique mock requires confirmation before directional exposure"],
            risk_flags=flags,
            evidence_ids=signals.evidence_ids,
            generated_at=market.as_of,
        )


class MockRecommendationDraftAgent:
    name = "mock_recommendation_draft"

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        bullish = sum(1 for signal in signals.signals if signal.direction == "bullish")
        bearish = sum(1 for signal in signals.signals if signal.direction == "bearish")
        if bullish > bearish:
            bias = Action.BUY
        elif bearish > bullish:
            bias = Action.SELL
        else:
            bias = Action.HOLD
        return AgentOpinion(
            agent_name=self.name,
            status=GateStatus.PASS,
            action_bias=bias,
            confidence=0.61,
            rationale=["draft mock aggregates deterministic signal directions"],
            risk_flags=[],
            evidence_ids=signals.evidence_ids,
            generated_at=market.as_of,
        )


def default_mock_agents() -> list[object]:
    return [
        MockHistoricalContextAgent(),
        MockCritiqueAgent(),
        MockRecommendationDraftAgent(),
    ]
