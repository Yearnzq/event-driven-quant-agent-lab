# 阶段 5 审查清单：风控规则增强

日期：2026-05-04

## 审查目标

确认 Phase 5 将 Risk Gate 从单资产基础限制扩展为可审计的组合风险检查。
本阶段仍只做 deterministic advisory gate，不生成订单，不接真实模型，不进入
paper/live trading。

## 离线必查项

- [ ] Risk Gate 记录 `risk_metrics`。
- [ ] report JSON 包含 `risk_decision.risk_metrics`。
- [ ] Markdown report 输出 risk metrics。
- [ ] 现有仓位上限仍能拒绝。
- [ ] 现金缓冲下限仍能拒绝。
- [ ] 小时波动上限仍能拒绝。
- [ ] 新增近期回撤上限拒绝。
- [ ] 新增下行波动上限拒绝。
- [ ] 新增单小时损失上限拒绝。
- [ ] 新增组合风险预算上限拒绝。
- [ ] `RiskConfig` 仍为 frozen Pydantic model。
- [ ] config hash 继续写入 run manifest，用于风控参数审计。
- [ ] `order_allowed=false` 保持。
- [ ] `human_required=true` 保持。
- [ ] Phase 1/2/3/4 gates 仍通过。

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
python scripts/stage_05_gate.py
'
```

## 自动断言覆盖

`scripts/stage_05_gate.py` 会自动检查：

- default run 生成 risk metrics。
- risk metrics 出现在 Markdown report。
- risk metrics 出现在 result JSON。
- recent drawdown 规则拒绝高回撤场景。
- downside volatility 规则拒绝高下行波动场景。
- single-hour loss 规则拒绝冲击损失场景。
- portfolio risk budget 规则拒绝超预算场景。
- strict risk config 仍写入可校验 run manifest。
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
- 不让 LLM 修改风控参数或绕过 Risk Gate。
