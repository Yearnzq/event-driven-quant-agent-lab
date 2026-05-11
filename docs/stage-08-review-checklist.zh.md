# Stage 8 Review Checklist

日期：2026-05-07

## 范围

Stage 8 聚焦单模型 Recommendation Draft Agent：

- 单模型 agent 必须接入 daily advisory pipeline。
- fake 单模型路径必须离线可复现。
- OpenAI provider 缺 key 或未允许网络时必须 fail-closed。
- 单模型日报必须写出 `model-call-audit.json`，并进入 artifact catalog。
- Data Gate / Risk Gate 仍是硬边界。
- 默认 gate 不发起真实模型调用。

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
python scripts/stage_08_gate.py
```

## 验收点

- `SINGLE_MODEL_AGENT_CHECK=PASS`
- `SINGLE_MODEL_REPORT_CHECK=PASS`
- `OPENAI_PROVIDER_FAIL_CLOSED_CHECK=PASS`
- `MODEL_AUDIT_ARTIFACT_CHECK=PASS`
- `MODEL_ERROR_REDACTION_CHECK=PASS`
- `DATA_RISK_GATE_BOUNDARY_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 可选联网验收

只有人工明确允许、设置 `QAL_ENABLE_OPENAI_PROVIDER=1` 且环境里有 `OPENAI_API_KEY` 时才运行：

```bash
QAL_ENABLE_OPENAI_PROVIDER=1 python scripts/stage_08_gate.py --allow-real-model-call
```

## 禁止边界

- 默认不联网。
- 不把 API key 写入产物。
- 不保存 raw prompt artifact。
- provider 失败不能中断 pipeline。
- provider 输出不能绕过 Data Gate / Risk Gate。
- provider 不能设置 `order_allowed=true`。
