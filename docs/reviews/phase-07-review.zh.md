# Phase 7 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 8（单模型真实 Agent），但真实 provider 必须由 Phase 8 的显式 opt-in、fail-closed 和审计 gate 单独约束。
- 审查发现：原先阻塞项已按阶段边界重新收敛；Phase 7 gate 只验证 fake provider 路径，Phase 8 真实 provider 路径由 `stage_08_gate.py` 覆盖。

## 2. 本阶段范围

Phase 7 聚焦模型接入边界准备：

- provider 默认值必须是 `fake`。
- Phase 7 CLI 路径只运行 `--run-fake-model-call`。
- prompt registry 有版本、输入契约和输出 schema。
- fake provider 输出 schema-valid `AgentOpinion`。
- model call audit 记录 input hash、prompt hash、output hash、token 估算、成本和延迟。
- 不保存 rendered prompt 原文 artifact。

Phase 7 不执行真实模型调用、不读取 secret、不联网、不接 A2A、NautilusTrader、paper/live trading、broker 或生产访问。

## 3. 修改文件

- `README.md`
- `docs/stage-07-review-checklist.zh.md`
- `docs/reviews/phase-07-review.zh.md`
- `scripts/stage_07_gate.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/core/config.py`
- `src/quant_agent_lab/core/schemas.py`
- `src/quant_agent_lab/models/__init__.py`
- `src/quant_agent_lab/models/fake_provider.py`
- `src/quant_agent_lab/models/prompts.py`
- `tests/test_model_boundary_phase7.py`

本阶段同时保留 Phase 6 审查后修正：

- agent exception 原文脱敏为 `ExceptionType: redacted`。
- `AGENTS.md` 和 repo-local skills 的 conda 激活命令兼容 `quant` / `medi`。

## 4. 新增或扩展的 schema / config

- `ModelProviderConfig`
- `PromptSpec`
- `RenderedPrompt`
- `ModelCallAuditRecord`
- `ModelBoundaryResult`

说明：Phase 8 已在同一工作区扩展 `ModelProviderConfig` 支持 `openai`，因此 Phase 7 不再断言 config 层拒绝 `openai`；Phase 7 的有效边界是默认 provider 为 fake、Stage 7 命令路径只使用 fake provider 且不联网。

## 5. 新增用户可运行命令

```bash
python scripts/stage_07_gate.py
```

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --run-fake-model-call \
  --output-dir artifacts/model-boundary
```

## 6. 产物路径

Phase 7 fake provider boundary 输出目录包含：

- `prompt-registry.json`
- `rendered-prompt-meta.json`
- `fake-agent-opinion.json`
- `model-call-audit.json`
- `model-boundary-result.json`
- `artifact-catalog.json`

`rendered-prompt-meta.json` 不保存 rendered prompt 原文，只保存 input/prompt hash 和 schema metadata。

## 7. 已运行命令

```bash
docker exec quant-agent-lab bash -lc '
set -e
cd /workspace/event-driven-quant-agent-lab
conda run -n medi python -m pytest -q
conda run -n medi python -m compileall -q src scripts
for s in scripts/stage_01_gate.py scripts/stage_02_gate.py scripts/stage_03_gate.py scripts/stage_04_gate.py scripts/stage_05_gate.py scripts/stage_06_gate.py scripts/stage_07_gate.py scripts/stage_08_gate.py; do
  conda run -n medi python $s
done
'
```

## 8. 验证结果

- Python：`Python 3.10.20`
- pytest：`57 passed in 0.90s`
- compileall：`python -m compileall -q src scripts` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS`
- Phase 5 gate：`STAGE_05_OFFLINE_GATE=PASS`
- Phase 6 gate：`STAGE_06_OFFLINE_GATE=PASS`
- Phase 7 gate：`STAGE_07_OFFLINE_GATE=PASS`
- Phase 8 gate：`STAGE_08_OFFLINE_GATE=PASS`

Stage 7 gate 明细：

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

## 9. 审查发现

原阻塞项是 Phase 8 的 OpenAI provider 能力混入 Phase 7 审查口径，导致旧版 Stage 7 gate 断言 `ModelProviderConfig(provider="openai")` 必须被拒绝。当前修正为：

- Phase 7 gate 不再检查全局 config 是否拒绝 `openai`。
- Phase 7 gate 明确检查默认 provider 是 `fake`、默认不允许网络。
- Phase 7 gate 只执行 `--run-fake-model-call` 和 fake provider boundary。
- Phase 8 真实 provider 能力由 `stage_08_gate.py` 单独检查 fail-closed、错误脱敏、model audit artifact 和 Data/Risk Gate 边界。

## 10. 边界确认

- Phase 7 no real model call：通过，Stage 7 只执行 fake provider。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret artifact：通过。
- no auto order：通过。
- no raw prompt artifact：通过，prompt 原文不写入 artifact。
- `order_allowed=false`：由 schema 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。

## 11. 剩余风险

- fake provider 不是模型质量评估，只验证结构化边界和审计链路。
- Phase 8 真实 provider 已实现显式 opt-in 和 fail-closed，但真实响应质量、延迟和成本仍需要人工允许联网后单独审查。
- 当前 fake latency/cost 为 deterministic zero，用于离线门禁；真实 provider 必须记录实际 latency 和估算成本。
