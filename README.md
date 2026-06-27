# Event-Driven Quant Agent Lab

Minimal Python runtime for an event-driven quant advisory pipeline.

This project is not an automated trading bot. It produces advisory reports only.
All generated recommendations keep `order_allowed=false` and require human
review before any real-world action.

## What It Runs

The default pipeline is:

```text
MarketSnapshot
  -> Data Validation Gate
  -> deterministic signals
  -> advisory agent opinions
  -> RecommendationDraft
  -> RiskGate
  -> Markdown report and JSON audit artifacts
```

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Run With Mock Data

```bash
quant-agent-lab --symbol BTC-USDT --output-dir artifacts/reports
```

or:

```bash
python -m quant_agent_lab.app.cli \
  --symbol BTC-USDT \
  --output-dir artifacts/reports
```

The output directory includes a Markdown report, JSON result, audit record,
audit log, artifact catalog, and run manifest.

## Run With CSV Data

Expected files:

```text
bars_1h.csv
bars_1d.csv
portfolio.json
```

CSV columns:

```text
symbol,ts,open,high,low,close,volume,source,evidence_id
```

Example:

```bash
python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --csv-dir path/to/dataset \
  --output-dir artifacts/reports
```

You can also pass files explicitly:

```bash
python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --bars-1h-csv path/to/bars_1h.csv \
  --bars-1d-csv path/to/bars_1d.csv \
  --portfolio-json path/to/portfolio.json \
  --output-dir artifacts/reports
```

## Generate Sample Data

```bash
python -m quant_agent_lab.app.cli \
  --write-sample-data sample_data/btc_usdt
```

Validate a dataset manifest:

```bash
python -m quant_agent_lab.app.cli \
  --validate-dataset sample_data/btc_usdt
```

## Optional Model Provider

The default provider is deterministic and offline. Real model calls are disabled
unless explicitly enabled by environment flag and CLI option.

OpenAI Responses API example:

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

## Safety Boundaries

- No automatic trading.
- No broker or exchange account access.
- No paper-trading engine.
- No order generation.
- `RiskGate` cannot be bypassed by model output.
- `order_allowed` remains `false`.
- Human review remains required.
