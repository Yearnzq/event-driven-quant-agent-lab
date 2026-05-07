# 十阶段实施路线图

日期：2026-05-03

## 工作节奏

项目按 10 个阶段推进，默认每天完成一个阶段。每天晚上进行人工审查：

- 如果当天阶段通过审查，下一天进入下一阶段。
- 如果当天阶段未通过审查，下一天继续修正当前阶段，不跳阶段。
- 每个阶段都必须有可运行命令、测试结果、产物路径和未完成风险说明。
- 阶段推进默认不自动提交，由人工审查后决定是否提交。

## 全局边界

- Phase 1 到 Phase 4 不自动下单。
- LLM/agent 不拥有仓位、订单、风控参数的最终控制权。
- 所有外部数据进入系统前必须有 schema、时间戳、来源和 evidence id。
- 所有建议都必须写审计产物，且 `order_allowed=false`，直到人工审批阶段明确引入。
- 每天只完成一个主要阶段，避免把数据、模型、回测、执行混在一次变更里。

## 十个阶段

| 阶段 | 名称 | 核心目标 | 当天验收重点 |
| --- | --- | --- | --- |
| 1 | 工程基线与离线可复现闭环 | 固化容器、测试、CLI、报告、mock/CSV 链路，形成后续九个阶段都能依赖的工程起点 | 离线测试全绿，sample CSV advisory 可复现，报告和审计产物存在，关键边界有自动断言 |
| 2 | 数据层硬化 | 统一行情、组合快照、文本证据、metadata、数据质量规则 | 数据 schema、metadata、bad data 样例、Data Gate 失败用例；联网下载失败降级从这里开始硬化 |
| 3 | Artifact 与审计账本 | 建立 run manifest、input/output hash、artifact catalog | 每次运行可追溯，可重放输入输出；Phase 1 只检查有基础审计产物，不提前实现完整账本 |
| 4 | 信号研究框架 | 把信号扩展为 registry、evaluation、research report | MA/突破/波动信号可比较，生成 JSON/Markdown 研究报告 |
| 5 | 风控规则增强 | 从单资产限制扩展到组合风险检查 | 最大仓位、现金缓冲、波动目标、回撤/亏损预算、拒绝测试；LLM 不能改风控阈值 |
| 6 | Advisory 决策层增强 | 强化 mock agent、committee、冲突处理、解释质量 | agent 失败降级、分歧解释、review/no_trade/insufficient_evidence 测试 |
| 7 | 模型接入边界准备 | 建 provider config、prompt registry、结构化输出、调用审计 | fake provider 测试、成本/延迟/哈希记录；不直接多模型并发 |
| 8 | 单模型真实 Agent | 接一个真实模型作为 Recommendation Draft Agent | 单模型日报、schema 校验、失败降级、成本/延迟记录；Data Gate/Risk Gate 仍是硬边界 |
| 9 | A2A 服务边界 | 把本地 agent 接口服务化，主应用作为 client | Agent Card、超时、重试、trace id、mock A2A server/client |
| 10 | 离线综合回测、鲁棒性验收与交易引擎适配前置 | 运行无人中途干预的 walk-forward 风格锦标赛，比较不同投资风格的样本外稳健性，同时做 NautilusTrader 只读/回测 adapter spike | strategy style tournament、walk-forward/stress/cost sensitivity 报告、simulation manifest、Nautilus adapter input sample、`deployable=false`、`order_allowed=false` |

## 阶段门禁

每个阶段结束时必须回答：

1. 新增了哪些用户可运行命令？
2. 新增或修改了哪些 schema？
3. 哪些行为被测试覆盖？
4. 哪些边界仍然禁止，例如下单、改风控参数、读原文？
5. 哪些联网或第三方能力属于 best-effort，失败时是否可豁免？
6. 当前阶段是否可以被延后一天继续修，不影响后续阶段？

## Phase 10：离线综合回测、鲁棒性验收与交易引擎适配前置

目标：在最终验收前，运行一次无人中途干预的离线综合模拟。系统使用过去几年历史数据，在固定数据切分、固定风控规则、固定交易成本和固定候选投资风格下，比较不同风格的样本外表现、风险调整收益、最大回撤、成本敏感性和鲁棒性。

该阶段不是让 AI 自由寻找历史收益最高策略，而是验证系统能否产生稳健、可审计、可复现的研究结论；同时建立 NautilusTrader adapter 的最小只读/回测前置，不进入实盘执行。

### 人工参与边界

- 模拟前：人工确认数据范围、候选风格、风控规则、成本模型、评分公式和 test period 锁定。
- 模拟中：人工不改参数、不换数据、不删结果、不根据 test 表现重跑到满意为止。
- 模拟后：人工审查报告，决定是否通过 Phase 10，以及是否进入下一轮 paper trading / sandbox 规划。

### 固定候选投资风格

第一版固定 5 到 7 类风格，不允许 AI 无限生成策略：

- `trend_following`
- `breakout`
- `mean_reversion`
- `volatility_regime`
- `momentum`
- `defensive_vol_target`
- `crypto_carry_or_funding`，crypto 专项，可选

偏稳健审查时，优先关注：

- `defensive_vol_target`
- `trend_following`
- `volatility_regime`
- `breakout`

均值回归可以保留，但必须额外检查极端行情下的尾部风险。

### 固定数据范围

第一版必须有：

- BTC/USDT 1h。
- BTC/USDT 1d。
- 成交量。
- 组合/现金快照。
- 手续费和滑点假设。

第二版再加：

- ETH/USDT。
- funding rate。
- open interest。
- SPY / QQQ / DXY / US10Y。
- 宏观事件日历。
- 新闻摘要 evidence。

暂时不直接加：

- 未清洗社媒原文。
- 网页全文。
- 新闻全文。
- LLM 自由搜索结果。
- 没有 `published_at` / `as_of` 的宏观数据。

### Walk-forward 切分

不要简单把过去几年整体跑一遍。Phase 10 使用固定 walk-forward 切分：

```text
Window 1:
2020-2021 train
2022 H1 validation
2022 H2 test

Window 2:
2021-2022 train
2023 H1 validation
2023 H2 test

Window 3:
2022-2023 train
2024 H1 validation
2024 H2 test

Window 4:
2023-2024 train
2025 H1 validation
2025 H2 test
```

核心规则：

- AI 和参数搜索只能看 train/validation。
- test period 只能最终跑一次。
- 不能根据 test 表现再改参数。
- 不能 shuffle 时间序列。
- 如果执行存在延迟，应使用 purge/lag 设计，避免过于乐观的执行假设。

### 稳健性评分，而不是收益率最高

最终排名不以 `total_return` 最大为唯一目标。第一版使用综合稳健评分：

```text
robust_score =
  0.20 * CAGR_rank
+ 0.20 * Sharpe_rank
+ 0.20 * Calmar_rank
+ 0.15 * max_drawdown_inverse_rank
+ 0.10 * downside_volatility_inverse_rank
+ 0.10 * stability_rank
+ 0.05 * turnover_cost_inverse_rank
```

报告必须区分：

- 收益率最高的风格。
- 风险调整后最好的风格。
- 最大回撤最低的风格。
- 样本外最稳定的风格。
- 成本最敏感的风格。
- 最不建议进入下一阶段的风格。

核心指标至少包括：

- `total_return`
- `CAGR`
- `volatility`
- `Sharpe`
- `Sortino`
- `Calmar`
- `max_drawdown`
- `drawdown_duration`
- `CVaR` / expected shortfall
- `turnover`
- `trade_count`
- `fee_paid`
- `slippage_cost`
- `win_rate`
- `profit_factor`
- `out_of_sample_return`
- `out_of_sample_sharpe`
- `parameter_stability`

### 成本敏感性

必须跑至少三组成本模型：

```text
low_cost:
fee_bps = 5
slippage_bps = 2

medium_cost:
fee_bps = 10
slippage_bps = 5

high_cost:
fee_bps = 20
slippage_bps = 10
```

如果一个风格只在低成本下有效，最终报告必须标记：

```json
{
  "cost_sensitive": true,
  "deployability": "not_recommended"
}
```

### 压力测试和扰动测试

Phase 10 不能只跑正常历史回测。必须加入：

- 成本上升测试。
- 随机滑点扰动。
- 数据缺失片段。
- 极端波动区间。
- 单日大跌/大涨冲击。
- 延迟执行一根 K 线。
- 信号滞后。
- 参数微扰。

目标不是找到历史曲线最好看的风格，而是找到：

- 参数稍微变化仍然稳定的风格。
- 成本提高后仍然能活的风格。
- 极端行情不会爆的风格。
- 样本外不明显退化的风格。

### AI blind preference check

Phase 10 增加 AI 盲测机制：

1. 系统锁定 test period。
2. AI 只能看到 train/validation 的摘要。
3. AI 先给出更稳健的风格偏好。
4. 系统再跑 test。
5. 报告比较 AI 的预判和实际样本外表现。

结构化输出示例：

```json
{
  "ai_preferred_style_before_test": "defensive_vol_target",
  "reason": [
    "lower validation drawdown",
    "less cost sensitive",
    "more stable across windows"
  ],
  "actual_best_oos_style_by_robust_score": "trend_following",
  "ai_preferred_style_rank_oos": 2,
  "match": false
}
```

### Phase 10 必须完成

1. 建立 strategy style registry。
2. 建立 walk-forward split。
3. 锁定数据版本、schema 版本、strategy 版本和 risk config。
4. 固定交易成本模型和滑点模型。
5. 跑 train/validation/test 分离的样本外测试。
6. 跑成本敏感性测试。
7. 跑压力测试和参数扰动测试。
8. 运行 AI blind preference check。
9. 生成 `strategy_style_tournament.md`。
10. 生成 `strategy_style_tournament.json`。
11. 生成 `walk_forward_results.json`。
12. 生成 `stress_test_results.json`。
13. 生成 `cost_sensitivity_results.json`。
14. 生成 `simulation_manifest.json`。
15. 生成 `adapter_input_sample.json`。
16. 确认 `order_allowed=false`。
17. 确认 `deployable=false`。
18. 确认报告标注 research/advisory-only。

### Phase 10 最终产物

```text
artifacts/research/strategy_style_tournament.md
artifacts/research/strategy_style_tournament.json
artifacts/research/walk_forward_results.json
artifacts/research/stress_test_results.json
artifacts/research/cost_sensitivity_results.json
artifacts/audit/simulation_manifest.json
artifacts/adapters/nautilus/adapter_input_sample.json
```

最终 JSON 至少包含：

```json
{
  "phase": 10,
  "simulation_type": "offline_walk_forward_strategy_style_tournament",
  "human_intervention_during_run": false,
  "data_start": "2020-01-01",
  "data_end": "2026-05-03",
  "styles_tested": [
    "trend_following",
    "breakout",
    "mean_reversion",
    "volatility_regime",
    "defensive_vol_target"
  ],
  "best_total_return_style": "breakout",
  "best_risk_adjusted_style": "defensive_vol_target",
  "lowest_drawdown_style": "defensive_vol_target",
  "most_stable_oos_style": "trend_following",
  "recommended_next_research_style": "defensive_vol_target",
  "deployable": false,
  "order_allowed": false,
  "human_required": true,
  "reason_not_deployable": [
    "research-only phase",
    "no paper trading validation",
    "single venue data",
    "limited cost model",
    "requires human review"
  ]
}
```

### Phase 10 禁止事项

- 不自动下单。
- 不进入 paper/live trading。
- 不允许 AI 根据 test set 修改参数。
- 不允许 AI 绕过 Data Gate 或 Risk Gate。
- 不允许使用未经清洗的新闻/网页正文。
- 不允许把收益率最高策略直接标记为可部署。
- 不把 NautilusTrader 变成完整实盘执行系统；本阶段只做 adapter spike。

### 外部依据

- NautilusTrader 的 backtesting 概念说明：`BacktestEngine` 处理历史数据流，数据耗尽后产出结果和性能指标，适合最终历史模拟和分析。
- NautilusTrader overview 说明其系统覆盖 research、deterministic simulation、live execution，Python 作为策略和编排控制面；这支持我们把 Nautilus 放到交易引擎适配前置，而不是阶段 1。
- QuantConnect research guide 提醒 overfitting 和 look-ahead bias 风险，并建议 walk-forward optimization、out-of-sample 测试、point-in-time data 或 reporting lag。
- skfolio `WalkForward` 明确用于时间序列 train/test split，test index 必须晚于之前索引，时间序列交叉验证不应 shuffle，并支持 purge 来控制执行延迟/前视风险。

## 今日阶段 1：工程基线与离线可复现闭环

目标：把当前项目整理成一个后续九个阶段都能依赖的工程起点。今天不做大架构变更，不接真实模型，不接 A2A，不接 NautilusTrader，不接交易执行。

阶段 1 不证明系统“功能完整”，只证明系统已经“可复现、可审查、边界清楚、离线稳定”。

### 今日必须完成：离线必过项

1. 确认容器 `quant-agent-lab` 可进入。
2. 确认 conda 环境 `quant` 可激活，并记录 `python --version`。
3. 确认 `python -m pytest -q` 通过。
4. 确认 `python -m compileall -q src` 通过。
5. 固化 mock advisory pipeline。
6. 固化 sample CSV advisory pipeline。
7. 固化 CSV metadata 自动加载。
8. 固化离线信号评估 smoke test。
9. 固化新闻/网页 JSONL 清洗 smoke test。
10. 确认 CLI 产物路径清楚：
    - reports
    - research
    - evidence
    - audit
11. 自动断言报告中明确写 advisory-only。
12. 自动断言 Phase 1 所有建议 `order_allowed=false`。
13. 自动断言清洗后的文本证据不包含原始正文、HTML 或 `content` 字段。

### 今日 best-effort 项

1. GitHub SSH 可访问，但不自动 commit/push。
2. Binance 公开 Kline 下载可尝试。
3. 如果 Binance 下载失败，记录为 `WAIVED_NETWORK_FAILURE`，不阻塞阶段 1；阶段 2 继续补网络失败降级和多数据源策略。

### 今日不做

- 不接真实模型 API。
- 不接 A2A。
- 不接 NautilusTrader。
- 不做 paper trading。
- 不自动下单。
- 不引入真实交易所 API key。
- 不让 LLM/agent 修改风控参数。
- 不把新闻/网页原文直接进入 agent。
- 不实现完整 artifact catalog/hash ledger；该内容留到 Phase 3。

### 今日验收命令

离线必过：

```bash
python --version
python -m pytest -q
python -m compileall -q src
python scripts/stage_01_gate.py
```

联网 best-effort：

```bash
python scripts/stage_01_gate.py --try-binance
ssh -T -o BatchMode=yes git@github.com || true
```

### 今日验收标准

- 离线必过项全部通过。
- Binance 下载成功则纳入审查产物；失败则必须明确记录 `BINANCE_CHECK=WAIVED_NETWORK_FAILURE`，但不阻塞阶段 1。
- README、路线文档和审查清单足以让人工复现阶段 1。
- 工作区保留给人工审查，不自动 commit/push。

### 今日风险

- Binance 公共接口可能因网络、地区、DNS、限流等原因失败；它不作为阶段 1 硬门禁。
- 当前环境是 Python 3.10 + Conda。NautilusTrader 官方支持 Python 3.12-3.14，并推荐 vanilla CPython/uv；该差异记录为第 10 阶段交易引擎适配前置评估，不在阶段 1 解决。
- 目前研究评估是简化版 MA crossover，不代表可交易策略，只作为 research lane 的最小 smoke test。
