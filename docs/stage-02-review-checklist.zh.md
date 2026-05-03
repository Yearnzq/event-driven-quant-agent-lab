# 阶段 2 审查清单：数据层硬化

日期：2026-05-03

## 审查目标

确认 Phase 2 在不引入真实模型、A2A、NautilusTrader、paper/live trading、
broker、secret 或自动下单的前提下，强化 CSV 数据集的 schema、metadata、
hash 校验、坏数据样例和 Data Gate 失败路径。

## 离线必查项

- [ ] `metadata.json` 使用 `phase2.dataset.v1`。
- [ ] `metadata.json` 包含 `dataset_id`、`symbol`、`as_of`、`source`、资产路径、资产 `sha256` 和 `size_bytes`。
- [ ] `metadata.json` 保持 `order_allowed=false`。
- [ ] `metadata.json` 保持 `human_required=true`。
- [ ] `--write-sample-data` 生成可通过 manifest 校验的好数据集。
- [ ] `--validate-dataset` 能检测好数据集通过。
- [ ] 篡改 CSV 后 manifest 校验能报告 hash/size mismatch。
- [ ] `--write-bad-sample-data` 生成可审计但会触发 Data Gate fail 的坏数据集。
- [ ] 坏数据集进入 pipeline 后输出 `insufficient_evidence`。
- [ ] 坏数据集和好数据集都不允许订单：`order_allowed=false`。
- [ ] Phase 1 gate 仍通过，避免数据层变更破坏既有离线闭环。

## 推荐审查命令

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant

python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py
python scripts/stage_02_gate.py
'
```

## 自动断言覆盖

`scripts/stage_02_gate.py` 会自动检查：

- sample CSV dataset manifest 通过。
- sample CSV pipeline Data Gate 通过。
- 篡改后的 CSV dataset manifest 失败，并报告 `asset sha256 mismatch`。
- bad CSV dataset manifest 通过，但 pipeline Data Gate 失败。
- bad CSV dataset 触发 `insufficient_evidence`。
- 所有 Phase 2 产物保持 `order_allowed=false`、`human_required=true`。

## 不做事项

- 不接真实模型 API。
- 不接 A2A。
- 不接 NautilusTrader。
- 不做 paper/live trading。
- 不创建订单或 order draft。
- 不读取 secret。
- 不引入写权限 MCP。
- 不把未清洗新闻、网页、社媒全文放入 agent context。
