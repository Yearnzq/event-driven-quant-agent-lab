# Phase 3 Review

日期：2026-05-03

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 4（信号研究框架），但需继续保持 advisory-only 边界。

## 2. 本阶段范围

Phase 3 聚焦 Artifact 与审计账本：

- 每次 pipeline 运行生成 `artifact-catalog.json`。
- 每次 pipeline 运行生成 `run-manifest.json`。
- catalog 记录 report/result/audit/audit-log 的 path、sha256、size、content type。
- manifest 记录 input/output/config/catalog hash。
- 阶段 gate 验证好数据、坏数据和 artifact 篡改。

未引入真实模型、A2A、NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 3. 修改文件

- `README.md`
- `docs/stage-03-review-checklist.zh.md`
- `docs/reviews/phase-03-review.zh.md`
- `scripts/stage_03_gate.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/data/audit.py`
- `tests/test_audit.py`

## 4. 新增或扩展的 schema

- `phase3.artifact_catalog.v1`
  - `run_id`
  - `artifacts[].role`
  - `artifacts[].path`
  - `artifacts[].sha256`
  - `artifacts[].size_bytes`
  - `artifacts[].content_type`
  - `order_allowed=false`
  - `human_required=true`
- `phase3.run_manifest.v1`
  - `phase=3`
  - `run_id`
  - `symbol`
  - `as_of`
  - `input_hash`
  - `output_hash`
  - `config_hash`
  - `artifact_catalog_hash`
  - `validation_result`
  - `replay_entrypoint`
  - `model_provider=mock`
  - `order_allowed=false`
  - `human_required=true`

## 5. 新增用户可运行命令

```bash
python scripts/stage_03_gate.py
```

每次 pipeline run 会在输出目录旁生成：

```text
artifact-catalog.json
run-manifest.json
```

## 6. 已运行命令

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant
python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-after-phase3
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-after-phase3
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-codex-20260503
'
```

## 7. 验证结果

- Python：`Python 3.10.20`
- pytest：`34 passed`
- compileall：`python -m compileall -q src` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-codex-20260503`
- Phase 3 gate 明细：
  - `RUN_MANIFEST_CHECK=PASS`
  - `ARTIFACT_CATALOG_CHECK=PASS`
  - `ARTIFACT_TAMPER_CHECK=PASS`
  - `BAD_DATA_AUDIT_CHECK=PASS`
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `HUMAN_REQUIRED=true`

## 8. 产物路径

- mock reports：`/tmp/qal-stage-03-codex-20260503/reports/mock/`
- CSV reports：`/tmp/qal-stage-03-codex-20260503/reports/csv/`
- tampered reports：`/tmp/qal-stage-03-codex-20260503/reports/tampered/`
- bad data reports：`/tmp/qal-stage-03-codex-20260503/reports/bad_gap/`
- sample good dataset：`/tmp/qal-stage-03-codex-20260503/sample_good/`
- sample bad dataset：`/tmp/qal-stage-03-codex-20260503/sample_bad_gap/`

## 9. 边界确认

- no real model call：通过，只使用 mock agents。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：通过。
- `human_required=true`：通过。
- Data Gate 失败不补猜：通过，坏数据集输出 `insufficient_evidence`，并仍生成审计账本。
- raw text leakage：本阶段未新增原文进入 agent context；Phase 1 gate 仍覆盖文本清洗。

## 10. 剩余风险

- 当前 replay 信息记录到 entrypoint 和 hash，尚未生成完整重放脚本；如需一键 replay，可在后续阶段补 CLI replay 命令。
- catalog 覆盖 pipeline 输出产物，不覆盖所有研究目录或外部数据源目录；Phase 4 研究产物需要继续接入 catalog。
- best-effort 网络检查未运行；网络失败或跳过不阻塞当前离线审计账本。

## 11. 2026-05-04 预推送复核

- Claude review 结论：Phase 2 / Phase 3 均 PASS；无 blocker / high risk。
- 已确认的中风险：CLI 暴露 risk config 参数。当前判断为可接受：该入口用于本地离线测试，`RiskConfig` 仍由 deterministic code 读取并写入 manifest；`order_allowed=false`、`human_required=true` 由 schema 和 gate 强制，不可通过 CLI 改为自动下单。
- 本次补丁：修复 `--evaluate-signals --bars-1d-csv <path>` 单独使用时误报参数缺失的问题，并新增回归测试。
- 预推送验证命令：
  ```bash
  docker exec quant-agent-lab bash -lc '
  cd /workspace/event-driven-quant-agent-lab
  source /opt/miniconda3/etc/profile.d/conda.sh
  conda activate quant
  python --version
  python -m pytest -q
  python -m compileall -q src
  python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-prepush-20260504
  python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-prepush-20260504
  python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-prepush-20260504
  '
  ```
- 预推送验证结果：
  - Python：`Python 3.10.20`
  - pytest：`35 passed in 4.02s`
  - compileall：PASS
  - Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS`
  - Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS`
  - Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS`
