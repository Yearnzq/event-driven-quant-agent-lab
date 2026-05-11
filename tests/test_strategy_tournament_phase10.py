from __future__ import annotations

import json

import pytest

from quant_agent_lab.app.cli import main
from quant_agent_lab.research.tournament import (
    CostModel,
    StrategyStyleSpec,
    default_strategy_style_registry,
    generate_phase10_daily_bars,
    run_style_backtest,
    run_strategy_style_tournament,
)


def test_phase10_tournament_writes_required_artifacts(tmp_path) -> None:
    research_dir = tmp_path / "research"
    audit_dir = tmp_path / "audit"
    adapter_dir = tmp_path / "adapters" / "nautilus"

    report = run_strategy_style_tournament(
        research_output_dir=research_dir,
        audit_output_dir=audit_dir,
        adapter_output_dir=adapter_dir,
    )

    assert report.phase == 10
    assert report.deployable is False
    assert report.order_allowed is False
    assert report.human_required is True
    assert len(report.styles_tested) >= 5
    assert report.ai_blind_preference_check.data_visible_to_ai == "train_validation_only"
    assert report.recommended_next_research_style == report.ai_blind_preference_check.ai_preferred_style_before_test
    assert (research_dir / "strategy_style_tournament.md").exists()
    assert (research_dir / "strategy_style_tournament.json").exists()
    assert (research_dir / "walk_forward_results.json").exists()
    assert (research_dir / "stress_test_results.json").exists()
    assert (research_dir / "cost_sensitivity_results.json").exists()
    assert (audit_dir / "simulation_manifest.json").exists()
    assert (adapter_dir / "adapter_input_sample.json").exists()

    manifest = json.loads((audit_dir / "simulation_manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "phase10.simulation_manifest.v1"
    assert manifest["order_allowed"] is False
    assert manifest["deployable"] is False
    adapter = json.loads((adapter_dir / "adapter_input_sample.json").read_text(encoding="utf-8"))
    assert adapter["adapter_scope"] == "read_only_backtest_input_spike"
    assert adapter["order_allowed"] is False


def test_phase10_walk_forward_uses_fixed_locked_splits(tmp_path) -> None:
    run_strategy_style_tournament(
        research_output_dir=tmp_path / "research",
        audit_output_dir=tmp_path / "audit",
        adapter_output_dir=tmp_path / "adapters" / "nautilus",
    )
    rows = json.loads((tmp_path / "research" / "walk_forward_results.json").read_text(encoding="utf-8"))
    split_names = {row["split_name"] for row in rows}
    style_names = {row["style_name"] for row in rows}

    assert split_names == {"window_1", "window_2", "window_3", "window_4"}
    assert {
        "trend_following",
        "breakout",
        "mean_reversion",
        "volatility_regime",
        "defensive_vol_target",
    }.issubset(style_names)
    assert all("test" in row and "train" in row and "validation" in row for row in rows)


def test_phase10_walk_forward_scoring_excludes_warmup_returns(tmp_path) -> None:
    run_strategy_style_tournament(
        research_output_dir=tmp_path / "research",
        audit_output_dir=tmp_path / "audit",
        adapter_output_dir=tmp_path / "adapters" / "nautilus",
    )
    rows = json.loads((tmp_path / "research" / "walk_forward_results.json").read_text(encoding="utf-8"))
    split_boundaries = {
        "window_1": {
            "train": "2020-01-01",
            "validation": "2022-01-01",
            "test": "2022-07-01",
        },
        "window_2": {
            "train": "2021-01-01",
            "validation": "2023-01-01",
            "test": "2023-07-01",
        },
        "window_3": {
            "train": "2022-01-01",
            "validation": "2024-01-01",
            "test": "2024-07-01",
        },
        "window_4": {
            "train": "2023-01-01",
            "validation": "2025-01-01",
            "test": "2025-07-01",
        },
    }

    for row in rows:
        boundaries = split_boundaries[row["split_name"]]
        for segment in ("train", "validation", "test"):
            metrics = row[segment]
            assert metrics["scored_return_count"] > 0
            assert metrics["first_scored_at"] >= boundaries[segment]


def test_phase10_warmup_position_entry_cost_is_not_free() -> None:
    bars = generate_phase10_daily_bars()
    style = next(item for item in default_strategy_style_registry() if item.spec.style_name == "trend_following")
    metrics = run_style_backtest(
        bars[:220],
        style,
        cost_model=CostModel(name="medium_cost", fee_bps=10, slippage_bps=5),
        score_start="2020-06-01",
        score_end="2020-07-01",
    )

    assert metrics.first_scored_at == "2020-06-01"
    assert metrics.fee_paid > 0
    assert metrics.slippage_cost > 0


def test_phase10_strategy_style_cannot_be_deployable() -> None:
    with pytest.raises(ValueError, match="cannot be deployable"):
        StrategyStyleSpec(
            style_name="trend_following",
            family="trend",
            parameters={},
            deployable=True,
        )


def test_phase10_dataset_is_deterministic() -> None:
    first = generate_phase10_daily_bars()
    second = generate_phase10_daily_bars()

    assert len(first) == len(second)
    assert first[0].ts.isoformat() == "2020-01-01T00:00:00+00:00"
    assert first[-1].ts.isoformat() == "2025-12-31T00:00:00+00:00"
    assert [bar.close for bar in first[:20]] == [bar.close for bar in second[:20]]


def test_cli_phase10_strategy_tournament(tmp_path) -> None:
    research_dir = tmp_path / "research"
    audit_dir = tmp_path / "audit"
    adapter_dir = tmp_path / "adapter"

    status = main(
        [
            "--run-strategy-tournament",
            "--output-dir",
            str(research_dir),
            "--audit-output-dir",
            str(audit_dir),
            "--adapter-output-dir",
            str(adapter_dir),
        ]
    )

    assert status == 0
    assert (research_dir / "strategy_style_tournament.json").exists()
    assert (audit_dir / "simulation_manifest.json").exists()
    assert (adapter_dir / "adapter_input_sample.json").exists()
