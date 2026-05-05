from __future__ import annotations

import json

from quant_agent_lab.app.cli import main
from quant_agent_lab.data.audit import validate_run_manifest
from quant_agent_lab.data.importers import write_sample_csv_dataset
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.research.evaluation import (
    build_signal_research_report,
    default_signal_registry,
    evaluate_ma_crossover,
    render_signal_evaluation_markdown,
    serialize_signal_registry,
)


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


def test_default_registry_evaluates_multiple_signal_families() -> None:
    snapshot = load_mock_market_snapshot(bars_1d_count=60)

    report = build_signal_research_report(snapshot.bars_1d, registry=default_signal_registry())

    assert report.schema_version == "phase4.signal_research.v1"
    assert report.strategy_count == 3
    assert report.order_allowed is False
    assert report.human_required is True
    assert report.deployable is False
    assert {summary.signal_family for summary in report.summaries} == {
        "trend",
        "breakout",
        "volatility",
    }
    assert len(report.ranking) == 3
    for row in report.ranking:
        assert 0 <= row.research_score <= 1
        assert row.score_components.keys() == {
            "cumulative_return_rank",
            "average_return_rank",
            "hit_rate_rank",
            "drawdown_inverse_rank",
            "directional_coverage_rank",
        }
    serialized = serialize_signal_registry(default_signal_registry(volatility_threshold=0.02))
    volatility = next(item for item in serialized if item["family"] == "volatility")
    assert volatility["parameters"]["volatility_threshold"] == 0.02


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
    report = json.loads((output_dir / "signal_research_report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "phase4.signal_research.v1"
    assert report["strategy_count"] == 3
    assert report["order_allowed"] is False
    assert report["ranking"][0]["score_components"]["drawdown_inverse_rank"] >= 0
    assert (output_dir / "signal-registry.json").exists()
    validation = validate_run_manifest(
        output_dir,
        required_roles={"research_markdown", "research_json", "registry_json"},
    )
    assert validation.status == "pass"


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
