# Phase 5 Review

日期：2026-05-04

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：可进入 Phase 6（Advisory 决策层增强），但需继续保持 advisory-only 边界。

## 2. 本阶段范围

Phase 5 聚焦 deterministic Risk Gate 增强：

- Risk Gate 输出 `risk_metrics`。
- Markdown/JSON 报告记录风控指标。
- 新增近期回撤检查。
- 新增下行波动检查。
- 新增单小时损失检查。
- 新增组合风险预算检查。
- 新增 `stage_05_gate.py`。

未引入真实模型、A2A、NautilusTrader、paper/live trading、broker、secret、生产访问或自动下单。

## 3. 修改文件

- `README.md`
- `docs/stage-05-review-checklist.zh.md`
- `docs/reviews/phase-05-review.zh.md`
- `scripts/stage_05_gate.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/app/pipeline.py`
- `src/quant_agent_lab/core/config.py`
- `src/quant_agent_lab/core/schemas.py`
- `src/quant_agent_lab/reports/daily.py`
- `src/quant_agent_lab/risk/gate.py`
- `tests/test_gates.py`
- `tests/test_pipeline.py`
- `tests/test_schemas.py`

## 4. 新增或扩展的 schema / config

- `RiskDecision.risk_metrics`
- `RiskConfig.max_recent_drawdown_pct`
- `RiskConfig.max_downside_volatility`
- `RiskConfig.max_single_hour_loss_pct`
- `RiskConfig.max_portfolio_risk_budget_pct`

`RiskConfig` 仍为 frozen Pydantic model。风控参数由 deterministic config 提供，并通过 run manifest `config_hash` 审计；LLM/agent 仍不能修改风控参数。

## 5. 新增用户可运行命令

```bash
python scripts/stage_05_gate.py
```

CLI 新增本地离线测试参数：

```text
--max-recent-drawdown-pct
--max-downside-volatility
--max-single-hour-loss-pct
--max-portfolio-risk-budget-pct
```

这些参数只影响本地 deterministic Risk Gate 评估；不会允许订单，也不会改变 `human_required=true`。

## 6. 已运行命令

```bash
docker exec quant-agent-lab bash -lc '
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate quant
python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase5-verify-20260504
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase5-verify-20260504
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase5-verify-20260504
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase5-verify-20260504
python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-phase5-verify-20260504
'
```

## 7. 验证结果

- Python：`Python 3.10.20`
- pytest：`41 passed in 3.17s`
- compileall：`python -m compileall -q src` 退出码 0
- Phase 1 gate：`STAGE_01_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-01-phase5-verify-20260504`
- Phase 2 gate：`STAGE_02_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-02-phase5-verify-20260504`
- Phase 3 gate：`STAGE_03_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-03-phase5-verify-20260504`
- Phase 4 gate：`STAGE_04_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-04-phase5-verify-20260504`
- Phase 5 gate：`STAGE_05_OFFLINE_GATE=PASS output_dir=/tmp/qal-stage-05-phase5-verify-20260504`
- Phase 5 gate 明细：
  - `RISK_METRICS_CHECK=PASS`
  - `DRAWDOWN_RULE_CHECK=PASS`
  - `DOWNSIDE_VOLATILITY_RULE_CHECK=PASS`
  - `SINGLE_HOUR_LOSS_RULE_CHECK=PASS`
  - `PORTFOLIO_RISK_BUDGET_RULE_CHECK=PASS`
  - `RISK_CONFIG_AUDIT_CHECK=PASS`
  - `ORDER_ALLOWED_TRUE_COUNT=0`
  - `HUMAN_REQUIRED=true`

## 8. 边界确认

- no real model call：通过，仍为 deterministic code。
- no A2A：通过。
- no NautilusTrader：通过。
- no paper/live trading：通过。
- no broker/account/secret：通过。
- no auto order：通过。
- `order_allowed=false`：由 schema 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。
- LLM cannot modify risk params：通过，未引入模型调用；`RiskConfig` frozen，参数写入 config hash。

## 9. 剩余风险

- 当前风控指标基于 BTC/USDT 单资产与已有组合快照，尚不是多资产组合 VaR/ES。
- drawdown/downside volatility 使用简化 deterministic 计算，适合作为 gate，不代表生产级风控模型。
