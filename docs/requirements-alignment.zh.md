# 系统需求对齐

日期：2026-05-03

## 系统定位

本系统第一轮不是自动交易系统，而是事件驱动量化 advisory lab。

它负责：

1. 收集和校验数据。
2. 生成确定性信号。
3. 调用 agent 做历史上下文、反方分析和建议草稿。
4. 通过 deterministic Data Gate 和 Risk Gate。
5. 输出可审计日报。
6. 在最终阶段做离线综合回测与鲁棒性验收。
7. 为后续 paper trading / NautilusTrader adapter / 人工审批订单草稿打基础。

它明确不负责：

1. 不自动下单。
2. 不直接实盘。
3. 不让 LLM 管仓位。
4. 不让 LLM 改风控。
5. 不保证收益。
6. 不把历史回测最优策略直接上线。
7. 不直接读取未经清洗的网页/新闻/社媒全文。

## 能力需求对齐表

| 需求 | 当前路线是否满足 | 对应阶段 | 说明 |
| --- | --- | --- | --- |
| 每日生成投资建议 | 满足 | Phase 1 / 6 / 8 | 先 mock，再真实模型 |
| 人工审查后再决定是否交易 | 满足 | 全阶段 | `human_required=true` |
| 初期不自动下单 | 满足 | Phase 1-10 | `order_allowed=false` |
| 使用事件驱动交易系统思想 | 满足 | Phase 4 / 10 | NautilusTrader adapter 后置 |
| 先从 crypto / BTC-USDT 开始 | 满足 | Phase 1-2 | 后续可扩多资产 |
| 可扩展到美股、期货、大宗、宏观 | 部分满足 | Phase 2 / 10 后 | 需要后续数据源和 broker adapter |
| 多模型 agent：长上下文、分析、综合 | 满足 | Phase 6-8 | 模型角色不写死供应商 |
| A2A agent 服务化 | 满足 | Phase 9 | 本地接口稳定后再服务化 |
| 确定性风控，不让 LLM 改参数 | 满足 | Phase 5 | 风控为 hard gate |
| 数据可追溯：source/timestamp/evidence_id | 满足 | Phase 2-3 | 是数据层硬门禁 |
| 新闻/网页不直接喂原文 | 满足 | Phase 2 / 6 | 只用清洗摘要和 evidence |
| 本地存储和审计 | 满足 | Phase 3 | manifest/hash/catalog |
| 策略研究和信号比较 | 满足 | Phase 4 | signal registry + research report |
| 最终离线回测和鲁棒性验收 | 满足 | Phase 10 | 本次新增最终 gate |
| 最终找稳健投资风格，而不是最高收益 | 满足 | Phase 10 | 使用 `robust_score` |
| 可接真实模型 API | 满足 | Phase 7-8 | 先单模型，不多模型并发 |
| 可服务化 agent | 满足 | Phase 9 | A2A server/client |
| 可接 NautilusTrader | 部分满足 | Phase 10 | 只做 adapter 前置，不做完整实盘 |
| 可进入 paper trading | 不在当前 10 阶段内 | Phase 11+ | 需要下一轮计划 |
| 可自动实盘下单 | 当前明确不满足 | 不做 | 这是刻意禁止，不是缺陷 |
| Web UI / dashboard | 当前不满足 | 后续 | 当前只做 CLI + Markdown/HTML |
| 多账户、多交易所真实执行 | 当前不满足 | 后续 | 需要独立执行阶段 |
| 合规/权限/灾难开关 | 当前只做前置 | 后续 | 自动下单前必须补 |

## 需求分歧警戒线

如果未来出现以下倾向，必须暂停阶段推进并重新对齐需求：

- 想把 `order_allowed=false` 提前改成 `true`。
- 想让 LLM 直接生成交易订单。
- 想让 LLM 修改风控阈值。
- 想把 Phase 10 回测最优风格直接标记为可部署。
- 想把未清洗新闻、网页、社媒原文直接塞给 agent。
- 想在没有 audit/manifest 的情况下运行真实模型或交易 adapter。

## 当前 10 阶段外的能力

以下能力不是当前 10 阶段目标，可以作为 Phase 11+ 规划：

- paper trading。
- 人工审批订单草稿。
- Web dashboard。
- 多账户/多交易所真实执行。
- 自动实盘下单。
- 合规权限系统。
- 灾难开关和执行权限隔离。

## Phase 10 新增需求确认

最终离线模拟测试加入 Phase 10，定位为：

```text
offline walk-forward strategy style tournament
```

它用于验证系统是否能产生稳健、可审计、可复现的研究结论，而不是让 AI 自由挑历史收益最高策略。

必须保持：

- `deployable=false`
- `order_allowed=false`
- `human_required=true`
- research/advisory-only

人工参与方式：

- 模拟前冻结规则。
- 模拟中不干预。
- 模拟后审查结果。
