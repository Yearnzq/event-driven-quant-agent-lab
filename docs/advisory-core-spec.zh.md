# Advisory Core 工程约束规格

日期：2026-04-29

## 1. 最终工程判断

系统原则改成更严格的一句话：

> 只选一个“权威交易/回测状态系统”，其他项目只吸收思想、接口形态和模块设计；LLM/A2A 只能做 advisory，不进入订单、账户、风控的最终控制面。

这意味着：

- NautilusTrader 是未来目标交易/回测/模拟/实盘语义主线。
- LEAN 是严肃对照，不是当前主线。
- Hummingbot/Freqtrade 只参考 crypto connector 和 bot ops。
- vectorbt/OpenBB/skfolio 是 sidecar，不是交易状态系统。
- LLM 只能生成分析、反证和 recommendation draft。
- 最终权限属于 deterministic gates + human approval。

## 2. Phase 1 边界

Phase 1 明确不接：

- 不接真实交易引擎。
- 不接 A2A。
- 不接多市场。
- 不接真实模型 API。
- 不自动下单。
- 不做 paper trading。
- 不让 LLM 影响仓位和风控参数。

Phase 1 只验证：

- 数据 schema。
- 数据质量检查。
- 确定性信号。
- mock agent。
- recommendation draft。
- validation gate。
- risk gate。
- audit log。
- Markdown daily advisory report。

MVP 范围：

```text
市场：BTC/USDT
周期：1h + 1d
数据：OHLCV + 当前持仓快照
存储：DuckDB + Parquet
策略：趋势 + 波动率 + 简单突破
模型：mock agents
输出：Markdown daily advisory report
交易：禁止下单
```

验收标准：

- 同一份输入，多次运行输出一致。
- 所有建议都有 `evidence_ids`。
- 所有 agent 输出都能 schema validate。
- Data Gate 失败时输出 `insufficient_evidence`。
- Risk Gate 能拒绝高风险建议。
- 模型/agent 冲突时输出 `hold` 或 `review_required`。
- 日报能解释为什么 buy/sell/hold/review。

## 3. Agent 命名和权限

原 `Decision Synthesis Agent` 改名为：

```text
Recommendation Draft Agent
```

原因：避免系统语义上默认 LLM 拥有决策权。

推荐角色：

| Agent | 模型选择方式 | 权限 |
| --- | --- | --- |
| Historical Context Agent | long-context capable model | 只做历史上下文和相似场景归纳 |
| Critique Agent | strong analysis / counterargument model | 只做反证、风险和信息缺口 |
| Recommendation Draft Agent | strong structured reasoning model | 只生成 recommendation draft |
| Report Agent | cost-effective writing model | 只生成可读日报 |

模型品牌不能写死进系统逻辑。配置应是：

```text
role -> provider/model config
```

而不是：

```text
Gemini == 历史
Claude == 分析
GPT == 决策
```

## 4. 必须新增 Data Validation Gate

Risk Gate 前必须有：

```text
Data Validation Gate
```

它负责判断：

- 行情数据是否过期。
- K 线是否缺失。
- 交易所数据是否断档。
- 新闻/宏观数据是否有 `published_at`。
- 持仓数据是否和账户快照一致。
- agent 输入是否完整。
- evidence 是否可追踪。

如果 Data Gate 失败，系统直接输出：

```text
insufficient_evidence
```

不能让模型补猜。

## 5. Recommendation Schema 增强

核心字段：

```json
{
  "recommendation_id": "2026-04-29-BTC-USDT-001",
  "symbol": "BTC-USDT",
  "action": "hold",
  "target_position_pct": 0.0,
  "max_loss_budget_pct": 0.0,
  "confidence": 0.62,
  "evidence_ids": [
    "ohlcv:okx:btc-usdt:1h:2026-04-29",
    "signal:trend:v1"
  ],
  "data_quality": "pass",
  "model_disagreement": "medium",
  "risk_gate": "pass",
  "risk_gate_reason": [],
  "human_required": true,
  "order_allowed": false
}
```

最重要的字段：

- `evidence_ids`：用于审计和回溯。
- `order_allowed`：明确区分 advisory 和 order。
- `human_required`：第一阶段必须恒为 `true`。

## 6. 新闻/网页输入约束

Agent 不应直接读取全量新闻正文、网页正文、社媒原文或评论区。

外部文本必须先经过 deterministic cleaning / extraction，只保留：

```text
source
published_at
title
summary
entities
market_relevance
url
content_hash
```

然后再进入 agent 上下文。

## 7. 模型失败降级硬规则

失败规则必须写成代码和测试：

| 失败点 | 系统行为 |
| --- | --- |
| Data Gate 失败 | `insufficient_evidence` |
| Historical Context Agent 失败 | 允许继续，但标记 `context_missing` |
| Critique Agent 失败 | 不允许输出 buy/sell，只能 hold/review |
| Recommendation Draft Agent 失败 | 不生成 recommendation |
| Schema validation 失败 | 不生成 recommendation |
| Risk Gate 失败 | `no_trade` |
| Agent 之间严重冲突 | `review_required` |

系统默认应该拒绝交易，而不是默认通过。

## 8. 真实模型接入顺序

Phase 2 不要一开始三模型并发。

推荐顺序：

1. 先接一个模型，跑通 schema、日志、成本、失败降级。
2. 再接第二个模型做 critique。
3. 最后接 long-context historical agent。

每次模型调用必须记录：

```text
model_provider
model_name
prompt_version
schema_version
input_hash
output_hash
latency_ms
cost_estimate
temperature
tool_calls
validation_result
```

## 9. A2A 延后原则

A2A 是 Phase 3 的服务化协议，不是 Phase 1 的 MVP 依赖。

阶段顺序：

```text
Phase 1: 本地 TypedAgent 接口 + mock agents
Phase 2: PydanticAI + real model agents
Phase 3: a2a-python server/client
```

A2A 上线后，主应用作为 A2A client 调用各 agent。不要让 agent 之间自由互相调用，避免形成不可控 agent mesh。

## 10. Nautilus Adapter 原则

不要把业务对象直接改成 Nautilus 内部对象。用 adapter：

```text
our SignalEvent       -> Nautilus custom data / strategy input
our Instrument        -> Nautilus Instrument
our PortfolioSnapshot -> Nautilus Portfolio read model
our Recommendation    -> no direct order
our OrderDraft        -> Nautilus order only after human approval
```

Nautilus 是目标执行/回测引擎，不是 Phase 1 的业务应用框架。

## 11. 风控硬规则

必须遵守：

```text
LLM 不能改风险参数
LLM 不能直接创建真实订单
LLM 不能绕过 Risk Gate
LLM 不能在 Data Gate 失败时硬猜
LLM 不能把 confidence 当作 position size
Risk Gate 默认拒绝，而不是默认通过
模型冲突时默认 hold/review，而不是强行交易
```

## 12. 最短实现路径

```text
Phase 1: pure Python advisory core
Phase 2: real model agents with PydanticAI
Phase 3: A2A service boundary
Phase 4: Nautilus adapter
Phase 5: paper trading / human approval order draft
```

当前最短路径：

> 先做一个每天稳定生成 BTC/USDT 建议的系统，不做“全球市场 + 多模型 + 多框架 + 多 agent + 多交易所”的系统。
