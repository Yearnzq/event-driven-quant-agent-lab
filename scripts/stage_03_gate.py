from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quant_agent_lab.app.pipeline import run_daily_pipeline  # noqa: E402
from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig  # noqa: E402
from quant_agent_lab.core.schemas import Action, GateStatus  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402
from quant_agent_lab.data.importers import write_bad_csv_dataset, write_sample_csv_dataset  # noqa: E402
from quant_agent_lab.data.metadata import validate_dataset_manifest  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-03-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _csv_config(dataset_dir: Path) -> CsvDataConfig:
    return CsvDataConfig(
        bars_1h_csv=dataset_dir / "bars_1h.csv",
        bars_1d_csv=dataset_dir / "bars_1d.csv",
        portfolio_json=dataset_dir / "portfolio.json",
    )


def _assert_valid_run_manifest(report_dir: Path) -> None:
    validation = validate_run_manifest(report_dir)
    _assert(validation.status == "pass", f"run manifest validation failed: {validation.reasons}")
    _assert(validation.manifest is not None, "run manifest missing after validation")
    _assert(validation.catalog is not None, "artifact catalog missing after validation")
    _assert(validation.manifest.order_allowed is False, "run manifest allowed orders")
    _assert(validation.manifest.human_required is True, "run manifest disabled human review")
    _assert(validation.catalog.order_allowed is False, "artifact catalog allowed orders")
    _assert(validation.catalog.human_required is True, "artifact catalog disabled human review")


def run_stage_03_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    mock_report_dir = output_dir / "reports" / "mock"
    mock_result = run_daily_pipeline(output_dir=mock_report_dir)
    _assert(mock_result.risk_decision.order_allowed is False, "mock run allowed orders")
    _assert_valid_run_manifest(mock_report_dir)

    sample_dir = write_sample_csv_dataset(output_dir / "sample_good", symbol="BTC-USDT")
    sample_manifest = validate_dataset_manifest(sample_dir)
    _assert(sample_manifest.status == "pass", f"sample manifest failed: {sample_manifest.reasons}")
    _assert(sample_manifest.manifest is not None, "sample manifest missing")
    csv_report_dir = output_dir / "reports" / "csv"
    csv_result = run_daily_pipeline(
        config=PipelineConfig(
            data_source="csv",
            as_of=sample_manifest.manifest.as_of,
            csv=_csv_config(sample_dir),
            output_dir=csv_report_dir,
        )
    )
    _assert(csv_result.data_validation.status == GateStatus.PASS, "csv run failed Data Gate")
    _assert(csv_result.risk_decision.order_allowed is False, "csv run allowed orders")
    _assert_valid_run_manifest(csv_report_dir)

    tampered_report_dir = output_dir / "reports" / "tampered"
    shutil.copytree(csv_report_dir, tampered_report_dir)
    report_path = next(tampered_report_dir.glob("*.md"))
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\nmanual tamper for phase 3 gate\n")
    tampered_validation = validate_run_manifest(tampered_report_dir)
    _assert(tampered_validation.status == "fail", "tampered artifact manifest unexpectedly passed")
    _assert(
        any(reason.startswith("artifact sha256 mismatch:") for reason in tampered_validation.reasons),
        "tampered artifact did not report sha256 mismatch",
    )

    bad_dir = write_bad_csv_dataset(output_dir / "sample_bad_gap", symbol="BTC-USDT")
    bad_manifest = validate_dataset_manifest(bad_dir)
    _assert(bad_manifest.status == "pass", f"bad sample manifest failed: {bad_manifest.reasons}")
    _assert(bad_manifest.manifest is not None, "bad sample manifest missing")
    bad_report_dir = output_dir / "reports" / "bad_gap"
    bad_result = run_daily_pipeline(
        config=PipelineConfig(
            data_source="csv",
            as_of=bad_manifest.manifest.as_of,
            csv=_csv_config(bad_dir),
            output_dir=bad_report_dir,
        )
    )
    _assert(bad_result.data_validation.status == GateStatus.FAIL, "bad dataset passed Data Gate")
    _assert(
        bad_result.recommendation.action == Action.INSUFFICIENT_EVIDENCE,
        "Data Gate failure did not force insufficient_evidence",
    )
    _assert_valid_run_manifest(bad_report_dir)

    print(f"STAGE_03_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("RUN_MANIFEST_CHECK=PASS")
    print("ARTIFACT_CATALOG_CHECK=PASS")
    print("ARTIFACT_TAMPER_CHECK=PASS")
    print("BAD_DATA_AUDIT_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 3 artifact and audit ledger gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_03_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
