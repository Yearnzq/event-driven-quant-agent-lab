# Stage 7 Review Checklist

日期：2026-05-07

## 范围

Stage 7 聚焦模型接入边界准备：

- provider config 默认必须使用 fake provider。
- prompt registry 必须有版本、输入契约和输出 schema。
- fake provider 输出必须是 schema-valid `AgentOpinion`。
- model call audit 必须记录 input/prompt/output hash、token 估算、成本和延迟。
- 不接真实模型 API，不读取 secret，不联网。
- 不允许多模型并发或真实 provider fallback；后续阶段新增真实 provider 时，Stage 7 gate 仍只验证 fake provider boundary。

## 必跑命令

```bash
python -m pytest -q
python -m compileall -q src scripts
python scripts/stage_01_gate.py
python scripts/stage_02_gate.py
python scripts/stage_03_gate.py
python scripts/stage_04_gate.py
python scripts/stage_05_gate.py
python scripts/stage_06_gate.py
python scripts/stage_07_gate.py
```

## 验收点

- `FAKE_PROVIDER_ONLY_CHECK=PASS`
- `DEFAULT_PROVIDER_FAKE_CHECK=PASS`
- `PROMPT_REGISTRY_CHECK=PASS`
- `STRUCTURED_OUTPUT_SCHEMA_CHECK=PASS`
- `MODEL_CALL_AUDIT_CHECK=PASS`
- `COST_LATENCY_HASH_CHECK=PASS`
- `NO_NETWORK_PROVIDER_CHECK=PASS`
- `NO_RAW_PROMPT_ARTIFACT_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 禁止边界

- Stage 7 路径不接 OpenAI、Anthropic 或其他真实模型 provider。
- 不读取环境变量 secret。
- 不保存 rendered prompt 原文产物。
- 不允许 provider 修改风控参数。
- 不允许 provider 生成订单或设置 `order_allowed=true`。
