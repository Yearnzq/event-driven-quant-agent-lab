---
name: quant-harness-review
description: Review event-driven quant advisory harness changes for safety, reproducibility, auditability, data leakage, advisory-only boundaries, Data Gate behavior, Risk Gate behavior, report integrity, and test coverage. Use for PR/code review, pre-merge checks, or high-risk changes in src, tests, scripts, docs, or artifacts.
---

# Quant Harness Review

## Overview

Use this skill to review changes to the quant advisory harness. Lead with
blockers and behavioral risks. Treat the repository gates and tests as the
completion source of truth.

## Review Checklist

Check these areas first:

- Advisory boundary:
  - `order_allowed` remains `false`.
  - `human_required` remains `true`.
  - No order, broker, exchange account, paper trading, or live trading behavior is introduced.
- Data Gate:
  - Missing, stale, unsorted, duplicated, or gapped bars fail safely.
  - Portfolio timestamp mismatches are rejected.
  - Evidence ids remain traceable.
- Text evidence:
  - Raw `content`, `raw_content`, HTML, social comments, and web/news full text do not enter agent context.
  - Cleaned evidence keeps source, timestamp, title, summary, entities, relevance, URL, hash, and evidence id.
- Risk Gate:
  - High disagreement blocks directional action.
  - High volatility, low cash, excessive existing position, or insufficient evidence blocks trading.
  - LLM confidence is never used as position size.
  - Risk limits are deterministic code and covered by tests.
- Audit:
  - Input and output hashes are stable.
  - Artifacts are written to expected paths.
  - Model metadata remains explicit, even for mock agents.
- Research:
  - Signal evaluation is marked research-only.
  - No result is described as deployable.
  - No test-set tuning, look-ahead bias, or data leakage is introduced.
- Tests and gates:
  - Relevant tests exist for changed behavior.
  - `pytest`, `compileall`, and stage gate are run when appropriate.

## Commands

For Phase 1 review, prefer:

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

## Escalate

Recommend Claude Code or deeper human review when changes touch:

- Risk rule semantics.
- Future real model integration.
- Backtest or walk-forward logic.
- NautilusTrader adapter boundaries.
- Any behavior that might evolve toward paper/live trading.

## Output Format

Use code-review style when reviewing a diff:

```text
Findings:
- [P1/P2/P3] file:line - issue and impact

Open questions:
- ...

Verification:
- commands run and results

Residual risk:
- ...
```

If there are no findings, say so clearly and still report any test gaps or
residual risk.
