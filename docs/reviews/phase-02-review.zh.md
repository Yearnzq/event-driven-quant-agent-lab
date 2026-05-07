# Phase 2 Review

日期：2026-05-03

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 3（Artifact 与审计账本），但需继续保持 advisory-only 边界。

## 2. 本阶段范围

Phase 2 聚焦数据层硬化：

- CSV 数据集 manifest / metadata schema。
- 文件 hash、size、必需资产校验。
- 好数据 sample 和坏数据 sample。
- Data Gate 失败用例固化。
- 独立 `stage_02_gate.py`。

未引入真实模型、A2A、NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 3. 修改文件

- `README.md`
- `docs/stage-02-review-checklist.zh.md`
- `docs/reviews/phase-02-review.zh.md`
- `scripts/stage_02_gate.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/data/connectors.py`
- `src/quant_agent_lab/data/importers.py`
- `src/quant_agent_lab/data/metadata.py`
- `tests/test_metadata.py`

## 4. 新增用户可运行命令

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli --write-sample-data sample_data/btc_usdt
PYTHONPATH=src python -m quant_agent_lab.app.cli --validate-dataset sample_data/btc_usdt
PYTHONPATH=src python -m quant_agent_lab.app.cli --write-bad-sample-data sample_data/bad_btc_usdt
python scripts/stage_02_gate.py
```

## 5. Schema / metadata 变更

- 新增 `phase2.dataset.v1` dataset manifest。
- manifest 字段包括：
  - `dataset_id`
  - `symbol`
  - `as_of`
  - `source`
  - `bars_1h_csv`
  - `bars_1d_csv`
  - `portfolio_json`
  - `assets[].role`
  - `assets[].path`
  - `assets[].sha256`
  - `assets[].size_bytes`
  - `quality_rules`
  - `order_allowed=false`
  - `human_required=true`

## 6. 已运行命令

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-after-phase2
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-codex-20260503
'
```

## 7. 验证结果

- Python：`Python 3.10.20`
- pytest：`32 passed in 2.09s`
- compileall：`python -m compileall -q src` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-after-phase2`，`BINANCE_CHECK=SKIPPED`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-codex-20260503`
- Phase 2 gate 明细：
  - `DATASET_MANIFEST_CHECK=PASS`
  - `TAMPER_CHECK=PASS`
  - `BAD_DATA_GATE_CHECK=PASS`
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `HUMAN_REQUIRED=true`

## 8. 产物路径

- 好数据集：`/tmp/qal-stage-02-codex-20260503/sample_good/`
- 篡改检测样例：`/tmp/qal-stage-02-codex-20260503/sample_tampered/`
- 坏数据集：`/tmp/qal-stage-02-codex-20260503/sample_bad_gap/`
- 好数据报告：`/tmp/qal-stage-02-codex-20260503/reports/good/`
- 坏数据报告：`/tmp/qal-stage-02-codex-20260503/reports/bad_gap/`

## 9. 边界确认

- no real model call：通过，只使用 mock agents。
- no A2A：通过，未引入服务化 agent。
- no NautilusTrader：通过，未引入 adapter 或引擎调用。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：通过。
- `human_required=true`：通过。
- Data Gate 失败不补猜：通过，坏数据集输出 `insufficient_evidence`。
- raw text leakage：本阶段未新增原文进入 agent context；Phase 1 文本清洗 gate 仍通过。

## 10. 剩余风险

- 本阶段 manifest 只覆盖 CSV/JSON 文件级 hash，不是完整 artifact catalog/hash ledger；该内容留给 Phase 3。
- Binance/GitHub SSH best-effort 网络检查未运行；网络失败按 Phase 1/2 规则不阻塞离线基线。
- 坏数据样例当前覆盖 hourly gap；更多坏数据类型（重复时间戳、错 symbol、缺字段、多来源降级）可在后续数据层迭代继续扩充。
