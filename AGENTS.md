# Repository Agent Instructions

## Project Mission

This repository is an event-driven quant advisory lab. It is not an automated
trading bot.

The current Phase 1 system validates a pure Python advisory loop:

```text
MarketSnapshot
  -> Data Validation Gate
  -> deterministic signals
  -> mock TypedAgents
  -> RecommendationDraft
  -> RiskGate
  -> Markdown report
  -> JSON audit records
```

The engineering truth source is the repository harness: tests, stage gates,
schemas, generated artifacts, and human review.

## Non-Negotiable Boundaries

- Do not enable automatic trading.
- Do not set `order_allowed=true` in Phase 1 artifacts, schemas, tests, or reports.
- Do not let LLMs modify risk parameters or bypass `RiskGate`.
- Do not let LLMs infer missing market data when `Data Validation Gate` fails.
- Do not feed raw news, web pages, social content, comments, or uncleaned full text
  directly into agent context.
- Do not introduce real model API calls, A2A services, NautilusTrader integration,
  paper trading, broker adapters, exchange account access, or secrets in Phase 1.
- Do not commit, push, or create PRs unless the user explicitly asks.

## Start Here

Before making changes, read the relevant context:

- `README.md`
- `docs/advisory-core-spec.zh.md`
- `docs/requirements-alignment.zh.md`
- `docs/phase1-status.zh.md`
- `docs/stage-01-review-checklist.zh.md`
- `scripts/stage_01_gate.py`

For core implementation work, inspect the matching source and tests under:

- `src/quant_agent_lab/`
- `tests/`

## Phase 1 Validation Commands

Prefer the project container because the host Python may not have the dev
dependencies installed.

```powershell
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
if conda env list | awk '{print $1}' | grep -qx quant; then
  conda activate quant
else
  conda activate medi
fi

python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py
'
```

Best-effort network checks are optional and must not block Phase 1 when the
network fails:

```powershell
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
if conda env list | awk '{print $1}' | grep -qx quant; then
  conda activate quant
else
  conda activate medi
fi

python scripts/stage_01_gate.py --try-binance
ssh -T -o BatchMode=yes git@github.com 2>&1 || true
'
```

## Completion Evidence

Do not report completion by self-assertion. Provide evidence:

- Python version used.
- Test command and result.
- Compile command and result.
- Stage gate command and result.
- Artifact paths touched or generated.
- Boundary confirmation: no real model calls, no A2A, no NautilusTrader, no paper
  trading, no auto order, `order_allowed=false`, no raw text leakage.
- Residual risks or skipped checks.

## Daily Phase Workflow

This project follows a ten-phase plan with one main phase per day. Work
autonomously within the active phase. Do not stop to ask for confirmation unless
the task would introduce a major feature, architecture change, new external
system, real model integration, trading/paper-trading behavior, write-capable
MCP, secrets, or production access.

For each phase:

1. Read the phase roadmap and current review checklist.
2. Implement the smallest scoped changes needed for that phase.
3. Run the relevant tests and stage gate.
4. Update the phase review memo under `docs/reviews/`.
5. Clean up phase-local clutter before finishing:
   - Remove scratch prompts and one-off notes.
   - Keep reusable rules in `AGENTS.md`, `CLAUDE.md`, skills, scripts, tests, or
     phase review docs.
   - Keep generated artifacts only when they are part of the review evidence.
   - Do not leave duplicate workflow docs when the same instruction already lives
     in a canonical file.
6. Leave the workspace ready for evening Claude Code review.

The intended daily loop is:

```text
Codex daytime implementation and gate evidence
  -> phase review memo
  -> Claude Code evening review for high-risk issues
  -> human decision to advance or hold the phase
```

## Skills

Use repo-local skills when they match the task:

- `.agents/skills/phase-1-gate-review` for Phase 1 readiness, gate runs, and
  review evidence.
- `.agents/skills/quant-harness-review` for code review of quant advisory harness
  changes.

## MCP Policy

Phase 1 uses no external MCP servers by default. `.mcp.json` is intentionally
empty. If an MCP server is introduced later, it must be read-only unless a
separate human approval policy explicitly allows writes.

Allowed future MCP categories:

- GitHub issues and PRs, read-only.
- CI logs, read-only.
- Internal docs or official technical docs, read-only.

Forbidden Phase 1 MCP categories:

- Exchange accounts or broker APIs.
- Production databases.
- Secret managers.
- Cloud resource mutation.
- Raw news/web/social full-text ingestion.
- Any tool that can create orders, modify risk limits, deploy, rollback, or write
  to production systems.

## Review Bias

For this project, correctness means safety, reproducibility, auditability, and
respecting advisory-only boundaries. A smaller patch with stronger evidence is
better than a broad change with unclear gates.
