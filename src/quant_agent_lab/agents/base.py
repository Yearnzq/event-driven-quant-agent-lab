from __future__ import annotations

from typing import Protocol

from quant_agent_lab.core.schemas import AgentOpinion, MarketSnapshot, SignalBundle


class TypedAgent(Protocol):
    name: str

    def run(self, market: MarketSnapshot, signals: SignalBundle) -> AgentOpinion:
        """Return a schema-validated advisory opinion."""
