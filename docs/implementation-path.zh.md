# 总体实现路径优化

日期：2026-04-29

## 1. 当前本地参考源码

当前 `upstreams/` 已包含 11 个参考项目：

| 本地目录 | 项目 | 用途 |
| --- | --- | --- |
| `upstreams/nautilus_trader` | NautilusTrader | 主交易语义和事件驱动底座 |
| `upstreams/lean` | QuantConnect LEAN | 多市场生产引擎对照 |
| `upstreams/aat` | aat | Python async 原型分层参考 |
| `upstreams/QUANTAXIS` | QUANTAXIS | 中文市场、账户、Pub/Sub、A 股/期货参考 |
| `upstreams/hummingbot` | Hummingbot | crypto connector、做市、CEX/DEX gateway |
| `upstreams/freqtrade` | Freqtrade | crypto bot 生命周期、dry-run、Web UI、hyperopt |
| `upstreams/vectorbt` | vectorbt | 快速向量化研究、参数扫描 |
| `upstreams/openbb` | OpenBB | 金融数据入口、API server、agent 数据接口 |
| `upstreams/skfolio` | skfolio | 组合优化、风险、交叉验证、压力测试 |
| `upstreams/alphahunter` | alphahunter | asyncio 事件循环和策略回调参考 |
| `upstreams/aioquant` | aioquant | 极简 async I/O 事件框架参考 |

## 2. 优化后的架构取舍

### 不做“大一统框架”

这些项目不应该被拼成一个运行时。我们只吸收思想：

- NautilusTrader/LEAN：交易系统语义。
- Hummingbot/Freqtrade：crypto 连接器和 bot 运维。
- vectorbt：研究速度。
- OpenBB：数据入口。
- skfolio：组合风控。
- TradingAgents/FinRobot 思路：agent 角色分工。

### 主线保持

第一主线仍是：

```text
Python 3.12 advisory app
  -> deterministic data/signals/risk
  -> A2A agents
  -> daily report
  -> NautilusTrader adapter
```

LEAN 不是立即替代 NautilusTrader，而是 Phase 2 之后的对照实验。

## 3. 五条能力线

```text
Research lane      vectorbt / OpenBB
        |
        v
Signal lane        our deterministic strategies
        |
        v
Advisory lane      A2A agents + PydanticAI structured outputs
        |
        v
Risk lane          skfolio-inspired portfolio/risk gate
        |
        v
Execution lane     NautilusTrader first, LEAN as comparison, Hummingbot/Freqtrade as crypto ops references
```

职责边界：

- `vectorbt` 只负责快速研究，不进入实盘状态机。
- `OpenBB` 只作为数据入口参考，不承担交易语义。
- LLM agents 只给结构化意见，不拥有仓位和订单权限。
- `skfolio` 思路进入组合/风险层，决定仓位是否合法。
- NautilusTrader 保持为交易语义主线；LEAN 作为多资产对照；Hummingbot/Freqtrade 只借鉴 crypto connector 和运维体验。

## 4. 推荐代码实现阶段

### Stage A：核心 schema 和每日闭环

目标：不用真实模型、不接交易所，也能稳定生成日报。

参考文件：

- `upstreams/aat/aat/engine`
- `upstreams/aat/aat/strategy`
- `upstreams/nautilus_trader/nautilus_trader/model`
- `upstreams/nautilus_trader/nautilus_trader/risk`

我们要实现：

- `Event`
- `MarketSnapshot`
- `Signal`
- `AgentOpinion`
- `Recommendation`
- `RiskDecision`
- `DailyReport`

### Stage B：数据层和研究层

目标：能拉数据、存数据、做批量研究。

参考文件：

- `upstreams/openbb/openbb_platform`
- `upstreams/vectorbt/vectorbt`
- `upstreams/freqtrade/freqtrade/data`

我们要实现：

- `data/connectors`
- `data/storage`
- `data/features`
- `research/vectorized_backtest.py`

### Stage C：agent 层

目标：mock agents -> real model agents -> A2A server。

参考文件：

- `docs/roadmap.zh.md` 的 Agent 分工
- A2A Python SDK 文档
- PydanticAI 文档

我们要实现：

- `HistoricalContextAgent`
- `CritiqueAgent`
- `DecisionSynthesisAgent`
- `ReportAgent`
- `A2AClient/A2AServer` adapter

### Stage D：风险和组合层

目标：把“建议”变成“是否允许交易/允许多大仓位”。

参考文件：

- `upstreams/skfolio/src/skfolio`
- `upstreams/nautilus_trader/nautilus_trader/risk`

我们要实现：

- 单资产最大仓位。
- 日内/单日亏损限制。
- 波动率目标。
- 相关性/集中度限制。
- 风险拒绝原因。

### Stage E：交易引擎 adapter

目标：将我们的信号接入 NautilusTrader 回测，不进入实盘。

参考文件：

- `upstreams/nautilus_trader/nautilus_trader/backtest`
- `upstreams/nautilus_trader/nautilus_trader/trading`
- `upstreams/nautilus_trader/examples`
- `upstreams/lean/Algorithm.Python`
- `upstreams/lean/Engine`

我们要实现：

- `adapters/nautilus/instruments.py`
- `adapters/nautilus/data.py`
- `adapters/nautilus/strategy.py`
- `adapters/nautilus/backtest.py`

### Stage F：crypto execution 研究

目标：只在 paper trading 或人工确认订单草稿阶段研究。

参考文件：

- `upstreams/hummingbot/hummingbot/connector`
- `upstreams/hummingbot/hummingbot/strategy`
- `upstreams/freqtrade/freqtrade/exchange`
- `upstreams/freqtrade/freqtrade/rpc`

我们要实现：

- exchange capability matrix。
- order draft。
- paper execution log。
- human approval workflow。

## 5. 当前建议的第一批实现文件

```text
src/quant_agent_lab/
  core/schemas.py
  core/events.py
  data/storage.py
  data/features.py
  strategy/signals.py
  agents/base.py
  agents/mock.py
  decision/committee.py
  risk/gate.py
  reports/daily.py
  app/cli.py
tests/
  test_schemas.py
  test_risk_gate.py
  test_daily_pipeline.py
```

第一批实现不需要真实 API key，不需要交易所，不需要 NautilusTrader 编译成功。

## 6. 关键工程建议

- 先安装 Git，再把当前 zipball snapshot 替换成真正的 clone/submodule 或独立 `references/` 目录。
- 不要把上游项目作为我们包的一部分发布，避免许可证和体积问题。
- 用 `upstreams-manifest.json` 固定参考快照来源。
- 所有模型输出必须写审计日志。
- 所有风险规则必须有单元测试。
- agent 失败时系统输出“不足以建议交易”，而不是 fallback 到激进交易。

## 7. 下一步最合理的动作

下一步应该创建真正的 `src/quant_agent_lab` Python 项目骨架，先完成 Stage A：

1. 定义 Pydantic schema。
2. 实现 mock market data。
3. 实现一个确定性趋势信号。
4. 实现三个 mock agent opinion。
5. 实现 committee + risk gate。
6. 输出一份 Markdown daily report。

完成这一步后，我们再接真实数据和真实模型。

## 8. 2026-04-29 约束更新

根据最新路线评审，Stage A 进一步收窄：

- 不接真实交易引擎。
- 不接 A2A。
- 不接真实模型 API。
- 不接多市场。
- 不自动下单。
- 新增 `Data Validation Gate`，位于 Risk Gate 之前。
- `Decision Synthesis Agent` 改名为 `Recommendation Draft Agent`。
- recommendation schema 必须包含 `evidence_ids` 和 `order_allowed`。
- agent 失败和数据失败必须输出确定状态，不能让模型补猜。

详细约束见 `docs/advisory-core-spec.zh.md`。

## 9. 2026-04-29 Phase 1 进展

Phase 1 骨架已经实现并通过容器测试。当前具备：

- mock data source。
- CSV data source。
- Data Validation Gate。
- deterministic signal bundle。
- mock TypedAgents。
- Recommendation Draft。
- deterministic Risk Gate。
- Markdown report。
- JSON 审计文件和 JSONL 审计日志。

详细状态见 `docs/phase1-status.zh.md`。
