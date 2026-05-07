from __future__ import annotations

from quant_agent_lab.app.pipeline import run_daily_pipeline
from quant_agent_lab.data.audit import stable_hash, validate_run_manifest


def test_stable_hash_is_order_independent_for_dicts() -> None:
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_pipeline_writes_valid_run_manifest_and_artifact_catalog(tmp_path) -> None:
    result = run_daily_pipeline(output_dir=tmp_path)

    validation = validate_run_manifest(tmp_path)

    assert validation.status == "pass"
    assert validation.manifest is not None
    assert validation.catalog is not None
    assert validation.manifest.run_id == result.run_id
    assert validation.manifest.order_allowed is False
    assert validation.manifest.human_required is True
    assert {artifact.role for artifact in validation.catalog.artifacts} == {
        "report_markdown",
        "result_json",
        "audit_json",
        "audit_log",
    }


def test_run_manifest_detects_artifact_tampering(tmp_path) -> None:
    result = run_daily_pipeline(output_dir=tmp_path)
    report_path = tmp_path / f"{result.run_id}.md"
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write("\nmanual tamper\n")

    validation = validate_run_manifest(tmp_path)

    assert validation.status == "fail"
    assert f"artifact sha256 mismatch: {result.run_id}.md" in validation.reasons
