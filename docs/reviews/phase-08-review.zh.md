# Phase 8 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 9（A2A 服务边界），但真实模型调用仍需人工显式允许。
- 审查发现：未发现阻塞性问题。

## 2. 本阶段范围

Phase 8 聚焦单模型 Recommendation Draft Agent：

- 新增 `SingleModelRecommendationAgent`。
- 新增 OpenAI Responses provider 适配层。
- daily advisory pipeline 写入 `model-call-audit.json` 并登记到 artifact catalog。
- CLI 新增 `--run-single-model-advisory`。
- CLI 新增 `--model-provider`、`--model-name`、`--allow-real-model-call`、`--model-api-key-env`。
- OpenAI provider 缺 key 或未允许网络时 fail-closed，输出 failed `AgentOpinion` 和 failed audit。
- 默认 stage gate 不联网，只验证 fake 单模型路径和 OpenAI fail-closed 路径。

## 3. 修改文件

- `README.md`
- `docs/stage-08-review-checklist.zh.md`
- `docs/reviews/phase-08-review.zh.md`
- `scripts/stage_08_gate.py`
- `src/quant_agent_lab/agents/model.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/core/config.py`
- `src/quant_agent_lab/core/schemas.py`
- `src/quant_agent_lab/models/openai_provider.py`
- `tests/test_single_model_phase8.py`

## 4. 新增或扩展的 schema / config

- `ModelProviderConfig.provider` 扩展为 `fake | openai`。
- `ModelProviderConfig` 新增：
  - `api_key_env`
  - `api_base_url`
  - `input_cost_per_million_tokens`
  - `output_cost_per_million_tokens`
- `RenderedPrompt.provider` 扩展为 `fake | openai`。
- `ModelCallAuditRecord.provider` 扩展为 `fake | openai`。
- `AdvisoryResult.model_call_audits`

## 5. 新增用户可运行命令

离线 fake 单模型日报：

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --output-dir artifacts/single-model-reports
```

OpenAI 单模型日报，需要人工显式允许 provider、配置 key 并允许联网：

```bash
QAL_ENABLE_OPENAI_PROVIDER=1 OPENAI_API_KEY=... PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --model-provider openai \
  --model-name gpt-5.4-mini \
  --allow-real-model-call \
  --output-dir artifacts/single-model-openai
```

Stage gate：

```bash
python scripts/stage_08_gate.py
```

## 6. 产物路径

单模型日报输出目录包含常规 advisory artifacts，并额外包含：

- `model-call-audit.json`

artifact catalog 包含 `model_call_audit` role。

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
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase8-review-20260507
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase8-review-20260507
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase8-review-20260507
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase8-review-20260507
python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-phase8-review-20260507
python scripts/stage_06_gate.py --output-dir /tmp/qal-stage-06-phase8-review-20260507
python scripts/stage_07_gate.py --output-dir /tmp/qal-stage-07-phase8-review-20260507
python scripts/stage_08_gate.py --output-dir /tmp/qal-stage-08-phase8-review-20260507
'
```

验证结果：

- Python：`Python 3.10.20`
- pytest：`57 passed in 1.13s`
- compileall：`python -m compileall -q src scripts` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-phase8-review-20260507`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-phase8-review-20260507`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-phase8-review-20260507`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-04-phase8-review-20260507`
- Phase 5 gate：`STAGE_05_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-05-phase8-review-20260507`
- Phase 6 gate：`STAGE_06_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-06-phase8-review-20260507`
- Phase 7 gate：`STAGE_07_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-07-phase8-review-20260507`
- Phase 8 gate：`STAGE_08_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-08-phase8-review-20260507`

Stage 8 gate 明细：

- `REAL_MODEL_OPTIONAL_CHECK=SKIPPED`
- `SINGLE_MODEL_AGENT_CHECK=PASS`
- `SINGLE_MODEL_REPORT_CHECK=PASS`
- `OPENAI_PROVIDER_FAIL_CLOSED_CHECK=PASS`
- `MODEL_AUDIT_ARTIFACT_CHECK=PASS`
- `MODEL_ERROR_REDACTION_CHECK=PASS`
- `DATA_RISK_GATE_BOUNDARY_CHECK=PASS`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

Stage 8 审查产物路径：

```text
/tmp/qal-stage-08-phase8-review-20260507/single-model-fake/model-call-audit.json
/tmp/qal-stage-08-phase8-review-20260507/single-model-fake/artifact-catalog.json
/tmp/qal-stage-08-phase8-review-20260507/single-model-fake/run-manifest.json
/tmp/qal-stage-08-phase8-review-20260507/single-model-fake/run-btc-usdt-20260429t000000z.json
/tmp/qal-stage-08-phase8-review-20260507/single-model-fake/run-btc-usdt-20260429t000000z.md
/tmp/qal-stage-08-phase8-review-20260507/single-model-openai-missing-key/model-call-audit.json
/tmp/qal-stage-08-phase8-review-20260507/cli-single-model-fake/model-call-audit.json
```

## 8. 审查发现

未发现阻塞性问题。

已重点核对：

- 默认 `--run-single-model-advisory` 使用 fake provider，不联网。
- OpenAI provider 只有 `provider="openai"` 且 `allow_network=true` 时才可能进入网络路径。
- 缺失 API key 和未允许网络都会 fail-closed，输出 failed `AgentOpinion` 和 failed `ModelCallAuditRecord`。
- `model-call-audit.json` 进入 artifact catalog，artifact hash 校验通过。
- report Markdown 包含 `Model Call Audit`，记录 provider/model/status/token/cost/latency。
- `model-call-audit.json` 不包含 rendered prompt 原文。
- missing-key 场景的错误信息为 `RuntimeError: redacted`，未泄漏 env var 名称或 secret。
- fake 单模型和 OpenAI fail-closed 场景均保持 `order_allowed=false`、`human_required=true`。

## 9. 边界确认

- default no real model call：通过。
- optional real OpenAI call：本次未运行，`REAL_MODEL_OPTIONAL_CHECK=SKIPPED`；仅人工显式设置 `QAL_ENABLE_OPENAI_PROVIDER=1`、允许联网且环境有 `OPENAI_API_KEY` 时运行。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret artifact：通过。
- no auto order：通过。
- no raw prompt artifact：通过，prompt 原文不写入 report/result/audit/catalog。
- `order_allowed=false`：由 schema、pipeline、risk gate 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。

## 10. 剩余风险

- 默认 gate 没有真实调用 OpenAI，只验证适配层和 fail-closed 行为。
- OpenAI 真实响应质量、延迟、成本需要人工允许联网后单独审查。
- Phase 9 前仍不提供 A2A 服务边界、重试队列、trace server 或远程 agent card。
- 当前 provider 适配层直接使用 Responses API HTTP 调用；Phase 9 服务化前仍需补 trace id、调用重试策略和更细粒度成本上限。
