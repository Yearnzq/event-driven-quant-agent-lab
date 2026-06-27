# Event-Driven Quant Agent Lab

[中文](#中文说明) | [English](#english)

## English

Event-Driven Quant Agent Lab is a lightweight Python research project for
turning market snapshots into structured strategy opinions, risk checks, and
auditable reports.

It is designed for experimentation with event-driven quant workflows:

- normalize market and portfolio snapshots
- validate OHLCV data before analysis
- build deterministic signal summaries
- combine rule-based or model-backed agent opinions
- evaluate decisions through a risk gate
- export Markdown reports and JSON audit records

The project is intentionally small: no database, no web service, no broker
adapter, and no exchange account integration. It is suitable for local research,
offline experiments, and reproducible strategy-assistant prototypes.

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### Quick Start

Run the built-in mock data pipeline:

```bash
quant-agent-lab --symbol BTC-USDT --output-dir artifacts/reports
```

or:

```bash
python -m quant_agent_lab.app.cli \
  --symbol BTC-USDT \
  --output-dir artifacts/reports
```

The output directory contains a Markdown report, result JSON, audit JSON,
append-only audit log, artifact catalog, and run manifest.

### CSV Data

Expected dataset files:

```text
bars_1h.csv
bars_1d.csv
portfolio.json
```

Expected bar columns:

```text
symbol,ts,open,high,low,close,volume,source,evidence_id
```

Run with a dataset directory:

```bash
python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --csv-dir path/to/dataset \
  --output-dir artifacts/reports
```

Generate a sample dataset:

```bash
python -m quant_agent_lab.app.cli \
  --write-sample-data sample_data/btc_usdt
```

Validate a dataset manifest:

```bash
python -m quant_agent_lab.app.cli \
  --validate-dataset sample_data/btc_usdt
```

### Optional Model Providers

The default path is deterministic and offline. Model-backed runs are opt-in and
can be pointed at OpenAI-compatible endpoints.

OpenAI example:

```bash
QAL_ENABLE_OPENAI_PROVIDER=1 OPENAI_API_KEY=... python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --model-provider openai \
  --model-name gpt-5.4-mini \
  --allow-real-model-call \
  --output-dir artifacts/openai-advisory
```

Codex-compatible endpoint example:

```bash
QAL_ENABLE_CODEX_PROVIDER=1 CODEX_API_KEY=... python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --model-provider codex \
  --model-name gpt-5.5 \
  --allow-real-model-call \
  --model-api-key-env CODEX_API_KEY \
  --model-api-base-url https://your-endpoint.example/v1/chat/completions \
  --model-timeout-seconds 180 \
  --output-dir artifacts/codex-advisory
```

### Notes

This repository is for research and decision-support experiments. It does not
place trades, manage accounts, or provide financial advice. Always review the
data, assumptions, and generated reports before using them in any investment
workflow.

### License

This project is released under the [MIT License](LICENSE).

## 中文说明

Event-Driven Quant Agent Lab 是一个轻量级 Python 量化研究项目，用来把市场
快照转换为结构化观点、风险检查结果和可审计报告。

它适合用于事件驱动量化流程的本地实验：

- 规范化市场数据和组合快照
- 在分析前检查 OHLCV 数据质量
- 生成确定性信号摘要
- 聚合规则代理或模型代理给出的策略观点
- 通过风险门控评估建议
- 输出 Markdown 报告和 JSON 审计记录

项目刻意保持简单：不依赖数据库，不启动 Web 服务，不接券商接口，也不连接
交易所账户。它更适合做本地研究、离线回测辅助、策略助手原型和可复现的模型
输出评估。

### 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

### 快速开始

使用内置 mock 数据运行一次完整流程：

```bash
quant-agent-lab --symbol BTC-USDT --output-dir artifacts/reports
```

也可以直接用模块方式运行：

```bash
python -m quant_agent_lab.app.cli \
  --symbol BTC-USDT \
  --output-dir artifacts/reports
```

输出目录会包含 Markdown 报告、结果 JSON、审计 JSON、审计日志、产物目录和
运行 manifest。

### CSV 数据

数据目录应包含：

```text
bars_1h.csv
bars_1d.csv
portfolio.json
```

K 线 CSV 字段：

```text
symbol,ts,open,high,low,close,volume,source,evidence_id
```

使用 CSV 数据运行：

```bash
python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --csv-dir path/to/dataset \
  --output-dir artifacts/reports
```

生成示例数据：

```bash
python -m quant_agent_lab.app.cli \
  --write-sample-data sample_data/btc_usdt
```

校验数据 manifest：

```bash
python -m quant_agent_lab.app.cli \
  --validate-dataset sample_data/btc_usdt
```

### 可选模型后端

默认流程是确定性的离线流程。模型调用需要显式开启，可以接 OpenAI 或兼容
OpenAI 格式的 API 端点。

OpenAI 示例：

```bash
QAL_ENABLE_OPENAI_PROVIDER=1 OPENAI_API_KEY=... python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --model-provider openai \
  --model-name gpt-5.4-mini \
  --allow-real-model-call \
  --output-dir artifacts/openai-advisory
```

Codex 兼容端点示例：

```bash
QAL_ENABLE_CODEX_PROVIDER=1 CODEX_API_KEY=... python -m quant_agent_lab.app.cli \
  --run-single-model-advisory \
  --model-provider codex \
  --model-name gpt-5.5 \
  --allow-real-model-call \
  --model-api-key-env CODEX_API_KEY \
  --model-api-base-url https://your-endpoint.example/v1/chat/completions \
  --model-timeout-seconds 180 \
  --output-dir artifacts/codex-advisory
```

### 说明

本项目用于研究和决策辅助实验，不执行交易、不管理账户，也不构成投资建议。
在任何真实投资流程中使用前，都应自行检查数据来源、参数假设和生成报告。

### 许可

本项目使用 [MIT License](LICENSE) 开源。
