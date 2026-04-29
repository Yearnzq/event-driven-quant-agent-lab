from __future__ import annotations

import argparse
from pathlib import Path

from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig, RiskConfig


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 daily advisory pipeline.")
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--output-dir", default="artifacts/reports")
    parser.add_argument("--data-source", choices=["mock", "csv"], default="mock")
    parser.add_argument("--bars-1h-csv")
    parser.add_argument("--bars-1d-csv")
    parser.add_argument("--portfolio-json")
    parser.add_argument("--max-position-pct", type=float, default=0.10)
    parser.add_argument("--max-loss-budget-pct", type=float, default=0.02)
    args = parser.parse_args(argv)

    csv_config = None
    if args.data_source == "csv":
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
            parser.error(f"csv data source requires: {', '.join(missing)}")
        csv_config = CsvDataConfig(
            bars_1h_csv=Path(args.bars_1h_csv),
            bars_1d_csv=Path(args.bars_1d_csv),
            portfolio_json=Path(args.portfolio_json),
        )
    config = PipelineConfig(
        symbol=args.symbol,
        data_source=args.data_source,
        csv=csv_config,
        output_dir=Path(args.output_dir),
        risk=RiskConfig(
            max_position_pct=args.max_position_pct,
            max_loss_budget_pct=args.max_loss_budget_pct,
        ),
    )
    result = run_daily_pipeline(config=config)
    print(result.report_markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
