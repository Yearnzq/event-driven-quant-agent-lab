# Event-Driven Quant Agent Lab

Research workspace for comparing event-driven trading engines and designing a
human-in-the-loop multi-agent quant advisory system.

## Upstream References

The source snapshots live under `upstreams/`.

| Project | Local path | Primary idea to study |
| --- | --- | --- |
| NautilusTrader | `upstreams/nautilus_trader` | Production-grade deterministic event engine, backtest/live parity, multi-asset abstractions |
| aat | `upstreams/aat` | Async strategy callbacks, trading/risk/execution/backtest engine split |
| QUANTAXIS | `upstreams/QUANTAXIS` | Chinese quant workflow, pub/sub engine, A-share/futures-oriented lifecycle |
| alphahunter | `upstreams/alphahunter` | asyncio event loop, market-making style strategy objects |
| aioquant | `upstreams/aioquant` | Lightweight async market data, order, timer, and task modules |

`upstreams-manifest.json` records the branch/source used for each downloaded
snapshot. Git was not available in the current shell, so these are GitHub
zipball snapshots rather than full git clones.

## Working Thesis

Use one primary event-driven engine as the runtime base, then borrow ideas from
the other systems where they improve the design. Do not merge five frameworks
into one runtime.

The intended product is not an autonomous trading bot. It is a daily advisory
system:

1. Collect market, position, news, macro, and historical context.
2. Convert raw inputs into normalized events and features.
3. Ask specialized model agents for analysis.
4. Aggregate those model outputs into a structured recommendation.
5. Run hard risk checks.
6. Produce a daily report for human approval.

## First Architecture Direction

- **Primary runtime candidate:** NautilusTrader if production-grade execution,
  multi-asset support, and backtest/live consistency matter most.
- **Fast prototype candidate:** aat if the team wants to stay mostly in Python
  while validating strategy and agent workflows.
- **Ideas to borrow:**
  - NautilusTrader: deterministic event model and strict domain objects.
  - aat: risk/execution/backtest separation.
  - QUANTAXIS: localized market workflow and distributed/pub-sub thinking.
  - alphahunter/aioquant: lightweight async I/O and strategy callback style.

See `docs/architecture.md` for the initial system design.

## Planning

- Ten-stage implementation roadmap: `docs/ten-stage-roadmap.zh.md`
- Requirements alignment: `docs/requirements-alignment.zh.md`
- Stage 1 review checklist: `docs/stage-01-review-checklist.zh.md`
- Stage 1 offline gate: `scripts/stage_01_gate.py`
- Stage 2 review checklist: `docs/stage-02-review-checklist.zh.md`
- Stage 2 offline gate: `scripts/stage_02_gate.py`
- Stage 3 review checklist: `docs/stage-03-review-checklist.zh.md`
- Stage 3 offline gate: `scripts/stage_03_gate.py`
- Stage 4 review checklist: `docs/stage-04-review-checklist.zh.md`
- Stage 4 offline gate: `scripts/stage_04_gate.py`
- Stage 5 review checklist: `docs/stage-05-review-checklist.zh.md`
- Stage 5 offline gate: `scripts/stage_05_gate.py`
- Chinese implementation roadmap: `docs/roadmap.zh.md`
- Additional open-source project research: `docs/additional-research.zh.md`
- Optimized implementation path: `docs/implementation-path.zh.md`
- Advisory core engineering constraints: `docs/advisory-core-spec.zh.md`
- Phase 1 implementation status: `docs/phase1-status.zh.md`

## Phase 1 Skeleton

Run tests in the `medifuse` container:

```bash
cd /workspace/event-driven-quant-agent-lab
source /opt/miniconda3/etc/profile.d/conda.sh
conda activate medi
python -m pytest -q
```

Run the deterministic mock advisory pipeline:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli --symbol BTC-USDT --output-dir artifacts/reports
```

Run with CSV data:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --bars-1h-csv path/to/bars_1h.csv \
  --bars-1d-csv path/to/bars_1d.csv \
  --portfolio-json path/to/portfolio.json \
  --output-dir artifacts/reports
```

Expected CSV columns:

```text
symbol,ts,open,high,low,close,volume,source
```

Generate a deterministic sample CSV dataset:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --write-sample-data sample_data/btc_usdt
```

The sample dataset writes a Phase 2 `metadata.json` manifest with file hashes,
schema version, `order_allowed=false`, and `human_required=true`. Validate it:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --validate-dataset sample_data/btc_usdt
```

Generate a deterministic bad CSV dataset for Data Gate failure checks:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --write-bad-sample-data sample_data/bad_btc_usdt
```

The Phase 1.1 risk gate also checks existing position size, cash buffer, and
hourly return volatility. These checks are advisory-only: `order_allowed`
remains `false` in Phase 1.

The Phase 5 risk gate extends deterministic checks with recent drawdown,
downside volatility, single-hour loss, and portfolio risk budget metrics. These
metrics are written into report JSON/Markdown and remain advisory-only:
`order_allowed=false`, `human_required=true`.

Download public Binance OHLCV data without API keys:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --download-binance-data sample_data/binance_btc_usdt \
  --symbol BTC-USDT
```

Then run the CSV pipeline using the generated `metadata.json` `as_of` value:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --data-source csv \
  --symbol BTC-USDT \
  --csv-dir sample_data/binance_btc_usdt \
  --output-dir artifacts/reports
```

Evaluate the deterministic MA crossover signal offline:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --evaluate-signals \
  --csv-dir sample_data/binance_btc_usdt \
  --output-dir artifacts/research
```

Phase 4 evaluates the default signal registry, currently including MA crossover,
breakout, and volatility-regime signals. The research output is advisory-only
and writes:

```text
artifacts/research/signal-registry.json
artifacts/research/signal_research_report.md
artifacts/research/signal_research_report.json
artifacts/research/artifact-catalog.json
artifacts/research/run-manifest.json
```

Clean raw news/web JSONL before any agent sees it:

```bash
PYTHONPATH=src python -m quant_agent_lab.app.cli \
  --clean-news-jsonl raw_news.jsonl \
  --cleaned-news-output artifacts/evidence/cleaned_news.jsonl
```

Input rows should include `published_at`, `title`, and one of `content`,
`body`, `text`, or `summary`. Output rows intentionally omit raw bodies.

Every advisory pipeline run writes a Phase 3 audit ledger beside the report:

```text
artifact-catalog.json
run-manifest.json
```

The catalog records report, result JSON, audit JSON, and audit-log file hashes.
The run manifest records input, output, config, and catalog hashes while keeping
`order_allowed=false` and `human_required=true`.
