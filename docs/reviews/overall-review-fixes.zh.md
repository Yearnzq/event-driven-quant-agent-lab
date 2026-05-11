# Overall Review Fixes

日期：2026-05-07

## 结论

整体 review 中列出的当前代码内可修复项已处理。项目仍保持 advisory-only：

- `order_allowed=false`
- `human_required=true`
- `deployable=false`，仅 Phase 10 research 产物适用
- 不接 broker/account/private API key
- 不进入 paper/live trading

## 已修复

- 时间戳可复现性：
  - `utc_now()` 不再读取系统实时时间。
  - audit/catalog/manifest `created_at` 由 pipeline `market.as_of`、research `generated_at` 或固定 epoch 注入。
  - pipeline hash 排除了 `output_dir`，相同输入写入不同目录时 audit hash 稳定。
- CSV fail-closed：
  - CSV 文件缺失、空数据或 schema 解析失败时，pipeline 生成 fail-closed advisory result。
  - 该路径仍写出 report、audit、audit-log、artifact catalog 和 run manifest。
- 模型审计元信息：
  - `AuditRecord` 与 `RunManifest` 写入实际执行路径的 model provider / model name / prompt version。
  - 单模型 fake/openai、A2A 和 mock agent 路径不再全部显示为默认 mock。
- A2A mock 确定性：
  - 移除真实 sleep/thread timeout 依赖。
  - mock timeout 由 `response_delay_seconds > timeout_seconds` 的确定性分支触发。
  - A2A trace `created_at` 使用请求时间。
- 边界测试写法：
  - 测试不再直接硬编码启用下单权限的字面量。
  - 仍保留 validator 负向覆盖。
- RiskGate：
  - `_returns()` 对空列表和单元素列表显式返回 `[]`。
  - 增加边缘测试。
- OpenAI provider：
  - 真实 provider 默认禁用。
  - 需要 `QAL_ENABLE_OPENAI_PROVIDER=1`、`--allow-real-model-call` 和 API key 同时存在才可能进入真实网络路径。
  - CLI help 不展示真实模型调用开关。
- Binance connector：
  - 文档和代码注释明确标记为 best-effort public research data，不是交易或账户集成。
  - public data download 需要 `--allow-network-data` 或代码层 `allow_network=True`。
- Phase 10 research：
  - warmup 仓位不再免费继承进入 score window；首个计分仓位变化会计入 fee/slippage。
  - `recommended_next_research_style` 改为来自 train/validation blind preference，而不是 OOS test ranking。

## 新增验证

- 相同输入写入不同 output dir 时，result/report/audit/manifest 内容保持一致。
- pipeline 产物不出现启用下单权限的标记。
- Phase 10 walk-forward 每个 split/style 的首个计分日期不早于对应窗口开始日。
- bad CSV 路径仍产出审计产物并保持 `insufficient_evidence`。
- 单模型 advisory 的 audit/manifest 记录实际 fake provider 元信息。

## 剩余风险

- OpenAI provider 代码仍保留用于 Phase 8 fail-closed 和人工显式联网验收，但默认禁用。
- Binance public data connector 仍是联网 best-effort，需要人工显式运行。
- NautilusTrader 仍只有 Phase 10 只读 adapter sample，未接真实 BacktestEngine。
