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


def test_pipeline_artifacts_are_deterministic_across_output_dirs(tmp_path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"

    first = run_daily_pipeline(output_dir=first_dir)
    second = run_daily_pipeline(output_dir=second_dir)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert (first_dir / f"{first.run_id}.md").read_text(encoding="utf-8") == (
        second_dir / f"{second.run_id}.md"
    ).read_text(encoding="utf-8")
    assert (first_dir / f"{first.run_id}.audit.json").read_text(encoding="utf-8") == (
        second_dir / f"{second.run_id}.audit.json"
    ).read_text(encoding="utf-8")
    assert (first_dir / "run-manifest.json").read_text(encoding="utf-8") == (
        second_dir / "run-manifest.json"
    ).read_text(encoding="utf-8")


def test_pipeline_artifacts_never_emit_order_allowed_true(tmp_path) -> None:
    run_daily_pipeline(output_dir=tmp_path)

    for path in tmp_path.glob("*"):
        if path.suffix in {".json", ".jsonl", ".md"}:
            assert '"order_allowed": true' not in path.read_text(encoding="utf-8").lower()
            assert "order allowed: `true`" not in path.read_text(encoding="utf-8").lower()
