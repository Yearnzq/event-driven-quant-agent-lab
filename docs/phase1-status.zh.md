# Phase 1 实现状态

日期：2026-04-29

## 已完成

当前 Phase 1 已经具备一个纯 Python advisory core：

```text
MarketSnapshot
  -> Data Validation Gate
  -> deterministic signals
  -> mock TypedAgents
  -> RecommendationDraft
  -> RiskGate
  -> Markdown report
  -> JSON audit records
```

实现模块：

| 模块 | 路径 | 状态 |
| --- | --- | --- |
| Pydantic schema | `src/quant_agent_lab/core/schemas.py` | 已完成 v1 |
| Pipeline config | `src/quant_agent_lab/core/config.py` | 已完成 v1 |
| Mock data source | `src/quant_agent_lab/data/mock.py` | 已完成 |
| CSV data source | `src/quant_agent_lab/data/csv_loader.py` | 已完成 |
| Data Validation Gate | `src/quant_agent_lab/data/validation.py` | 已完成 v1 |
| Audit hash / JSON / JSONL | `src/quant_agent_lab/data/audit.py` | 已完成 |
| Deterministic signals | `src/quant_agent_lab/strategy/signals.py` | 已完成 v1 |
| Mock agents | `src/quant_agent_lab/agents/mock.py` | 已完成 |
| Committee | `src/quant_agent_lab/decision/committee.py` | 已完成 v1 |
| Risk Gate | `src/quant_agent_lab/risk/gate.py` | 已完成 v1 |
| Daily report | `src/quant_agent_lab/reports/daily.py` | 已完成 v1 |
| CLI | `src/quant_agent_lab/app/cli.py` | 已完成 |

## 当前验证

在 `medifuse` 容器的 `medi` conda 环境中验证：

```text
11 passed
```

运行命令：

```bash
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate medi
python -m pytest -q
```

CLI：

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli --symbol BTC-USDT --output-dir artifacts/reports
```

产物：

```text
artifacts/reports/run-btc-usdt-20260429t000000z.md
artifacts/reports/run-btc-usdt-20260429t000000z.json
artifacts/reports/run-btc-usdt-20260429t000000z.audit.json
artifacts/reports/audit-log.jsonl
```

## 已实现的硬约束

- Phase 1 不允许 `order_allowed=true`。
- `human_required` 必须为 `true`。
- `hold/review_required/no_trade/insufficient_evidence` 的目标仓位必须为 0。
- Data Gate 失败会进入 `insufficient_evidence`。
- Risk Gate 默认不允许订单。
- 风险限制可通过 `PipelineConfig.risk` 或 CLI 参数配置。
- 输出包含 `evidence_ids`。
- 审计记录包含 `input_hash` 和 `output_hash`。

## 当前依赖现实

容器 `medi` 环境是 Python 3.10.19，不是 Python 3.12。因此当前 Phase 1 代码保持 Python 3.10+ 兼容。

当前容器已具备：

- `pydantic`
- `pytest`
- `pandas`
- `numpy`

当前容器缺少：

- `duckdb`
- `pyarrow`

所以本阶段先实现 CSV/JSON/JSONL 存储链路。DuckDB + Parquet 将作为后续 storage adapter 接入。

## 下一步建议

下一步进入 Phase 1.1：

1. 增加真实 OHLCV 数据导入脚本，优先支持 OKX/Binance 导出的 CSV。
2. 增加 sample data 目录和 CSV schema 文档。
3. 增加 `NewsEvent` / `CleanedTextEvidence` schema，但不接网页原文。
4. 增加更严格的 risk rules：最大回撤、波动率目标、已有仓位约束。
5. 增加 report template，把“为什么 review_required”写得更清晰。
