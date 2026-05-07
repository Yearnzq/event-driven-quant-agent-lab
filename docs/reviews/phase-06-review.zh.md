# Phase 6 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 7（模型接入边界准备），但仍不得接真实模型或自动下单。

## 2. 本阶段范围

Phase 6 聚焦 Advisory 决策层增强：

- agent 运行失败降级为 `AgentOpinion(status=fail)`。
- committee 输出 `phase6.decision_trace.v1`。
- 强方向冲突进入 `review_required`。
- 全部 agent 失败进入 `insufficient_evidence`。
- 单一 no-trade agent 保持 `no_trade` 且目标仓位为 0。
- Daily report 和 result JSON 写入 decision trace。

未引入真实模型、A2A、NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 3. 修改文件

- `README.md`
- `docs/stage-06-review-checklist.zh.md`
- `docs/reviews/phase-06-review.zh.md`
- `scripts/stage_06_gate.py`
- `src/quant_agent_lab/agents/mock.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/core/schemas.py`
- `src/quant_agent_lab/decision/committee.py`
- `src/quant_agent_lab/reports/daily.py`
- `tests/test_decision_phase6.py`

## 4. 新增或扩展的 schema

- `AgentOpinion.error_message`
- `DecisionTrace`
  - `schema_version="phase6.decision_trace.v1"`
  - `opinion_count`
  - `passed_agent_count`
  - `failed_agent_count`
  - `action_vote_counts`
  - `disagreement_reasons`
  - `fallback_reasons`
- `RecommendationDraft.decision_trace`

## 5. 新增用户可运行命令

```bash
python scripts/stage_06_gate.py
```

## 6. 验证结果

本阶段验证命令：

```bash
python -m pytest -q
python scripts/stage_01_gate.py
python scripts/stage_02_gate.py
python scripts/stage_03_gate.py
python scripts/stage_04_gate.py
python scripts/stage_05_gate.py
python scripts/stage_06_gate.py
```

预期 Stage 6 gate 明细：

- `AGENT_FAILURE_DEGRADATION_CHECK=PASS`
- `DISAGREEMENT_EXPLANATION_CHECK=PASS`
- `NO_TRADE_DECISION_CHECK=PASS`
- `INSUFFICIENT_EVIDENCE_FALLBACK_CHECK=PASS`
- `DECISION_TRACE_AUDIT_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 7. 边界确认

- no real model call：通过，仍为 deterministic mock agent。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：由 schema、risk gate 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。
- LLM cannot modify risk params：通过，Phase 6 未引入模型调用或风控参数写入路径。

## 8. 剩余风险

- 当前 agent 仍是 deterministic mock，不代表真实模型输出质量。
- 分歧解释是规则化 committee trace，不是自然语言推理质量评估。
- Phase 7 需要先建立 provider config、prompt registry、结构化输出和调用审计，再考虑真实模型接入。
