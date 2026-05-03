from __future__ import annotations

from quant_agent_lab.core.schemas import (
    Action,
    DataQuality,
    GateStatus,
    MarketSnapshot,
    RecommendationDraft,
    RiskDecision,
    SignalBundle,
)


class RiskGate:
    def __init__(
        self,
        max_position_pct: float = 0.10,
        max_loss_budget_pct: float = 0.02,
        max_existing_position_pct: float = 0.25,
        min_cash_pct: float = 0.05,
        max_hourly_return_vol: float = 0.03,
    ) -> None:
        self.max_position_pct = max_position_pct
        self.max_loss_budget_pct = max_loss_budget_pct
        self.max_existing_position_pct = max_existing_position_pct
        self.min_cash_pct = min_cash_pct
        self.max_hourly_return_vol = max_hourly_return_vol

    def evaluate(
        self,
        draft: RecommendationDraft,
        *,
        market: MarketSnapshot | None = None,
        signals: SignalBundle | None = None,
    ) -> RiskDecision:
        reasons: list[str] = []
        final_action = draft.action

        if draft.data_quality != DataQuality.PASS:
            reasons.append("data quality is not pass")
        if draft.order_allowed:
            reasons.append("orders are not allowed in phase 1")
        if draft.target_position_pct > self.max_position_pct:
            reasons.append("target_position_pct exceeds limit")
        if draft.max_loss_budget_pct > self.max_loss_budget_pct:
            reasons.append("max_loss_budget_pct exceeds limit")
        if draft.action in {Action.BUY, Action.SELL} and draft.model_disagreement.value == "high":
            reasons.append("high model disagreement blocks directional action")
        if draft.action == Action.INSUFFICIENT_EVIDENCE:
            reasons.append("insufficient evidence blocks trading")
        if draft.action == Action.REVIEW_REQUIRED:
            reasons.append("review required blocks trading")

        if market is not None:
            current_position_pct = abs(market.portfolio.positions.get(draft.symbol, 0.0))
            if current_position_pct > self.max_existing_position_pct:
                reasons.append("existing position exceeds limit")
            cash_pct = market.portfolio.cash / market.portfolio.equity
            if cash_pct < self.min_cash_pct:
                reasons.append("cash buffer is below minimum")

        if signals is not None:
            volatility = next((signal for signal in signals.signals if signal.name == "volatility"), None)
            if volatility is not None:
                hourly_vol = float(volatility.details.get("hourly_return_vol", 0.0))
                if hourly_vol > self.max_hourly_return_vol:
                    reasons.append("hourly return volatility exceeds limit")

        if reasons:
            status = GateStatus.FAIL
            if draft.action == Action.INSUFFICIENT_EVIDENCE:
                final_action = Action.INSUFFICIENT_EVIDENCE
            elif draft.action == Action.REVIEW_REQUIRED:
                final_action = Action.REVIEW_REQUIRED
            else:
                final_action = Action.NO_TRADE
        else:
            status = GateStatus.PASS
            if draft.action in {Action.BUY, Action.SELL}:
                reasons.append("phase 1 advisory only; no order will be created")
                final_action = Action.REVIEW_REQUIRED

        return RiskDecision(
            status=status,
            final_action=final_action,
            order_allowed=False,
            reasons=reasons,
            checked_at=draft.generated_at,
        )
