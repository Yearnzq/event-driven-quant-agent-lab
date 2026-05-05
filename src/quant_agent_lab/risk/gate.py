from __future__ import annotations

from math import sqrt
from statistics import pstdev

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
        max_recent_drawdown_pct: float = 0.12,
        max_downside_volatility: float = 0.025,
        max_single_hour_loss_pct: float = 0.08,
        max_portfolio_risk_budget_pct: float = 0.01,
    ) -> None:
        self.max_position_pct = max_position_pct
        self.max_loss_budget_pct = max_loss_budget_pct
        self.max_existing_position_pct = max_existing_position_pct
        self.min_cash_pct = min_cash_pct
        self.max_hourly_return_vol = max_hourly_return_vol
        self.max_recent_drawdown_pct = max_recent_drawdown_pct
        self.max_downside_volatility = max_downside_volatility
        self.max_single_hour_loss_pct = max_single_hour_loss_pct
        self.max_portfolio_risk_budget_pct = max_portfolio_risk_budget_pct

    @staticmethod
    def _returns(closes: list[float]) -> list[float]:
        return [(right / left) - 1 for left, right in zip(closes, closes[1:]) if left > 0]

    @staticmethod
    def _max_drawdown(closes: list[float]) -> float:
        peak = closes[0] if closes else 0.0
        max_drawdown = 0.0
        for close in closes:
            peak = max(peak, close)
            if peak:
                max_drawdown = max(max_drawdown, (peak - close) / peak)
        return max_drawdown

    @staticmethod
    def _downside_volatility(returns: list[float]) -> float:
        downside = [min(value, 0.0) for value in returns]
        if not downside:
            return 0.0
        return sqrt(sum(value * value for value in downside) / len(downside))

    def evaluate(
        self,
        draft: RecommendationDraft,
        *,
        market: MarketSnapshot | None = None,
        signals: SignalBundle | None = None,
    ) -> RiskDecision:
        reasons: list[str] = []
        risk_metrics: dict[str, float] = {}
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
            risk_metrics["existing_position_pct"] = round(current_position_pct, 8)
            if current_position_pct > self.max_existing_position_pct:
                reasons.append("existing position exceeds limit")
            cash_pct = market.portfolio.cash / market.portfolio.equity
            risk_metrics["cash_pct"] = round(cash_pct, 8)
            if cash_pct < self.min_cash_pct:
                reasons.append("cash buffer is below minimum")
            hourly_closes = [bar.close for bar in market.bars_1h]
            hourly_returns = self._returns(hourly_closes)
            if hourly_returns:
                recent_drawdown = self._max_drawdown(hourly_closes)
                downside_volatility = self._downside_volatility(hourly_returns)
                worst_hourly_return = min(hourly_returns)
                portfolio_risk_budget = current_position_pct * (pstdev(hourly_returns) if len(hourly_returns) > 1 else 0.0)
                risk_metrics["recent_drawdown_pct"] = round(recent_drawdown, 8)
                risk_metrics["downside_volatility"] = round(downside_volatility, 8)
                risk_metrics["worst_hourly_return"] = round(worst_hourly_return, 8)
                risk_metrics["portfolio_risk_budget_pct"] = round(portfolio_risk_budget, 8)
                if recent_drawdown > self.max_recent_drawdown_pct:
                    reasons.append("recent drawdown exceeds limit")
                if downside_volatility > self.max_downside_volatility:
                    reasons.append("downside volatility exceeds limit")
                if abs(min(worst_hourly_return, 0.0)) > self.max_single_hour_loss_pct:
                    reasons.append("single hour loss exceeds limit")
                if portfolio_risk_budget > self.max_portfolio_risk_budget_pct:
                    reasons.append("portfolio risk budget exceeds limit")

        if signals is not None:
            volatility = next((signal for signal in signals.signals if signal.name == "volatility"), None)
            if volatility is not None:
                hourly_vol = float(volatility.details.get("hourly_return_vol", 0.0))
                risk_metrics["hourly_return_vol"] = round(hourly_vol, 8)
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
            risk_metrics=risk_metrics,
            checked_at=draft.generated_at,
        )
