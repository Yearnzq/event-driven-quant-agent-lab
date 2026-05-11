# Phase 6 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 7（模型接入边界准备），但仍不得接真实模型或自动下单。
- 审查发现：未发现阻塞性问题。

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

## 6. 已运行命令

优先按 `AGENTS.md` 尝试 `conda activate quant`，但当前容器不存在 `quant` 环境：

```bash
docker exec quant-agent-lab bash -lc '
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant
'
```

结果：

```text
EnvironmentNameNotFound: Could not find conda environment: quant
```

实际使用容器中存在的 `medi` 环境完成同一组离线验证：

```bash
docker exec quant-agent-lab bash -lc '
set -euo pipefail
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate medi

python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase6-review-20260507
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase6-review-20260507
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase6-review-20260507
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase6-review-20260507
python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-phase6-review-20260507
python scripts/stage_06_gate.py --output-dir /tmp/qal-stage-06-phase6-review-20260507
'
```

## 7. 验证结果

- Python：`Python 3.10.20`
- pytest：`46 passed in 0.78s`
- compileall：`python -m compileall -q src` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-phase6-review-20260507`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-phase6-review-20260507`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-phase6-review-20260507`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-04-phase6-review-20260507`
- Phase 5 gate：`STAGE_05_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-05-phase6-review-20260507`
- Phase 6 gate：`STAGE_06_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-06-phase6-review-20260507`
- Stage 6 gate 明细：
  - `AGENT_FAILURE_DEGRADATION_CHECK=PASS`
  - `DISAGREEMENT_EXPLANATION_CHECK=PASS`
  - `NO_TRADE_DECISION_CHECK=PASS`
  - `INSUFFICIENT_EVIDENCE_FALLBACK_CHECK=PASS`
  - `DECISION_TRACE_AUDIT_CHECK=PASS`
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `HUMAN_REQUIRED=true`

Stage 6 审查产物路径：

```text
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/artifact-catalog.json
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/audit-log.jsonl
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/run-btc-usdt-20260429t000000z.audit.json
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/run-btc-usdt-20260429t000000z.json
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/run-btc-usdt-20260429t000000z.md
/tmp/qal-stage-06-phase6-review-20260507/reports/agent_failure/run-manifest.json
```

## 8. 审查发现

未发现阻塞性问题。

已重点核对：

- agent exception 被降级为 schema-valid `AgentOpinion(status=fail)`，pipeline 不崩溃。
- 全部 agent 失败时 recommendation 为 `insufficient_evidence`，confidence 为 0。
- 方向冲突时 recommendation 为 `review_required`，decision trace 记录 `conflicting_directional_actions`。
- no-trade 路径保持 `target_position_pct=0`。
- Markdown report 和 result JSON 均包含 `decision_trace`。
- run manifest / artifact catalog 校验通过。

## 9. 边界确认

- no real model call：通过，仍为 deterministic mock agent。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：由 schema、risk gate 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。
- LLM cannot modify risk params：通过，Phase 6 未引入模型调用或风控参数写入路径。

额外边界搜索结果：

- `order_allowed=true` 只出现在负向 schema 测试、stage gate 禁止断言和文档禁用说明中。
- `raw_content` / HTML 只出现在文本清洗负向测试和 Stage 1 gate 输入样例中，清洗输出禁止泄漏。
- A2A、NautilusTrader、broker、secret、paper trading 只出现在路线/边界文档中，未出现在 Phase 6 运行路径。

## 10. 审查后修正

- `AgentOpinion.error_message` 不再写入 exception 原文，改为 `ExceptionType: redacted`，避免未来 provider 异常携带 prompt、原文或 secret 时进入报告/JSON。
- `stage_06_gate.py` 增加 `AGENT_ERROR_REDACTION_CHECK=PASS`。
- `AGENTS.md` 和 repo-local skills 的 conda 激活命令改为优先 `quant`、否则回落 `medi`，匹配当前容器实际环境。

## 11. 剩余风险

- 当前 agent 仍是 deterministic mock，不代表真实模型输出质量。
- 分歧解释是规则化 committee trace，不是自然语言推理质量评估。
- Phase 7 需要先建立 provider config、prompt registry、结构化输出和调用审计，再考虑真实模型接入。
- 历史阶段 review 文档仍保留当时的 `quant` 环境命令；当前规范以 `AGENTS.md` 和 repo-local skills 的兼容激活命令为准。
