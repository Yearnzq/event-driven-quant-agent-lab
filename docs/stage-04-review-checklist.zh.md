# 阶段 4 审查清单：信号研究框架

日期：2026-05-04

## 审查目标

确认 Phase 4 将单一 MA crossover smoke test 扩展为离线 signal registry、
多信号比较和 research artifact 审计闭环。该阶段只做 research/advisory-only，
不生成订单，不进入 paper/live trading。

## 离线必查项

- [ ] 默认 signal registry 至少包含 `trend`、`breakout`、`volatility` 三类信号。
- [ ] `--evaluate-signals` 输出 `signal-registry.json`。
- [ ] `--evaluate-signals` 输出 `signal_research_report.md`。
- [ ] `--evaluate-signals` 输出 `signal_research_report.json`。
- [ ] research report schema 为 `phase4.signal_research.v1`。
- [ ] research report 包含 strategy ranking。
- [ ] strategy ranking 使用多维 robust score，而不是单一收益排序。
- [ ] ranking JSON 包含 `score_components`。
- [ ] research report 标注 `deployable=false`。
- [ ] research report 标注 `order_allowed=false`。
- [ ] research report 标注 `human_required=true`。
- [ ] research report 明确写明不是 trading instruction。
- [ ] research 输出目录生成 `artifact-catalog.json`。
- [ ] research 输出目录生成 `run-manifest.json`。
- [ ] 篡改 research artifact 后 manifest 校验失败。
- [ ] Phase 1/2/3 gates 仍通过。

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
python scripts/stage_04_gate.py
'
```

## 自动断言覆盖

`scripts/stage_04_gate.py` 会自动检查：

- signal registry 生成。
- signal research Markdown/JSON 生成。
- trend/breakout/volatility signal families 均存在。
- research ranking 存在。
- research score 为归一化多维分数，包含收益、hit rate、回撤倒数和方向性覆盖率组件。
- research output 生成 artifact catalog 和 run manifest。
- research artifact 篡改会被 hash mismatch 检出。
- `order_allowed=true` 不出现。
- `deployable=true` 不出现。
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
