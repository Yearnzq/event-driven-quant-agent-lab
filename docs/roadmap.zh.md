# Event-Driven Quant Agent 路线规划

日期：2026-04-29

## 0. 总体结论

我们的方向应该是：

> **选一个主事件驱动交易系统作为底座，LLM/A2A 作为研究与决策建议层，不让模型绕过确定性的交易、风控和审计边界。**

第一阶段不做自动下单，先做每日 advisory 系统：输入行情、持仓、宏观/新闻/链上信息，输出结构化建议和日报，由人工决定是否执行。

## 1. 五个上游项目简表

| 项目 | 定位 | 优点 | 主要风险/不足 | 我们借鉴什么 | 是否做主框架 |
| --- | --- | --- | --- | --- | --- |
| NautilusTrader | 生产级多资产交易引擎 | Rust 核心、Python 策略、确定性事件模型、回测/实盘一致、模块完整 | 学习和工程接入成本最高；Windows/Rust 构建环境要提前验证；LGPL-3.0-or-later 需要合规处理 | 事件模型、领域对象、portfolio/risk/execution 边界、回测实盘一致性 | **推荐主框架** |
| aat | Python-first 异步交易框架 | 结构清晰，Trading/Risk/Execution/Backtest 分层明确，适合快速理解和原型 | 生态和生产成熟度弱于 NautilusTrader；连接器和资产覆盖要补 | 策略回调、引擎分层、轻量原型 | 备选原型框架 |
| QUANTAXIS | 中文量化全流程框架 | 中文生态、A 股/期货工作流、账户/数据/回测/可视化模块全 | 代码体量大，历史包袱较重；若主战场不是 A 股，收益下降 | A 股/期货流程、账户模型、本地化数据链路、Pub/Sub 思路 | 中国市场专项备选 |
| alphahunter | asyncio 事件驱动做市/交易框架 | Python 原生 asyncio，轻量，策略/网关回调直观 | 依赖较老，生产维护风险高；更像参考实现 | async I/O、做市策略结构、事件中心 | 不做主框架 |
| aioquant | asyncio 事件 I/O 驱动框架 | 极简 async 结构，市场/交易/定时任务模块容易读 | 维护和生产完整度有限；适合作为设计参考 | 轻量事件循环、任务调度、交易所适配风格 | 不做主框架 |

## 2. 主框架选择

### 选择：NautilusTrader

原因：

1. 我们最终目标不是只生成一个聊天建议，而是要逐步接近真实交易系统。NautilusTrader 已经把交易系统最难的几个边界放好了：event model、portfolio、risk、execution、backtest、live。
2. 它的核心是 Rust，策略控制面是 Python，正好符合“底层可靠、上层快速迭代”的需求。
3. 未来如果从人工建议走到模拟盘、纸交易、再到人工确认下单，NautilusTrader 的 research-to-live parity 价值会很高。

### 现实约束

第一阶段不要直接改 NautilusTrader 核心。我们先把自己的系统作为外层 advisory app：

```text
our advisory app
  -> normalized data/events
  -> strategy signals
  -> model agents
  -> decision/risk/report
  -> NautilusTrader adapter, initially read/backtest only
```

这样可以避免一开始就被 NautilusTrader 的构建和内部扩展复杂度拖住。

### 备选路径

如果 NautilusTrader 在当前 Windows 环境构建困难，第一阶段可以用 aat 的分层思想做轻量 Python 原型，但领域模型和接口仍按 NautilusTrader 的严格边界设计，避免未来迁移重写。

## 3. 技术栈决策

### 实现语言

- **主语言：Python 3.12**
- **底层交易引擎：复用 NautilusTrader 的 Rust/Python 包，不主动写 Rust**
- **后续 UI：FastAPI + 前端可选 React/Next.js，第一阶段只输出 Markdown/HTML 日报**

选择 Python 3.12 的原因：

- NautilusTrader 当前包声明支持 Python `>=3.12,<3.15`。
- agent、数据处理、日报、API 集成都以 Python 生态更快。
- Pydantic/FastAPI/asyncio/A2A SDK 都能自然接入。

### A2A / Agent 框架

采用分层选择：

| 层 | 选择 | 用途 |
| --- | --- | --- |
| Agent-to-Agent 协议 | **A2A Protocol + a2a-python SDK** | 让 Gemini 历史上下文 agent、Claude 分析 agent、GPT 综合 agent 可以作为独立服务暴露能力 |
| 单个 agent 的模型调用与结构化输出 | **PydanticAI** | 统一 OpenAI、Anthropic、Gemini 等模型；强制输出 Pydantic schema；便于单元测试和 eval |
| 工作流编排 | 第一阶段用我们自己的 async workflow；复杂后再引入 LangGraph | 每日任务链路很固定，先避免过重编排；如果后续需要 durable execution/human-in-loop 状态机，再引入 LangGraph |
| 工具访问 | 后续可补 MCP | MCP 适合 agent 调工具/数据库/API；A2A 适合 agent 和 agent 协作，两者不是替代关系 |

采用 A2A SDK 的原因：

- A2A 官方文档定义的是 agent 间协作协议，适合多个独立 agent 服务协同。
- `a2a-python` 官方 SDK 支持 async Python、HTTP/FastAPI/Starlette、gRPC、OpenTelemetry 和 SQL 后端。
- 这比自己定义 HTTP endpoint 更利于未来和外部 agent 互通。

PydanticAI 的定位不是替代 A2A，而是实现每个 agent 内部的模型调用、schema 校验和输出类型约束。

## 4. Agent 分工

| Agent | 模型倾向 | 输入 | 输出 | 约束 |
| --- | --- | --- | --- | --- |
| Historical Context Agent | Gemini 长上下文 | 历史行情、前序日报、宏观/新闻时间线、仓位变化 | 市场状态、历史相似情景、长期风险 | 只做上下文和历史归纳，不直接给订单 |
| Analysis/Critique Agent | Claude | 当前信号、上下文摘要、风险因素 | 反方观点、下行情景、信息缺口 | 必须列出不确定性和反证 |
| Decision Synthesis Agent | GPT | 策略信号、两个 agent 输出、组合状态 | 结构化 recommendation draft | 不拥有最终权限 |
| Risk Gate | deterministic code | recommendation draft、账户/仓位/波动率/流动性 | pass/reject/resize | 不能由 LLM 覆盖 |
| Report Generator | GPT 或本地模板 | 最终建议、审计轨迹 | Markdown/HTML daily report | 必须引用结构化字段 |

最终建议对象示例：

```json
{
  "date": "2026-04-29",
  "symbol": "BTC-USDT",
  "action": "hold",
  "target_position_pct": 0.0,
  "confidence": 0.62,
  "time_horizon": "1d-3d",
  "rationale": ["trend mixed", "event risk elevated"],
  "invalidation": ["daily close above resistance", "funding normalizes"],
  "risk_flags": ["high_volatility", "macro_event"],
  "risk_gate": "pass",
  "human_required": true
}
```

## 5. 初版系统边界

第一阶段系统只做这些事：

1. 从一个市场开始，例如 BTC/USDT。
2. 拉取日线/小时线数据，保存到 Parquet/DuckDB。
3. 计算一两个确定性策略信号，例如趋势、波动率、突破、均线。
4. 用 mock agent 先跑通 A2A 风格接口和结构化输出。
5. 生成 recommendation draft。
6. 通过 deterministic risk gate。
7. 输出 daily report。

第一阶段明确不做：

- 不自动下单。
- 不追逐高频。
- 不直接把新闻全文无过滤塞给模型。
- 不让 LLM 修改风控参数。
- 不用多个交易引擎并行维护账户状态。

## 6. 建议代码结构

```text
src/quant_agent_lab/
  core/
    events.py              # 标准事件模型
    schemas.py             # Pydantic typed objects
    clock.py               # 时间、交易日、时区
  data/
    loaders.py             # 行情/新闻/宏观加载
    storage.py             # DuckDB/Parquet
    features.py            # 技术指标和特征
  strategy/
    base.py
    signals.py             # 确定性策略信号
  agents/
    base.py
    historical_context.py
    critique.py
    decision.py
    a2a_server.py
  decision/
    committee.py           # 汇总和冲突处理
    recommendation.py
  risk/
    limits.py
    gate.py
  reports/
    daily.py
    templates/
  adapters/
    nautilus/
      backtest.py
      instruments.py
      signals.py
  app/
    cli.py
    api.py                 # 后续 FastAPI
tests/
```

## 7. 阶段路线

### Phase 0：工程地基

- 安装 Git，重新把本仓库变成真正的 git repo。
- 建 Python 3.12 项目，使用 `uv` 或 `poetry` 管理依赖。
- 加 `ruff`、`mypy/pyright`、`pytest`。
- 定义核心 Pydantic schema：Event、Signal、AgentOpinion、Recommendation、RiskDecision、DailyReport。

### Phase 1：每日建议闭环

- 单市场数据管道：BTC/USDT 日线 + 小时线。
- DuckDB/Parquet 本地存储。
- 一个确定性信号策略。
- 三个 mock agent。
- deterministic risk gate。
- Markdown 日报。

验收标准：不用真实模型，也能每天稳定生成一份结构化建议和报告。

### Phase 2：真实模型接入

- 用 PydanticAI 接入 Gemini、GPT、Claude。
- 对每个 agent 强制结构化输出。
- 做 token/cost/latency 记录。
- 所有 prompt、输入、输出、版本号写入审计日志。
- 增加失败降级：某个模型失败时输出 `insufficient_evidence`，而不是硬猜。

### Phase 3：A2A 服务化

- 把三个 agent 包成 A2A server。
- 主应用作为 A2A client 调用它们。
- 加 Agent Card、能力描述、超时、重试、trace id。
- 引入 OpenTelemetry。

### Phase 4：NautilusTrader 适配

- 用 NautilusTrader 做回测/模拟层。
- 把我们的 deterministic signals 转成 NautilusTrader 策略输入。
- 不改核心引擎，先写 adapter。
- 验证研究/回测/报告输出的一致性。

### Phase 5：组合与人工审批

- 多标的、多策略、多 agent opinions。
- 仓位级风险：最大单资产权重、行业/币种相关性、最大回撤、VaR/vol targeting。
- 报告里加入“建议原因、反方观点、风险拒绝原因、需要人工确认的问题”。
- 如果接交易所，也只做 paper trading 或人工确认订单草稿。

## 8. 额外必须考虑的问题

### 数据和回测

- 避免未来函数和数据泄漏。
- 明确每条数据的时间戳、可见时间、来源版本。
- 新闻/宏观数据必须有发布时间，不只用事件发生时间。
- 回测时模型输出要冻结，不能每次用当前模型重跑历史。

### 风控

- LLM 不能改风险阈值。
- 风控失败时只能输出“不建议交易”或“需要人工复核”。
- 风险规则需要单元测试和场景测试。

### 安全

- 新闻、社媒、网页内容会有 prompt injection。
- agent 工具权限必须最小化。
- API key 只能放 `.env` 或密钥管理，不进入日志和报告。
- 外部 agent 返回内容必须做 schema 校验。

### 合规与审计

- 每次建议都要保存输入、模型、prompt 版本、输出、风险决策和人工动作。
- 日报应标注“辅助决策，不构成自动交易指令”。
- 如果未来涉及自动下单，需要单独做权限、合规和灾难开关。

### 工程环境

- 当前机器没有可用 `git.exe`，后续正式开发前要安装 Git。
- NautilusTrader 可能要求 Rust/Python 3.12+ 构建环境；如果 Windows 直接构建不顺，优先使用 WSL2 或 Docker。
- 上游源码当前是 zipball snapshot，不带 git history。正式实现前建议重新 clone。

## 9. 当前决策记录

| 决策 | 结果 |
| --- | --- |
| 主框架 | NautilusTrader |
| 快速原型思想来源 | aat |
| 中文/A 股专项参考 | QUANTAXIS |
| async 轻量参考 | alphahunter、aioquant |
| 主语言 | Python 3.12 |
| 模型/agent 实现 | PydanticAI |
| agent 间协议 | A2A Protocol + a2a-python SDK |
| 初期编排 | 自研 async workflow |
| 后续复杂编排备选 | LangGraph |
| 初期存储 | DuckDB + Parquet |
| 初期产物 | Markdown/HTML daily advisory report |
| 下单策略 | 第一阶段不自动下单，人工确认 |

## 10. 参考链接

- A2A Protocol: https://a2a-protocol.org/latest/
- A2A Python SDK: https://github.com/a2aproject/a2a-python
- PydanticAI: https://pydantic.dev/docs/ai/overview/
- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- NautilusTrader: https://github.com/nautechsystems/nautilus_trader
- aat: https://github.com/AsyncAlgoTrading/aat
- QUANTAXIS: https://github.com/QUANTAXIS/QUANTAXIS
- alphahunter: https://github.com/phonegapX/alphahunter
- aioquant: https://github.com/paulran/aioquant
- QuantConnect LEAN: https://github.com/QuantConnect/Lean
- Hummingbot: https://github.com/hummingbot/hummingbot
- Freqtrade: https://github.com/freqtrade/freqtrade
- vectorbt: https://github.com/polakowo/vectorbt
- OpenBB: https://github.com/OpenBB-finance/OpenBB
- skfolio: https://github.com/skfolio/skfolio

## 11. 2026-04-29 路线更新

第二批参考项目已经拉取到本地：

- `upstreams/lean`
- `upstreams/hummingbot`
- `upstreams/freqtrade`
- `upstreams/vectorbt`
- `upstreams/openbb`
- `upstreams/skfolio`

更新后的总体路径见 `docs/implementation-path.zh.md`。路线不推翻 NautilusTrader 主线，但新增五条能力线：`Research lane`、`Signal lane`、`Advisory lane`、`Risk lane`、`Execution lane`。第一阶段仍先做 pure Python advisory core，之后再分别接 OpenBB/vectorbt/skfolio 思路、NautilusTrader adapter、LEAN 对照实验和 crypto execution 研究。

## 12. 2026-04-29 工程约束更新

路线评审后，Phase 1 明确改为：

> 不接真实交易引擎、不接 A2A、不接多市场、不自动下单；先验证数据、schema、信号、agent mock、Data Validation Gate、Risk Gate、日报和审计闭环。

同时做以下语义调整：

- `Decision Synthesis Agent` 改名为 `Recommendation Draft Agent`。
- Risk Gate 前新增 `Data Validation Gate`。
- recommendation schema 增加 `recommendation_id`、`evidence_ids`、`data_quality`、`model_disagreement`、`risk_gate_reason`、`order_allowed`。
- A2A 延后到 Phase 3。
- PydanticAI 延后到 Phase 2；Phase 1 只做本地 `TypedAgent` 接口和 mock agents。
- 失败降级成为硬规则：Data Gate 失败必须 `insufficient_evidence`，Risk Gate 失败必须 `no_trade`，agent 严重冲突必须 `review_required`。

完整约束见 `docs/advisory-core-spec.zh.md`。
