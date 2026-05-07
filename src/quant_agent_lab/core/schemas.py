from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Action(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REVIEW_REQUIRED = "review_required"
    NO_TRADE = "no_trade"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"


class DataQuality(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class ModelDisagreement(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Bar(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    timeframe: Literal["1h", "1d"]
    ts: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    source: str = "mock"
    evidence_id: str

    @model_validator(mode="after")
    def validate_prices(self) -> "Bar":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high must be >= open, close and low")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low must be <= open, close and high")
        return self


class PortfolioSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: datetime
    base_currency: str = "USDT"
    equity: float = Field(gt=0)
    cash: float = Field(ge=0)
    positions: dict[str, float] = Field(default_factory=dict)
    source: str = "mock"
    evidence_id: str


class NewsEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str
    published_at: datetime
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    entities: list[str] = Field(default_factory=list)
    market_relevance: float = Field(ge=0, le=1)
    url: str | None = None
    content_hash: str
    evidence_id: str

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class CleanedTextEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    source: str
    published_at: datetime
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    entities: list[str] = Field(default_factory=list)
    market_relevance: float = Field(ge=0, le=1)
    url: str | None = None
    content_hash: str

    @classmethod
    def from_news_event(cls, event: NewsEvent) -> "CleanedTextEvidence":
        return cls(**event.model_dump())

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("published_at must be timezone-aware")
        return value.astimezone(timezone.utc)


class MarketSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    as_of: datetime
    bars_1h: list[Bar]
    bars_1d: list[Bar]
    portfolio: PortfolioSnapshot

    @field_validator("bars_1h", "bars_1d")
    @classmethod
    def require_bars(cls, bars: list[Bar]) -> list[Bar]:
        if not bars:
            raise ValueError("bars cannot be empty")
        return bars

    @property
    def evidence_ids(self) -> list[str]:
        ids = [bar.evidence_id for bar in self.bars_1h + self.bars_1d]
        ids.append(self.portfolio.evidence_id)
        return sorted(set(ids))


class DataValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: GateStatus
    data_quality: DataQuality
    reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Signal(BaseModel):
    model_config = ConfigDict(frozen=True)

    signal_id: str
    symbol: str
    name: str
    direction: Literal["bullish", "bearish", "neutral"]
    strength: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    generated_at: datetime
    details: dict[str, float | str] = Field(default_factory=dict)


class SignalBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    as_of: datetime
    signals: list[Signal]

    @property
    def evidence_ids(self) -> list[str]:
        ids: list[str] = []
        for signal in self.signals:
            ids.extend(signal.evidence_ids)
            ids.append(signal.signal_id)
        return sorted(set(ids))


class AgentOpinion(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_name: str
    status: GateStatus
    action_bias: Action
    confidence: float = Field(ge=0, le=1)
    rationale: list[str]
    risk_flags: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    generated_at: datetime


class RecommendationDraft(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendation_id: str
    symbol: str
    action: Action
    target_position_pct: float = Field(ge=0, le=1)
    max_loss_budget_pct: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str]
    data_quality: DataQuality
    model_disagreement: ModelDisagreement
    rationale: list[str]
    risk_flags: list[str] = Field(default_factory=list)
    human_required: bool = True
    order_allowed: bool = False
    generated_at: datetime

    @model_validator(mode="after")
    def advisory_only(self) -> "RecommendationDraft":
        if self.order_allowed:
            raise ValueError("Phase 1 recommendation drafts cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 1 recommendation drafts must require human approval")
        if self.action in {Action.HOLD, Action.REVIEW_REQUIRED, Action.NO_TRADE, Action.INSUFFICIENT_EVIDENCE}:
            if self.target_position_pct != 0:
                raise ValueError("non-trading actions must have zero target_position_pct")
        return self


class RiskDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: GateStatus
    final_action: Action
    order_allowed: bool = False
    reasons: list[str] = Field(default_factory=list)
    risk_metrics: dict[str, float] = Field(default_factory=dict)
    checked_at: datetime

    @model_validator(mode="after")
    def never_allow_orders_in_phase1(self) -> "RiskDecision":
        if self.order_allowed:
            raise ValueError("Phase 1 risk gate cannot allow orders")
        return self


class AdvisoryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    symbol: str
    as_of: datetime
    market: MarketSnapshot
    data_validation: DataValidationResult
    signals: SignalBundle
    agent_opinions: list[AgentOpinion]
    recommendation: RecommendationDraft
    risk_decision: RiskDecision
    report_markdown: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)
