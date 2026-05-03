from __future__ import annotations

from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig
from quant_agent_lab.data.importers import normalize_ohlcv_csv, write_sample_csv_dataset


def test_normalize_ohlcv_csv_accepts_common_aliases(tmp_path) -> None:
    raw = tmp_path / "raw.csv"
    normalized = tmp_path / "normalized.csv"
    raw.write_text(
        "\n".join(
            [
                "timestamp,o,h,l,c,vol",
                "2026-04-28T23:00:00+00:00,64000,64100,63900,64050,123",
            ]
        ),
        encoding="utf-8",
    )

    normalize_ohlcv_csv(raw, normalized, symbol="BTC-USDT", source="exchange-export")

    lines = normalized.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "symbol,ts,open,high,low,close,volume,source"
    assert lines[1] == (
        "BTC-USDT,2026-04-28T23:00:00+00:00,64000,64100,63900,64050,123,"
        "exchange-export"
    )


def test_normalize_ohlcv_csv_accepts_epoch_milliseconds(tmp_path) -> None:
    raw = tmp_path / "raw.csv"
    normalized = tmp_path / "normalized.csv"
    raw.write_text(
        "\n".join(
            [
                "open_time,open,high,low,close,volume",
                "1777417200000,64000,64100,63900,64050,123",
            ]
        ),
        encoding="utf-8",
    )

    normalize_ohlcv_csv(raw, normalized, symbol="BTC-USDT", source="binance-export")

    lines = normalized.read_text(encoding="utf-8").splitlines()
    assert lines[1].startswith("BTC-USDT,2026-04-28T23:00:00+00:00")


def test_write_sample_csv_dataset_runs_through_pipeline(tmp_path) -> None:
    sample_dir = write_sample_csv_dataset(tmp_path / "sample", symbol="BTC-USDT")

    result = run_daily_pipeline(
        config=PipelineConfig(
            data_source="csv",
            csv=CsvDataConfig(
                bars_1h_csv=sample_dir / "bars_1h.csv",
                bars_1d_csv=sample_dir / "bars_1d.csv",
                portfolio_json=sample_dir / "portfolio.json",
            ),
            output_dir=tmp_path / "reports",
        )
    )

    assert result.data_validation.status.value == "pass"
    assert (sample_dir / "bars_1h.csv").exists()
    assert (sample_dir / "bars_1d.csv").exists()
    assert (sample_dir / "portfolio.json").exists()
