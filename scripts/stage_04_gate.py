from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quant_agent_lab.app.cli import main as cli_main  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402
from quant_agent_lab.data.importers import write_sample_csv_dataset  # noqa: E402
from quant_agent_lab.data.metadata import validate_dataset_manifest  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-04-gate")
RESEARCH_ROLES = {"research_markdown", "research_json", "registry_json"}


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read_text_artifacts(root: Path) -> str:
    parts: list[str] = []
    for path in root.rglob("*"):
        if path.suffix.lower() in {".md", ".json", ".jsonl"}:
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def run_stage_04_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_dir = write_sample_csv_dataset(output_dir / "sample", symbol="BTC-USDT")
    sample_manifest = validate_dataset_manifest(sample_dir)
    _assert(sample_manifest.status == "pass", f"sample manifest failed: {sample_manifest.reasons}")

    research_dir = output_dir / "research"
    exit_code = cli_main(
        [
            "--evaluate-signals",
            "--csv-dir",
            str(sample_dir),
            "--output-dir",
            str(research_dir),
        ]
    )
    _assert(exit_code == 0, "signal research CLI failed")

    report_path = research_dir / "signal_research_report.json"
    markdown_path = research_dir / "signal_research_report.md"
    registry_path = research_dir / "signal-registry.json"
    _assert(report_path.exists(), "signal research JSON missing")
    _assert(markdown_path.exists(), "signal research Markdown missing")
    _assert(registry_path.exists(), "signal registry JSON missing")
    _assert((research_dir / "artifact-catalog.json").exists(), "research artifact catalog missing")
    _assert((research_dir / "run-manifest.json").exists(), "research run manifest missing")

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    _assert(payload["schema_version"] == "phase4.signal_research.v1", "wrong research schema version")
    _assert(payload["strategy_count"] >= 3, "expected at least three signal strategies")
    _assert(payload["order_allowed"] is False, "research report allowed orders")
    _assert(payload["human_required"] is True, "research report disabled human review")
    _assert(payload["deployable"] is False, "research report marked deployable")
    families = {summary["signal_family"] for summary in payload["summaries"]}
    _assert({"trend", "breakout", "volatility"}.issubset(families), "missing required signal families")
    _assert(payload["ranking"], "research ranking missing")
    first_row = payload["ranking"][0]
    _assert(0 <= first_row["research_score"] <= 1, "research score must be normalized")
    for component in {
        "cumulative_return_rank",
        "average_return_rank",
        "hit_rate_rank",
        "drawdown_inverse_rank",
        "directional_coverage_rank",
    }:
        _assert(component in first_row["score_components"], f"score component missing: {component}")
    _assert("Not a trading instruction" in payload["disclaimer"], "research disclaimer missing")

    manifest_validation = validate_run_manifest(research_dir, required_roles=RESEARCH_ROLES)
    _assert(
        manifest_validation.status == "pass",
        f"research manifest validation failed: {manifest_validation.reasons}",
    )

    tampered_dir = output_dir / "research_tampered"
    shutil.copytree(research_dir, tampered_dir)
    with (tampered_dir / "signal_research_report.md").open("a", encoding="utf-8") as handle:
        handle.write("\nmanual tamper for phase 4 gate\n")
    tampered_validation = validate_run_manifest(tampered_dir, required_roles=RESEARCH_ROLES)
    _assert(tampered_validation.status == "fail", "tampered research manifest unexpectedly passed")
    _assert(
        "artifact sha256 mismatch: signal_research_report.md" in tampered_validation.reasons,
        "tampered research artifact did not report sha256 mismatch",
    )

    text_blob = _read_text_artifacts(output_dir).lower()
    _assert('"order_allowed": true' not in text_blob, "order_allowed=true is forbidden")
    _assert("deployable\": true" not in text_blob, "research output must not be deployable")

    print(f"STAGE_04_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("SIGNAL_REGISTRY_CHECK=PASS")
    print("SIGNAL_RESEARCH_REPORT_CHECK=PASS")
    print("RESEARCH_ARTIFACT_CATALOG_CHECK=PASS")
    print("RESEARCH_TAMPER_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("DEPLOYABLE_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 4 signal research framework gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_04_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
