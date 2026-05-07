# Claude Code Escalation Context

Claude Code is an escalation reviewer/worker for this repository, not the
default executor.

Use Claude Code for tasks that need deeper reasoning than a normal deterministic
Codex patch:

- Risk rule redesign.
- Walk-forward or backtest correctness review.
- Look-ahead bias and data leakage analysis.
- Real model agent boundary design.
- NautilusTrader adapter review.
- Complex multi-module root cause analysis.
- High-risk PR review where correctness, reproducibility, or safety is unclear.

Do not use Claude Code to bypass repository gates. Completion still requires the
same evidence as Codex work:

- Tests.
- `compileall`.
- Stage gate output.
- Artifact paths.
- Boundary confirmation.

Important repository boundaries:

- This is advisory-only in Phase 1.
- `order_allowed` must remain `false`.
- `human_required` must remain `true`.
- LLM output cannot control position sizing, risk limits, orders, broker state, or
  account state.
- Raw news, web pages, social media text, and comments must be cleaned before any
  agent sees them.

When reviewing, lead with concrete blockers and risks. Pay special attention to:

- Data Gate behavior when evidence is stale, missing, unsorted, duplicated, or
  inconsistent.
- Risk Gate behavior when draft actions are directional, high disagreement exists,
  volatility is high, cash is low, or existing position exceeds limits.
- Any path that changes `order_allowed`, `human_required`, `target_position_pct`,
  `max_loss_budget_pct`, or model disagreement handling.
- Audit record stability: `input_hash`, `output_hash`, schema version, model
  metadata, and artifact paths.
- Research code that could accidentally become deployable or trade-like.
