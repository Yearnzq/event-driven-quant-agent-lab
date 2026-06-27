from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from quant_agent_lab.agents.base import TypedAgent
from quant_agent_lab.core.schemas import (
    A2AAgentCard,
    A2AAgentRequest,
    A2AAgentResponse,
    A2ATraceRecord,
    Action,
    AgentOpinion,
    GateStatus,
    MarketSnapshot,
    SignalBundle,
)
from quant_agent_lab.core.events import run_id as advisory_run_id
from quant_agent_lab.data.audit import stable_hash


DelayFn = Callable[[float], None]


def _no_delay(_: float) -> None:
    return None


def _redact_a2a_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: redacted"


def _failed_opinion(agent_name: str, signals: SignalBundle, error_message: str) -> AgentOpinion:
    return AgentOpinion(
        agent_name=agent_name,
        status=GateStatus.FAIL,
        action_bias=Action.INSUFFICIENT_EVIDENCE,
        confidence=0.0,
        rationale=["A2A agent call failed; degraded to insufficient evidence"],
        risk_flags=["a2a_agent_failed"],
        evidence_ids=signals.evidence_ids,
        error_message=error_message,
        generated_at=signals.as_of,
    )


class MockA2AAgentServer:
    def __init__(
        self,
        agent: TypedAgent,
        *,
        agent_id: str | None = None,
        response_delay_seconds: float = 0.0,
        delay_fn: DelayFn = _no_delay,
    ) -> None:
        self.agent = agent
        self.agent_id = agent_id or getattr(agent, "name", agent.__class__.__name__)
        self.response_delay_seconds = response_delay_seconds
        self.delay_fn = delay_fn

    def agent_card(self, *, timeout_seconds: float = 5.0, max_retries: int = 1) -> A2AAgentCard:
        return A2AAgentCard(
            agent_id=self.agent_id,
            name=getattr(self.agent, "name", self.agent_id),
            description="Local mock A2A advisory agent endpoint for Phase 9 boundary checks.",
            capabilities=[
                "schema_validated_agent_opinion",
                "trace_id_echo",
                "advisory_only",
                "no_order_creation",
            ],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

    def handle(self, request: A2AAgentRequest) -> A2AAgentResponse:
        if self.response_delay_seconds > 0:
            self.delay_fn(self.response_delay_seconds)
        if request.agent_id != self.agent_id:
            raise ValueError("A2A request agent_id does not match server agent")
        try:
            opinion = self.agent.run(request.market, request.signals)
            status = opinion.status
            error_message = opinion.error_message
        except Exception as exc:  # noqa: BLE001 - service boundary must fail closed.
            error_message = _redact_a2a_error(exc)
            opinion = _failed_opinion(self.agent_id, request.signals, error_message)
            status = GateStatus.FAIL
        latency_ms = round(self.response_delay_seconds * 1000, 3)
        return A2AAgentResponse(
            trace_id=request.trace_id,
            agent_id=self.agent_id,
            status=status,
            opinion=opinion,
            latency_ms=latency_ms,
            attempt_count=1,
            error_message=error_message,
            received_at=request.created_at,
        )


class A2AClient:
    def __init__(
        self,
        server: MockA2AAgentServer,
        *,
        timeout_seconds: float = 5.0,
        max_retries: int = 1,
    ) -> None:
        self.server = server
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    def agent_card(self) -> A2AAgentCard:
        return self.server.agent_card(
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
        )

    def invoke(
        self,
        *,
        run_id: str,
        market: MarketSnapshot,
        signals: SignalBundle,
    ) -> tuple[AgentOpinion, A2ATraceRecord]:
        trace_id = f"trace-{uuid4().hex}"
        request = A2AAgentRequest(
            trace_id=trace_id,
            run_id=run_id,
            agent_id=self.server.agent_id,
            market_hash=stable_hash(market.model_dump(mode="json")),
            signal_hash=stable_hash(signals.model_dump(mode="json")),
            market=market,
            signals=signals,
            created_at=signals.as_of,
        )
        request_hash = stable_hash(request.model_dump(mode="json"))
        response: A2AAgentResponse | None = None
        error_message: str | None = None
        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                if self.server.response_delay_seconds > self.timeout_seconds:
                    raise TimeoutError("A2A mock response exceeded deterministic timeout")
                response = self.server.handle(request)
                response = response.model_copy(update={"attempt_count": attempt})
                error_message = response.error_message
                break
            except Exception as exc:  # noqa: BLE001 - boundary errors are recorded and retried.
                error_message = _redact_a2a_error(exc)

        latency_ms = response.latency_ms if response is not None else round(attempts * self.timeout_seconds * 1000, 3)
        if response is None:
            opinion = _failed_opinion(self.server.agent_id, signals, error_message or "TimeoutError: redacted")
            response = A2AAgentResponse(
                trace_id=trace_id,
                agent_id=self.server.agent_id,
                status=GateStatus.FAIL,
                opinion=opinion,
                latency_ms=latency_ms,
                attempt_count=attempts,
                error_message=opinion.error_message,
                received_at=signals.as_of,
            )
        trace = A2ATraceRecord(
            trace_id=trace_id,
            run_id=run_id,
            agent_id=self.server.agent_id,
            status=response.status,
            attempt_count=response.attempt_count,
            timeout_seconds=self.timeout_seconds,
            latency_ms=latency_ms,
            request_hash=request_hash,
            response_hash=stable_hash(response.model_dump(mode="json")),
            error_message=response.error_message,
            created_at=request.created_at,
        )
        return response.opinion, trace


class A2AClientAgent:
    def __init__(self, client: A2AClient) -> None:
        self.client = client
        self.agent_card = client.agent_card()
        self.name = f"a2a_client:{self.agent_card.agent_id}"
        self.last_a2a_trace_record: A2ATraceRecord | None = None

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        run_id = advisory_run_id(market.symbol, market.as_of)
        opinion, trace = self.client.invoke(run_id=run_id, market=market, signals=signals)
        self.last_a2a_trace_record = trace
        return opinion.model_copy(update={"agent_name": self.name})
