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
    error_message: str | None = None
    generated_at: datetime


class DecisionTrace(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase6.decision_trace.v1"] = "phase6.decision_trace.v1"
    opinion_count: int = Field(ge=0)
    passed_agent_count: int = Field(ge=0)
    failed_agent_count: int = Field(ge=0)
    action_vote_counts: dict[str, int] = Field(default_factory=dict)
    disagreement_reasons: list[str] = Field(default_factory=list)
    fallback_reasons: list[str] = Field(default_factory=list)


class PromptSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase7.prompt_spec.v1"] = "phase7.prompt_spec.v1"
    prompt_id: str
    version: str
    purpose: str
    template: str
    input_contract: list[str] = Field(default_factory=list)
    output_schema: str
    advisory_only: bool = True


class RenderedPrompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase7.rendered_prompt.v1"] = "phase7.rendered_prompt.v1"
    prompt_id: str
    prompt_version: str
    provider: Literal["fake", "openai", "codex"]
    model_name: str
    input_hash: str
    prompt_hash: str
    output_schema: str
    rendered_prompt: str
    created_at: datetime


class ModelCallAuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase7.model_call_audit.v1"] = "phase7.model_call_audit.v1"
    provider: Literal["fake", "openai", "codex"]
    model_name: str
    prompt_id: str
    prompt_version: str
    input_hash: str
    prompt_hash: str
    output_hash: str
    output_schema: str
    status: GateStatus
    latency_ms: float = Field(ge=0)
    estimated_input_tokens: int = Field(ge=0)
    estimated_output_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)
    error_message: str | None = None
    order_allowed: bool = False
    human_required: bool = True
    called_at: datetime

    @model_validator(mode="after")
    def advisory_only(self) -> "ModelCallAuditRecord":
        if self.order_allowed:
            raise ValueError("Phase 7 model call audit cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 7 model call audit must require human approval")
        return self


class ModelBoundaryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase7.model_boundary_result.v1"] = "phase7.model_boundary_result.v1"
    opinion: AgentOpinion
    audit_record: ModelCallAuditRecord
    prompt_registry: list[PromptSpec]


class A2AAgentCard(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase9.agent_card.v1"] = "phase9.agent_card.v1"
    agent_id: str
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    endpoint_path: str = "/a2a/agent-opinion"
    input_schema: str = "phase9.agent_request.v1"
    output_schema: str = "AgentOpinion"
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_retries: int = Field(default=1, ge=0, le=5)
    advisory_only: bool = True
    order_allowed: bool = False
    human_required: bool = True

    @model_validator(mode="after")
    def advisory_only_card(self) -> "A2AAgentCard":
        if not self.advisory_only:
            raise ValueError("Phase 9 agent card must be advisory-only")
        if self.order_allowed:
            raise ValueError("Phase 9 agent card cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 9 agent card must require human approval")
        return self


class A2AAgentRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase9.agent_request.v1"] = "phase9.agent_request.v1"
    trace_id: str
    run_id: str
    agent_id: str
    market_hash: str
    signal_hash: str
    market: MarketSnapshot
    signals: SignalBundle
    created_at: datetime
    order_allowed: bool = False
    human_required: bool = True

    @model_validator(mode="after")
    def advisory_only_request(self) -> "A2AAgentRequest":
        if self.order_allowed:
            raise ValueError("Phase 9 A2A request cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 9 A2A request must require human approval")
        return self


class A2AAgentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase9.agent_response.v1"] = "phase9.agent_response.v1"
    trace_id: str
    agent_id: str
    status: GateStatus
    opinion: AgentOpinion
    latency_ms: float = Field(ge=0)
    attempt_count: int = Field(ge=1)
    error_message: str | None = None
    received_at: datetime
    order_allowed: bool = False
    human_required: bool = True

    @model_validator(mode="after")
    def advisory_only_response(self) -> "A2AAgentResponse":
        if self.order_allowed:
            raise ValueError("Phase 9 A2A response cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 9 A2A response must require human approval")
        if self.opinion.status == GateStatus.FAIL and self.opinion.action_bias != Action.INSUFFICIENT_EVIDENCE:
            raise ValueError("failed A2A responses must degrade to insufficient evidence")
        return self


class A2ATraceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: Literal["phase9.a2a_trace.v1"] = "phase9.a2a_trace.v1"
    trace_id: str
    run_id: str
    agent_id: str
    status: GateStatus
    attempt_count: int = Field(ge=1)
    timeout_seconds: float = Field(gt=0)
    latency_ms: float = Field(ge=0)
    request_hash: str
    response_hash: str
    error_message: str | None = None
    order_allowed: bool = False
    human_required: bool = True
    created_at: datetime

    @model_validator(mode="after")
    def advisory_only_trace(self) -> "A2ATraceRecord":
        if self.order_allowed:
            raise ValueError("Phase 9 A2A trace cannot allow orders")
        if not self.human_required:
            raise ValueError("Phase 9 A2A trace must require human approval")
        return self


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
    decision_trace: DecisionTrace = Field(
        default_factory=lambda: DecisionTrace(
            opinion_count=0,
            passed_agent_count=0,
            failed_agent_count=0,
        )
    )
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
    model_call_audits: list[ModelCallAuditRecord] = Field(default_factory=list)
    a2a_agent_cards: list[A2AAgentCard] = Field(default_factory=list)
    a2a_trace_records: list[A2ATraceRecord] = Field(default_factory=list)


def utc_now() -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc)
