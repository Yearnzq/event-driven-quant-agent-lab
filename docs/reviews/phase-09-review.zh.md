# Phase 9 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 10（离线综合回测、鲁棒性验收与交易引擎适配前置）。
- 审查发现：未发现阻塞性问题。

## 2. 本阶段范围

Phase 9 聚焦 A2A 服务边界：

- 新增 Phase 9 A2A schema：Agent Card、request、response、trace record。
- 新增本地 mock A2A server/client。
- 新增 `A2AClientAgent`，主 pipeline 通过 client 调用 agent。
- daily advisory pipeline 写入 `a2a-agent-card.json` 和 `a2a-trace.json`。
- artifact catalog 登记 `a2a_agent_card` 和 `a2a_trace`。
- CLI 新增 `--run-a2a-advisory`。
- A2A 超时和异常 fail-closed，输出 failed `AgentOpinion` 和 failed trace。

## 3. 修改文件

- `README.md`
- `docs/stage-09-review-checklist.zh.md`
- `docs/reviews/phase-09-review.zh.md`
- `scripts/stage_09_gate.py`
- `src/quant_agent_lab/a2a/__init__.py`
- `src/quant_agent_lab/a2a/mock.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/core/schemas.py`
- `src/quant_agent_lab/reports/daily.py`
- `tests/test_a2a_phase9.py`

## 4. 新增 schema

- `A2AAgentCard`
- `A2AAgentRequest`
- `A2AAgentResponse`
- `A2ATraceRecord`
- `AdvisoryResult.a2a_agent_cards`
- `AdvisoryResult.a2a_trace_records`

## 5. 新增用户可运行命令

离线 mock A2A 日报：

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --run-a2a-advisory \
  --output-dir artifacts/a2a-reports
```

Stage gate：

```bash
python scripts/stage_09_gate.py
```

## 6. 产物路径

A2A 日报输出目录包含常规 advisory artifacts，并额外包含：

- `a2a-agent-card.json`
- `a2a-trace.json`

artifact catalog 包含：

- `a2a_agent_card`
- `a2a_trace`

## 7. 验证结果

本阶段验证命令：

```bash
docker exec quant-agent-lab bash -lc '
set -euo pipefail
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
if conda env list | grep -Eq "^quant[[:space:]]"; then
  conda activate quant
else
  conda activate medi
fi

python --version
python -m pytest -q
python -m compileall -q src scripts
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase9-review-20260507
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase9-review-20260507
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase9-review-20260507
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase9-review-20260507
python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-phase9-review-20260507
python scripts/stage_06_gate.py --output-dir /tmp/qal-stage-06-phase9-review-20260507
python scripts/stage_07_gate.py --output-dir /tmp/qal-stage-07-phase9-review-20260507
python scripts/stage_08_gate.py --output-dir /tmp/qal-stage-08-phase9-review-20260507
python scripts/stage_09_gate.py --output-dir /tmp/qal-stage-09-phase9-review-20260507
'
```

验证结果：

- Python：`Python 3.10.20`
- pytest：`61 passed in 1.12s`
- compileall：`python -m compileall -q src scripts` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-phase9-review-20260507`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-phase9-review-20260507`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-phase9-review-20260507`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-04-phase9-review-20260507`
- Phase 5 gate：`STAGE_05_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-05-phase9-review-20260507`
- Phase 6 gate：`STAGE_06_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-06-phase9-review-20260507`
- Phase 7 gate：`STAGE_07_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-07-phase9-review-20260507`
- Phase 8 gate：`STAGE_08_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-08-phase9-review-20260507`
- Phase 9 gate：`STAGE_09_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-09-phase9-review-20260507`

Stage 9 gate 明细：

- `A2A_AGENT_CARD_CHECK=PASS`
- `A2A_CLIENT_SERVER_CHECK=PASS`
- `A2A_TIMEOUT_RETRY_CHECK=PASS`
- `A2A_TRACE_ARTIFACT_CHECK=PASS`
- `A2A_ERROR_REDACTION_CHECK=PASS`
- `A2A_DATA_RISK_BOUNDARY_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

Stage 9 审查产物路径：

```text
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/a2a-agent-card.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/a2a-trace.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/artifact-catalog.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/run-manifest.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/run-btc-usdt-20260429t000000z.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-fake/run-btc-usdt-20260429t000000z.md
/tmp/qal-stage-09-phase9-review-20260507/a2a-timeout/a2a-agent-card.json
/tmp/qal-stage-09-phase9-review-20260507/a2a-timeout/a2a-trace.json
/tmp/qal-stage-09-phase9-review-20260507/cli-a2a-fake/a2a-agent-card.json
/tmp/qal-stage-09-phase9-review-20260507/cli-a2a-fake/a2a-trace.json
```

## 8. 审查发现

未发现阻塞性问题。

已重点核对：

- `A2AAgentCard` 使用 `phase9.agent_card.v1`，`order_allowed=false`，`human_required=true`。
- `A2ATraceRecord` 使用 `phase9.a2a_trace.v1`，记录 trace id、run id、agent id、request hash、response hash、latency、timeout 和 attempt count。
- A2A trace artifact 不保存 market/request 原文，只保存 hash 与元数据。
- artifact catalog 包含 `a2a_agent_card` 和 `a2a_trace`，manifest 校验通过。
- timeout 场景 attempt count 为 2，agent opinion 降级为 `status=fail`、`action_bias=insufficient_evidence`、`error_message="TimeoutError: redacted"`。
- timeout 场景 recommendation 和 RiskGate final action 均为 `insufficient_evidence`，`order_allowed=false`。
- CLI `--run-a2a-advisory` 生成 A2A card 和 trace，并在报告中写入 `A2A Trace`。
- 边界搜索显示 `order_allowed=true` 只出现在负向测试、stage gate 禁止断言和文档禁用说明中。

## 9. 边界确认

- default no network：通过。
- mock A2A client/server：通过。
- timeout/retry/fail-closed：通过。
- no raw prompt artifact：通过。
- no broker/account/secret artifact：通过。
- no paper/live trading：通过。
- no auto order：通过。
- `order_allowed=false`：由 schema、pipeline、risk gate 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。

## 10. 剩余风险

- 当前是本地 mock A2A 边界，不启动真实远程服务。
- 尚未实现真实 agent discovery、远程鉴权、队列化重试或 trace server。
- Phase 10 前仍不提供 paper/live trading 和 NautilusTrader 执行适配。
- 当前 timeout 实现使用本地线程池模拟边界超时；真实远程 A2A 需要进一步验证 HTTP/gRPC 超时、取消语义、幂等 trace id 和重试退避策略。
