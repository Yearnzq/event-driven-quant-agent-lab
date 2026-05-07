# 阶段 3 审查清单：Artifact 与审计账本

日期：2026-05-03

## 审查目标

确认每次 advisory pipeline 运行都会留下可审计、可校验的 run manifest 和
artifact catalog。Phase 3 只强化审计账本，不引入真实模型、A2A、
NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 离线必查项

- [ ] 每次 mock pipeline 运行生成 `run-manifest.json`。
- [ ] 每次 mock pipeline 运行生成 `artifact-catalog.json`。
- [ ] 每次 CSV pipeline 运行生成 `run-manifest.json`。
- [ ] 每次 CSV pipeline 运行生成 `artifact-catalog.json`。
- [ ] catalog 至少记录 Markdown report、result JSON、audit JSON、audit log。
- [ ] catalog 记录每个 artifact 的相对路径、sha256、size、content type。
- [ ] manifest 记录 `input_hash`、`output_hash`、`config_hash`、`artifact_catalog_hash`。
- [ ] 篡改任一已记录 artifact 后，manifest 校验失败。
- [ ] Data Gate 失败运行仍写入 manifest/catalog，且 recommendation 为 `insufficient_evidence`。
- [ ] manifest/catalog 均保持 `order_allowed=false`。
- [ ] manifest/catalog 均保持 `human_required=true`。
- [ ] Phase 1 和 Phase 2 gates 仍通过。

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
python scripts/stage_03_gate.py
'
```

## 自动断言覆盖

`scripts/stage_03_gate.py` 会自动检查：

- mock run manifest/catalog 通过校验。
- CSV run manifest/catalog 通过校验。
- artifact 篡改后 hash 校验失败。
- bad data run 仍生成有效 manifest/catalog。
- bad data run 触发 `insufficient_evidence`。
- `order_allowed=true` 不出现。
- `human_required=true` 保持。

## 不做事项

- 不接真实模型 API。
- 不接 A2A。
- 不接 NautilusTrader。
- 不做 paper/live trading。
- 不创建订单或 order draft。
- 不读取 secret。
- 不引入写权限 MCP。
- 不把未清洗新闻、网页、社媒全文放入 agent context。
