from __future__ import annotations

import json

from quant_agent_lab.app.cli import main
from quant_agent_lab.data.importers import write_sample_csv_dataset
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.research.evaluation import evaluate_ma_crossover, render_signal_evaluation_markdown


def test_evaluate_ma_crossover_returns_summary() -> None:
    snapshot = load_mock_market_snapshot(bars_1d_count=60)

    summary = evaluate_ma_crossover(snapshot.bars_1d, fast_window=7, slow_window=30, horizon=1)

    assert summary.symbol == "BTC-USDT"
    assert summary.strategy_name == "ma_crossover_7_30_h1"
    assert summary.sample_count == 30
    assert summary.directional_count > 0
    assert 0 <= summary.hit_rate <= 1
    assert summary.points[-1].action.value in {"buy", "sell", "hold"}


def test_render_signal_evaluation_markdown() -> None:
    snapshot = load_mock_market_snapshot(bars_1d_count=60)
    summary = evaluate_ma_crossover(snapshot.bars_1d)

    report = render_signal_evaluation_markdown(summary)

    assert "Signal Evaluation" in report
    assert "offline signal research only" in report
    assert summary.strategy_name in report


def test_cli_evaluate_signals_writes_outputs(tmp_path) -> None:
    csv_dir = write_sample_csv_dataset(tmp_path / "sample", symbol="BTC-USDT")
    output_dir = tmp_path / "research"

    exit_code = main(
        [
            "--evaluate-signals",
            "--csv-dir",
            str(csv_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    payload = json.loads((output_dir / "ma_crossover_7_30_h1.json").read_text(encoding="utf-8"))
    assert payload["sample_count"] > 0
    assert (output_dir / "ma_crossover_7_30_h1.md").exists()


def test_cli_evaluate_signals_accepts_bars_1d_csv_without_csv_dir(tmp_path) -> None:
    csv_dir = write_sample_csv_dataset(tmp_path / "sample", symbol="BTC-USDT")
    output_dir = tmp_path / "research"

    exit_code = main(
        [
            "--evaluate-signals",
            "--bars-1d-csv",
            str(csv_dir / "bars_1d.csv"),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert (output_dir / "ma_crossover_7_30_h1.json").exists()
