from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig
from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.app.cli import main
from quant_agent_lab.data.audit import validate_run_manifest


def _write_bars(path, *, symbol: str, timeframe: str, count: int, as_of: datetime) -> None:
    delta = timedelta(hours=1) if timeframe == "1h" else timedelta(days=1)
    base = 64000 if timeframe == "1h" else 61000
    with path.open("w", encoding="utf-8") as handle:
        handle.write("symbol,ts,open,high,low,close,volume,source\n")
        for index in range(count):
            ts = as_of - delta * (count - index)
            price = base + index * 10
            handle.write(
                f"{symbol},{ts.isoformat()},{price},{price + 20},{price - 15},{price + 5},1000,csv\n"
            )


def test_pipeline_loads_csv_data(tmp_path) -> None:
    as_of = datetime(2026, 4, 29, tzinfo=timezone.utc)
    bars_1h = tmp_path / "bars_1h.csv"
    bars_1d = tmp_path / "bars_1d.csv"
    portfolio = tmp_path / "portfolio.json"
    _write_bars(bars_1h, symbol="BTC-USDT", timeframe="1h", count=72, as_of=as_of)
    _write_bars(bars_1d, symbol="BTC-USDT", timeframe="1d", count=45, as_of=as_of)
    portfolio.write_text(
        json.dumps(
            {
                "as_of": as_of.isoformat(),
                "equity": 100000,
                "cash": 90000,
                "positions": {"BTC-USDT": 0.1},
            }
        ),
        encoding="utf-8",
    )

    result = run_daily_pipeline(
        config=PipelineConfig(
            symbol="BTC-USDT",
            as_of=as_of,
            data_source="csv",
            csv=CsvDataConfig(
                bars_1h_csv=bars_1h,
                bars_1d_csv=bars_1d,
                portfolio_json=portfolio,
            ),
            output_dir=tmp_path / "out",
        )
    )

    assert result.data_validation.status.value == "pass"
    assert (tmp_path / "out" / f"{result.run_id}.audit.json").exists()
    assert (tmp_path / "out" / "audit-log.jsonl").exists()


def test_cli_loads_csv_dir_metadata(tmp_path) -> None:
    as_of = datetime(2026, 4, 29, tzinfo=timezone.utc)
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    _write_bars(csv_dir / "bars_1h.csv", symbol="BTC-USDT", timeframe="1h", count=72, as_of=as_of)
    _write_bars(csv_dir / "bars_1d.csv", symbol="BTC-USDT", timeframe="1d", count=45, as_of=as_of)
    (csv_dir / "portfolio.json").write_text(
        json.dumps(
            {
                "as_of": as_of.isoformat(),
                "equity": 100000,
                "cash": 90000,
                "positions": {"BTC-USDT": 0.1},
            }
        ),
        encoding="utf-8",
    )
    (csv_dir / "metadata.json").write_text(
        json.dumps(
            {
                "as_of": as_of.isoformat(),
                "bars_1h_csv": "bars_1h.csv",
                "bars_1d_csv": "bars_1d.csv",
                "portfolio_json": "portfolio.json",
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--data-source",
            "csv",
            "--csv-dir",
            str(csv_dir),
            "--output-dir",
            str(tmp_path / "reports"),
        ]
    )

    assert exit_code == 0


def test_pipeline_bad_csv_fails_closed_with_audit_artifacts(tmp_path) -> None:
    as_of = datetime(2026, 4, 29, tzinfo=timezone.utc)
    output_dir = tmp_path / "bad-csv-report"

    result = run_daily_pipeline(
        config=PipelineConfig(
            symbol="BTC-USDT",
            as_of=as_of,
            data_source="csv",
            csv=CsvDataConfig(
                bars_1h_csv=tmp_path / "missing_1h.csv",
                bars_1d_csv=tmp_path / "missing_1d.csv",
                portfolio_json=tmp_path / "missing_portfolio.json",
            ),
            output_dir=output_dir,
        )
    )

    assert result.data_validation.status.value == "fail"
    assert result.recommendation.action.value == "insufficient_evidence"
    assert result.risk_decision.order_allowed is False
    assert "market data loading failed" in result.data_validation.reasons[0]
    assert (output_dir / f"{result.run_id}.md").exists()
    assert (output_dir / f"{result.run_id}.audit.json").exists()
    assert validate_run_manifest(output_dir).status == "pass"
