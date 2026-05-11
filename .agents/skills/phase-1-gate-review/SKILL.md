---
name: phase-1-gate-review
description: Run and document Phase 1 readiness checks for the event-driven quant advisory lab. Use when asked to review Phase 1, run the offline gate, verify advisory-only boundaries, fill a phase review memo, or decide whether the project can proceed to Phase 2.
---

# Phase 1 Gate Review

## Overview

Use this skill to verify the Phase 1 engineering baseline. The goal is not to
prove trading performance; it is to prove that the offline advisory core is
reproducible, auditable, and still constrained to decision support.

## Required Context

Read these files before judging the phase:

- `AGENTS.md`
- `README.md`
- `docs/advisory-core-spec.zh.md`
- `docs/requirements-alignment.zh.md`
- `docs/phase1-status.zh.md`
- `docs/stage-01-review-checklist.zh.md`
- `scripts/stage_01_gate.py`

## Workflow

1. Check current git status and note whether unrelated changes already exist.
2. Run the Phase 1 offline validation in the container:

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

3. Only run the best-effort network gate when explicitly requested:

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

4. Inspect generated artifacts when needed:
   - reports
   - research
   - evidence
   - audit
5. Verify boundary statements in reports and JSON artifacts:
   - advisory-only wording exists.
   - `order_allowed=true` does not appear.
   - cleaned text evidence does not leak `content`, `raw_content`, or HTML.
6. Fill or summarize `docs/reviews/phase-01-review.zh.md` if the user asks for a
   review artifact.

## Forbidden Actions

- Do not call real model APIs.
- Do not connect A2A.
- Do not connect NautilusTrader.
- Do not do paper trading.
- Do not create orders or order drafts.
- Do not read secrets.
- Do not commit or push unless explicitly requested.
- Do not treat Binance network failure as a hard Phase 1 failure.

## Evidence Required

A valid Phase 1 review must report:

- Python version.
- pytest result.
- compileall result.
- `stage_01_gate.py` result.
- Optional Binance/GitHub best-effort result if run.
- Artifact paths reviewed or generated.
- Boundary confirmation:
  - no real model calls
  - no A2A
  - no NautilusTrader
  - no paper trading
  - no auto order
  - `order_allowed=false`
  - no raw news/web body enters agent context
- Residual risks and skipped checks.

## Output Format

For a short user-facing summary:

```text
Phase 1 gate: PASS / FAIL / PASS_WITH_NETWORK_WAIVER

Evidence:
- Python:
- Tests:
- Compile:
- Offline gate:
- Network gate:
- Artifacts:

Boundary check:
- ...

Residual risk:
- ...
```
