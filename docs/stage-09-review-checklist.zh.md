# Stage 9 Review Checklist

日期：2026-05-07

## 范围

Stage 9 聚焦 A2A 服务边界：

- 本地 agent 必须通过 mock A2A client/server 边界调用。
- 必须写出 Agent Card，声明能力、schema、超时、重试和 advisory-only 边界。
- 每次 A2A 调用必须有 trace id、request hash、response hash、latency 和 attempt count。
- 超时和服务异常必须 fail-closed，降级为 `insufficient_evidence`。
- A2A 输出不能绕过 Data Gate / Risk Gate。
- 默认 gate 不联网，不启动真实远程服务。

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
python scripts/stage_09_gate.py
```

## 验收点

- `A2A_AGENT_CARD_CHECK=PASS`
- `A2A_CLIENT_SERVER_CHECK=PASS`
- `A2A_TIMEOUT_RETRY_CHECK=PASS`
- `A2A_TRACE_ARTIFACT_CHECK=PASS`
- `A2A_ERROR_REDACTION_CHECK=PASS`
- `A2A_DATA_RISK_BOUNDARY_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

## 禁止边界

- 默认不联网。
- 不启动真实远程 A2A 服务。
- 不保存 raw prompt artifact。
- 不把 API key、secret 或 private key 写入产物。
- A2A 失败不能中断 pipeline。
- A2A agent/card/trace 不能设置 `order_allowed=true`。
- A2A 响应不能绕过 Data Gate / Risk Gate。
