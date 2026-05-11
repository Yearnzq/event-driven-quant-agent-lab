# Stage 6 Review Checklist

日期：2026-05-07

## 范围

Stage 6 聚焦 Advisory 决策层增强：

- agent 失败必须降级为 schema-valid `AgentOpinion`，不能让 pipeline 崩溃。
- committee 必须给出结构化分歧解释。
- `review_required` / `no_trade` / `insufficient_evidence` 必须有可测试路径。
- 报告和 JSON 产物必须包含 decision trace。
- 继续保持 `order_allowed=false` 和 `human_required=true`。

## 必跑命令

```bash
python -m pytest -q
python scripts/stage_01_gate.py
python scripts/stage_02_gate.py
python scripts/stage_03_gate.py
python scripts/stage_04_gate.py
python scripts/stage_05_gate.py
python scripts/stage_06_gate.py
```

## 验收点

- `AGENT_FAILURE_DEGRADATION_CHECK=PASS`
- `AGENT_ERROR_REDACTION_CHECK=PASS`
- `DISAGREEMENT_EXPLANATION_CHECK=PASS`
- `NO_TRADE_DECISION_CHECK=PASS`
- `INSUFFICIENT_EVIDENCE_FALLBACK_CHECK=PASS`
- `DECISION_TRACE_AUDIT_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 禁止边界

- 不接真实模型 API。
- 不接 broker、账户、交易所私有接口或 secret。
- 不允许 agent 修改风控参数。
- 不允许下单。
- 不把 `review_required` 当作交易许可。
