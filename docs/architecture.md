# Architecture Notes

## Design Position

Most serious quant teams do not run several trading frameworks side by side in
production. They choose one execution and event runtime, then absorb design
patterns from other systems. That is the right bias here.

The reason is operational: order lifecycle, portfolio state, clock semantics,
replay determinism, risk checks, and broker adapters need one source of truth.
Multiple runtimes create mismatched state and hard-to-debug behavior.

## Proposed Layers

```text
market/news/macro/on-chain data
          |
          v
Data Normalization Layer
          |
          v
Event Bus / Event Store
          |
          +--> Strategy Engine
          |        |
          |        v
          |   Candidate Signals
          |
          +--> LLM Research Layer
          |        |
          |        +--> Gemini: long-context historical and cross-market memory
          |        +--> GPT: decision synthesis and structured action proposal
          |        +--> Claude: critique, scenario analysis, and risk narrative
          |
          v
Decision Committee
          |
          v
Risk Gate
          |
          v
Daily Human Approval Report
```

## Agent Responsibilities

The models should not directly place orders.

- **Gemini long context:** summarize historical regimes, recurring patterns,
  prior decisions, long event timelines, and cross-market memory.
- **GPT decision agent:** convert model and strategy inputs into a structured
  recommendation such as buy/sell/hold, target size, confidence, and invalidation
  conditions.
- **Claude analysis agent:** produce adversarial review, downside scenarios,
  missing evidence, and narrative explanation for human readers.

The final output should be a typed object, not only prose. Example fields:

```json
{
  "symbol": "BTC-USDT",
  "action": "hold",
  "confidence": 0.62,
  "max_position_pct": 0.0,
  "rationale": ["trend mixed", "macro event risk elevated"],
  "invalidation": ["daily close above X", "funding normalizes"],
  "risk_flags": ["high_volatility", "event_risk"],
  "human_required": true
}
```

## Non-Negotiable Boundaries

- Risk rules are deterministic code, not model suggestions.
- Every model input and output should be stored for audit.
- Any natural-language recommendation must be backed by structured fields.
- Backtests must use frozen model outputs or deterministic mock agents.
- Human approval remains the last mile before trading.

## Framework Selection Criteria

Choose the base engine by the first real deployment target:

| Target | Recommended base |
| --- | --- |
| Production multi-asset, low-latency, serious execution | NautilusTrader |
| Python-first research and faster prototype | aat |
| A-share / Chinese futures workflow | QUANTAXIS |
| Lightweight async market-making prototype | alphahunter or aioquant |

## Suggested First Milestone

Build a minimal daily advisory loop before any live trading:

1. Ingest one market, such as BTC/USDT daily and hourly bars.
2. Add a simple deterministic strategy signal.
3. Add mock model agents that return fixed structured opinions.
4. Aggregate opinions into one recommendation object.
5. Apply risk limits.
6. Generate a Markdown daily report.

After this works end to end, replace mock agents with real model API calls.
