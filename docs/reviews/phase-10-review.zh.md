# Phase 10 Review

日期：2026-05-07

## 1. 本阶段结论

- 状态：PASS
- 审查人：Codex
- 是否进入下一阶段：十阶段路线已完成；后续应进入人工总审查，而不是直接进入 paper/live trading。

## 1.1 审查修复

- 已修复 P1 walk-forward 计分窗口污染问题。`_slice_bars()` 仍可带入 split start 前的 warmup bars 用于信号计算，但 `run_style_backtest()` 现在接收 `score_start` / `score_end`，只有 score window 内的 returns、turnover、fee、slippage 会进入 metrics。
- `BacktestMetrics` 新增 `scored_return_count`、`first_scored_at`、`last_scored_at`，用于审计每个 train/validation/test 段的实际计分范围。
- `tests/test_strategy_tournament_phase10.py` 新增回归断言，确认每个 split/style 的 `first_scored_at` 不早于对应窗口开始日。
- `scripts/stage_10_gate.py` 新增同等门禁断言，防止 warmup returns 再次污染 OOS metrics。

## 2. 本阶段范围

Phase 10 聚焦离线综合回测、鲁棒性验收与交易引擎适配前置：

- 新增固定 strategy style registry。
- 新增固定 walk-forward split。
- 新增 deterministic Phase 10 BTC/USDT 样本数据生成。
- 新增离线 style backtest metrics。
- 新增成本敏感性测试。
- 新增压力测试和参数扰动测试。
- 新增 AI blind preference check。
- 新增 NautilusTrader 只读 adapter input sample。
- CLI 新增 `--run-strategy-tournament`。

## 3. 修改文件

- `README.md`
- `docs/stage-10-review-checklist.zh.md`
- `docs/reviews/phase-10-review.zh.md`
- `scripts/stage_10_gate.py`
- `src/quant_agent_lab/app/cli.py`
- `src/quant_agent_lab/research/tournament.py`
- `tests/test_strategy_tournament_phase10.py`

## 4. 新增 schema / config

- `CostModel`
- `WalkForwardSplit`
- `StrategyStyleSpec`
- `BacktestMetrics`
- `WalkForwardStyleResult`
- `StyleRankingRow`
- `CostSensitivityResult`
- `StressTestResult`
- `AIBlindPreferenceCheck`
- `StrategyStyleTournamentReport`
- `SimulationManifest`

## 5. 新增用户可运行命令

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --run-strategy-tournament \
  --output-dir artifacts/research \
  --audit-output-dir artifacts/audit \
  --adapter-output-dir artifacts/adapters/nautilus
```

Stage gate：

```bash
python scripts/stage_10_gate.py
```

## 6. 产物路径

```text
artifacts/research/strategy_style_tournament.md
artifacts/research/strategy_style_tournament.json
artifacts/research/walk_forward_results.json
artifacts/research/stress_test_results.json
artifacts/research/cost_sensitivity_results.json
artifacts/audit/simulation_manifest.json
artifacts/adapters/nautilus/adapter_input_sample.json
```

## 7. 验证结果

本次审查在项目容器 `quant-agent-lab` 中执行，conda 环境为 `medi`，Python 版本：

```text
Python 3.10.20
```

本阶段验证命令与结果：

```bash
python -m pytest -q
python -m compileall -q src scripts
python scripts/stage_01_gate.py --output-dir /tmp/qal-stage-01-phase10-review-20260507
python scripts/stage_02_gate.py --output-dir /tmp/qal-stage-02-phase10-review-20260507
python scripts/stage_03_gate.py --output-dir /tmp/qal-stage-03-phase10-review-20260507
python scripts/stage_04_gate.py --output-dir /tmp/qal-stage-04-phase10-review-20260507
python scripts/stage_05_gate.py --output-dir /tmp/qal-stage-05-phase10-review-20260507
python scripts/stage_06_gate.py --output-dir /tmp/qal-stage-06-phase10-review-20260507
python scripts/stage_07_gate.py --output-dir /tmp/qal-stage-07-phase10-review-20260507
python scripts/stage_08_gate.py --output-dir /tmp/qal-stage-08-phase10-review-20260507
python scripts/stage_09_gate.py --output-dir /tmp/qal-stage-09-phase10-review-20260507
python scripts/stage_10_gate.py --output-dir /tmp/qal-stage-10-phase10-review-20260507
```

结果：

- `pytest`：修复后 `67 passed`
- `compileall`：PASS，`src scripts` 编译无错误。
- Stage 01：`STAGE_01_OFFLINE_GATE=PASS`，`BINANCE_CHECK=SKIPPED`。
- Stage 02：`STAGE_02_OFFLINE_GATE=PASS`，dataset manifest、tamper、bad data gate 均通过。
- Stage 03：`STAGE_03_OFFLINE_GATE=PASS`，run manifest、artifact catalog、tamper、bad data audit 均通过。
- Stage 04：`STAGE_04_OFFLINE_GATE=PASS`，signal registry、research report、catalog、tamper 均通过。
- Stage 05：`STAGE_05_OFFLINE_GATE=PASS`，risk metrics、drawdown、downside volatility、single hour loss、portfolio budget、risk config audit 均通过。
- Stage 06：`STAGE_06_OFFLINE_GATE=PASS`，agent failure degradation、redaction、disagreement、no-trade、fallback、decision trace audit 均通过。
- Stage 07：`STAGE_07_OFFLINE_GATE=PASS`，fake default、prompt registry、schema、model audit、hash、no-network、no raw prompt artifact 均通过。
- Stage 08：`STAGE_08_OFFLINE_GATE=PASS`，`REAL_MODEL_OPTIONAL_CHECK=SKIPPED`；single model、fail-closed、audit、redaction、data/risk boundary 均通过。
- Stage 09：`STAGE_09_OFFLINE_GATE=PASS`，A2A card、client/server、timeout/retry、trace、redaction、data/risk boundary 均通过。

实际 Stage 10 gate 明细：

- `STRATEGY_STYLE_REGISTRY_CHECK=PASS`
- `WALK_FORWARD_SPLIT_CHECK=PASS`
- `COST_SENSITIVITY_CHECK=PASS`
- `STRESS_TEST_CHECK=PASS`
- `AI_BLIND_PREFERENCE_CHECK=PASS`
- `SIMULATION_MANIFEST_CHECK=PASS`
- `NAUTILUS_ADAPTER_SAMPLE_CHECK=PASS`
- `DEPLOYABLE_TRUE_COUNT=0`
- `ORDER_ALLOWED_TRUE_COUNT=0`
- `HUMAN_REQUIRED=true`

本次 Stage 10 审查生成并抽查的产物目录：

```text
/tmp/qal-stage-10-phase10-review-20260507/research/strategy_style_tournament.md
/tmp/qal-stage-10-phase10-review-20260507/research/strategy_style_tournament.json
/tmp/qal-stage-10-phase10-review-20260507/research/walk_forward_results.json
/tmp/qal-stage-10-phase10-review-20260507/research/stress_test_results.json
/tmp/qal-stage-10-phase10-review-20260507/research/cost_sensitivity_results.json
/tmp/qal-stage-10-phase10-review-20260507/research/strategy-style-registry.json
/tmp/qal-stage-10-phase10-review-20260507/research/artifact-catalog.json
/tmp/qal-stage-10-phase10-review-20260507/research/simulation_manifest.sha256
/tmp/qal-stage-10-phase10-review-20260507/audit/simulation_manifest.json
/tmp/qal-stage-10-phase10-review-20260507/adapters/nautilus/adapter_input_sample.json
```

产物内容抽查：

- Strategy styles：6 个，`trend_following`、`breakout`、`mean_reversion`、`volatility_regime`、`defensive_vol_target`、`momentum`。
- Walk-forward windows：4 个，`window_1` 到 `window_4`；结果行数 24。
- Cost models：3 个，`low_cost`、`medium_cost`、`high_cost`；结果行数 18。
- Stress scenarios：8 个，结果行数 48。
- AI blind preference：`data_visible_to_ai=train_validation_only`。
- `simulation_manifest.json`：`schema_version=phase10.simulation_manifest.v1`，`deployable=false`，`order_allowed=false`。
- Nautilus adapter sample：`adapter_scope=read_only_backtest_input_spike`，`deployable=false`，`order_allowed=false`。

## 8. 边界确认

- research-only：通过。
- deterministic offline sample：通过。
- walk-forward train/validation/test 分离：通过；warmup 可用于信号计算，但计分 returns 从对应 split start 后开始。
- test period locked before blind preference：通过。
- no paper/live trading：通过。
- no broker/account/secret artifact：通过。
- Nautilus adapter 只读样例：通过。
- `deployable=false`：由 schema 和 stage gate 断言。
- `order_allowed=false`：由 schema 和 stage gate 断言。
- `human_required=true`：由 schema 和 stage gate 断言。
- 边界关键词检索显示：`order_allowed=true` / `deployable=true` 只出现在负向测试、stage gate 禁止断言或文档禁用说明中；Phase 10 正向路径没有设置可部署或可下单。
- Phase 10 范围内 `paper trading`、`live trading`、`broker`、`secret`、`NautilusTrader` 命中均为禁止说明、残余风险说明或只读 adapter 样例说明。

## 9. 剩余风险

- Phase 10 使用确定性样本数据，不代表真实多年交易数据质量。
- NautilusTrader 只是 adapter input sample，未运行真实 BacktestEngine。
- 成本和压力测试是第一版工程验收模型，进入真实研究前需要替换为真实交易所数据和更严格执行模型。
- 十阶段完成后仍禁止直接进入实盘或自动下单。
