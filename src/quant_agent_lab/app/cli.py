from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig, RiskConfig
from quant_agent_lab.data.connectors import write_binance_csv_dataset
from quant_agent_lab.data.csv_loader import load_bars_csv
from quant_agent_lab.data.importers import write_bad_csv_dataset, write_sample_csv_dataset
from quant_agent_lab.data.metadata import validate_dataset_manifest
from quant_agent_lab.data.text_cleaning import clean_news_jsonl
from quant_agent_lab.research.evaluation import evaluate_ma_crossover, render_signal_evaluation_markdown


def _parse_as_of(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _load_csv_dir(csv_dir: Path) -> tuple[CsvDataConfig, datetime | None]:
    metadata_path = csv_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    config = CsvDataConfig(
        bars_1h_csv=csv_dir / str(metadata.get("bars_1h_csv", "bars_1h.csv")),
        bars_1d_csv=csv_dir / str(metadata.get("bars_1d_csv", "bars_1d.csv")),
        portfolio_json=csv_dir / str(metadata.get("portfolio_json", "portfolio.json")),
    )
    as_of = _parse_as_of(str(metadata["as_of"])) if metadata.get("as_of") else None
    return config, as_of


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 daily advisory pipeline.")
    parser.add_argument("--write-sample-data", help="Write a deterministic CSV sample dataset and exit.")
    parser.add_argument("--write-bad-sample-data", help="Write deterministic bad CSV samples for Data Gate tests and exit.")
    parser.add_argument("--validate-dataset", help="Validate a CSV dataset metadata manifest and exit.")
    parser.add_argument("--download-binance-data", help="Download public Binance OHLCV CSV data and exit.")
    parser.add_argument("--evaluate-signals", action="store_true", help="Evaluate deterministic signals on CSV daily bars and exit.")
    parser.add_argument("--clean-news-jsonl", help="Clean raw news/web JSONL into schema-safe text evidence and exit.")
    parser.add_argument("--cleaned-news-output", help="Output path for --clean-news-jsonl.")
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--as-of", help="UTC as-of timestamp for CSV runs, e.g. 2026-04-29T00:00:00Z.")
    parser.add_argument("--output-dir", default="artifacts/reports")
    parser.add_argument("--data-source", choices=["mock", "csv"], default="mock")
    parser.add_argument("--csv-dir", help="Directory containing bars_1h.csv, bars_1d.csv, portfolio.json, and optional metadata.json.")
    parser.add_argument("--bars-1h-csv")
    parser.add_argument("--bars-1d-csv")
    parser.add_argument("--portfolio-json")
    parser.add_argument("--hourly-limit", type=int, default=72)
    parser.add_argument("--daily-limit", type=int, default=45)
    parser.add_argument("--fast-window", type=int, default=7)
    parser.add_argument("--slow-window", type=int, default=30)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--portfolio-equity", type=float, default=100000.0)
    parser.add_argument("--portfolio-cash", type=float, default=100000.0)
    parser.add_argument("--position-pct", type=float, default=0.0)
    parser.add_argument("--max-position-pct", type=float, default=0.10)
    parser.add_argument("--max-loss-budget-pct", type=float, default=0.02)
    parser.add_argument("--max-existing-position-pct", type=float, default=0.25)
    parser.add_argument("--min-cash-pct", type=float, default=0.05)
    parser.add_argument("--max-hourly-return-vol", type=float, default=0.03)
    args = parser.parse_args(argv)

    if args.write_sample_data:
        output_dir = write_sample_csv_dataset(Path(args.write_sample_data), symbol=args.symbol)
        print(f"Wrote sample dataset to {output_dir}")
        return 0

    if args.write_bad_sample_data:
        output_dir = write_bad_csv_dataset(Path(args.write_bad_sample_data), symbol=args.symbol)
        print(f"Wrote bad sample dataset to {output_dir}")
        return 0

    if args.validate_dataset:
        result = validate_dataset_manifest(Path(args.validate_dataset))
        print(result.model_dump_json(indent=2))
        return 0 if result.status == "pass" else 1

    if args.download_binance_data:
        output_dir = write_binance_csv_dataset(
            Path(args.download_binance_data),
            symbol=args.symbol,
            hourly_limit=args.hourly_limit,
            daily_limit=args.daily_limit,
            equity=args.portfolio_equity,
            cash=args.portfolio_cash,
            position_pct=args.position_pct,
        )
        metadata = output_dir / "metadata.json"
        print(f"Wrote Binance public market dataset to {output_dir}")
        print(f"Metadata: {metadata}")
        return 0

    if args.clean_news_jsonl:
        if not args.cleaned_news_output:
            parser.error("--clean-news-jsonl requires --cleaned-news-output")
        output_path = clean_news_jsonl(Path(args.clean_news_jsonl), Path(args.cleaned_news_output))
        print(f"Wrote cleaned text evidence to {output_path}")
        return 0

    csv_config = None
    metadata_as_of = None
    if args.csv_dir:
        csv_config, metadata_as_of = _load_csv_dir(Path(args.csv_dir))
    if args.data_source == "csv":
        if csv_config is None:
            missing = [
                name
                for name, value in {
                    "--bars-1h-csv": args.bars_1h_csv,
                    "--bars-1d-csv": args.bars_1d_csv,
                    "--portfolio-json": args.portfolio_json,
                }.items()
                if not value
            ]
            if missing:
                parser.error(f"csv data source requires --csv-dir or: {', '.join(missing)}")
            csv_config = CsvDataConfig(
                bars_1h_csv=Path(args.bars_1h_csv),
                bars_1d_csv=Path(args.bars_1d_csv),
                portfolio_json=Path(args.portfolio_json),
            )

    if args.evaluate_signals:
        bars_1d_csv = csv_config.bars_1d_csv if csv_config is not None else None
        if bars_1d_csv is None and args.bars_1d_csv:
            bars_1d_csv = Path(args.bars_1d_csv)
        if bars_1d_csv is None:
            parser.error("--evaluate-signals requires --csv-dir or --bars-1d-csv")
        bars_1d = load_bars_csv(bars_1d_csv, symbol=args.symbol, timeframe="1d")
        try:
            summary = evaluate_ma_crossover(
                bars_1d,
                fast_window=args.fast_window,
                slow_window=args.slow_window,
                horizon=args.horizon,
            )
        except ValueError as exc:
            parser.error(str(exc))
        report = render_signal_evaluation_markdown(summary)
        output_dir = Path(args.output_dir)
        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / f"{summary.strategy_name}.md").write_text(report, encoding="utf-8")
            (output_dir / f"{summary.strategy_name}.json").write_text(
                json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(report)
        return 0

    config = PipelineConfig(
        symbol=args.symbol,
        as_of=_parse_as_of(args.as_of) if args.as_of else metadata_as_of or PipelineConfig().as_of,
        data_source=args.data_source,
        csv=csv_config,
        output_dir=Path(args.output_dir),
        risk=RiskConfig(
            max_position_pct=args.max_position_pct,
            max_loss_budget_pct=args.max_loss_budget_pct,
            max_existing_position_pct=args.max_existing_position_pct,
            min_cash_pct=args.min_cash_pct,
            max_hourly_return_vol=args.max_hourly_return_vol,
        ),
    )
    result = run_daily_pipeline(config=config)
    print(result.report_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
