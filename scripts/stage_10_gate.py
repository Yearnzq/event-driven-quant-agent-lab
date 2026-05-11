from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quant_agent_lab.app.cli import main as cli_main  # noqa: E402
from quant_agent_lab.research.tournament import run_strategy_style_tournament  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-10-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _load(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_walk_forward_scoring_windows(walk_forward: list[dict]) -> None:
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
    for row in walk_forward:
        boundaries = split_boundaries[row["split_name"]]
        for segment in ("train", "validation", "test"):
            metrics = row[segment]
            _assert(metrics["scored_return_count"] > 0, f"{row['split_name']} {row['style_name']} {segment} has no scored returns")
            _assert(
                metrics["first_scored_at"] >= boundaries[segment],
                f"{row['split_name']} {row['style_name']} {segment} scored before split start",
            )


def run_stage_10_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    research_dir = output_dir / "research"
    audit_dir = output_dir / "audit"
    adapter_dir = output_dir / "adapters" / "nautilus"
    report = run_strategy_style_tournament(
        research_output_dir=research_dir,
        audit_output_dir=audit_dir,
        adapter_output_dir=adapter_dir,
    )

    required = [
        research_dir / "strategy_style_tournament.md",
        research_dir / "strategy_style_tournament.json",
        research_dir / "walk_forward_results.json",
        research_dir / "stress_test_results.json",
        research_dir / "cost_sensitivity_results.json",
        audit_dir / "simulation_manifest.json",
        adapter_dir / "adapter_input_sample.json",
    ]
    for path in required:
        _assert(path.exists(), f"required Phase 10 artifact missing: {path}")

    payload = _load(research_dir / "strategy_style_tournament.json")
    manifest = _load(audit_dir / "simulation_manifest.json")
    adapter = _load(adapter_dir / "adapter_input_sample.json")
    walk_forward = _load(research_dir / "walk_forward_results.json")
    stress = _load(research_dir / "stress_test_results.json")
    cost = _load(research_dir / "cost_sensitivity_results.json")

    _assert(payload["phase"] == 10, "tournament phase mismatch")
    _assert(payload["simulation_type"] == "offline_walk_forward_strategy_style_tournament", "simulation type mismatch")
    _assert(payload["human_intervention_during_run"] is False, "human intervention flag must be false")
    _assert(payload["deployable"] is False, "tournament cannot be deployable")
    _assert(payload["order_allowed"] is False, "tournament cannot allow orders")
    _assert(payload["human_required"] is True, "tournament must require human review")
    _assert(len(payload["styles_tested"]) >= 5, "not enough strategy styles tested")
    _assert({row["split_name"] for row in walk_forward} == {"window_1", "window_2", "window_3", "window_4"}, "fixed split mismatch")
    _assert(all("train" in row and "validation" in row and "test" in row for row in walk_forward), "train/validation/test separation missing")
    _assert_walk_forward_scoring_windows(walk_forward)
    _assert(len(cost) >= len(payload["styles_tested"]) * 3, "cost sensitivity did not cover three cost models")
    _assert({row["cost_model"]["name"] for row in cost} == {"low_cost", "medium_cost", "high_cost"}, "cost models mismatch")
    _assert(len({row["scenario"] for row in stress}) >= 8, "stress scenario coverage incomplete")
    _assert(payload["ai_blind_preference_check"]["data_visible_to_ai"] == "train_validation_only", "AI blind check used wrong data scope")
    _assert(payload["ai_blind_preference_check"]["test_period_locked_before_preference"] is True, "test period not locked")
    _assert(
        payload["recommended_next_research_style"]
        == payload["ai_blind_preference_check"]["ai_preferred_style_before_test"],
        "recommended style must come from train/validation blind preference",
    )
    _assert(manifest["schema_version"] == "phase10.simulation_manifest.v1", "simulation manifest schema mismatch")
    _assert(manifest["order_allowed"] is False and manifest["deployable"] is False, "manifest boundary mismatch")
    _assert(adapter["adapter_scope"] == "read_only_backtest_input_spike", "adapter scope mismatch")
    _assert(adapter["order_allowed"] is False and adapter["deployable"] is False, "adapter boundary mismatch")
    _assert(report.order_allowed is False and report.deployable is False, "report model boundary mismatch")

    cli_dir = output_dir / "cli"
    cli_stdout = StringIO()
    with redirect_stdout(cli_stdout):
        status = cli_main(
            [
                "--run-strategy-tournament",
                "--output-dir",
                str(cli_dir / "research"),
                "--audit-output-dir",
                str(cli_dir / "audit"),
                "--adapter-output-dir",
                str(cli_dir / "adapter"),
            ]
        )
    _assert(status == 0, "Phase 10 CLI failed")
    _assert("Order allowed: false" in cli_stdout.getvalue(), "Phase 10 CLI did not print boundary")

    print(f"STAGE_10_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("STRATEGY_STYLE_REGISTRY_CHECK=PASS")
    print("WALK_FORWARD_SPLIT_CHECK=PASS")
    print("COST_SENSITIVITY_CHECK=PASS")
    print("STRESS_TEST_CHECK=PASS")
    print("AI_BLIND_PREFERENCE_CHECK=PASS")
    print("SIMULATION_MANIFEST_CHECK=PASS")
    print("NAUTILUS_ADAPTER_SAMPLE_CHECK=PASS")
    print("DEPLOYABLE_TRUE_COUNT=0")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 10 offline tournament gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_10_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
