from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    schema_version: str = "phase1.advisory.v1"
    input_hash: str
    output_hash: str
    model_provider: str = "mock"
    model_name: str = "mock-agents"
    prompt_version: str = "mock.v1"
    validation_result: str


class ArtifactRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    content_type: str


class ArtifactCatalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "phase3.artifact_catalog.v1"
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    artifacts: list[ArtifactRecord]
    order_allowed: bool = False
    human_required: bool = True


class RunManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = "phase3.run_manifest.v1"
    phase: int = 3
    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    symbol: str
    as_of: datetime
    input_hash: str
    output_hash: str
    config_hash: str
    artifact_catalog_hash: str
    validation_result: str
    replay_entrypoint: str = "quant_agent_lab.app.cli"
    model_provider: str = "mock"
    order_allowed: bool = False
    human_required: bool = True


class RunManifestValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    reasons: list[str] = Field(default_factory=list)
    manifest: RunManifest | None = None
    catalog: ArtifactCatalog | None = None


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return path


def append_jsonl(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
        handle.write("\n")
    return path


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "text/markdown"
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/jsonl"
    return "application/octet-stream"


def artifact_record(root: Path, path: Path, *, role: str) -> ArtifactRecord:
    return ArtifactRecord(
        role=role,
        path=path.relative_to(root).as_posix(),
        sha256=file_sha256(path),
        size_bytes=path.stat().st_size,
        content_type=_content_type(path),
    )


def write_artifact_catalog(
    output_dir: Path,
    *,
    run_id: str,
    artifacts: list[tuple[str, Path]],
) -> Path:
    records = [artifact_record(output_dir, path, role=role) for role, path in artifacts]
    catalog = ArtifactCatalog(run_id=run_id, artifacts=records)
    return write_json(output_dir / "artifact-catalog.json", catalog.model_dump(mode="json"))


def write_run_manifest(
    output_dir: Path,
    *,
    run_id: str,
    symbol: str,
    as_of: datetime,
    input_hash: str,
    output_hash: str,
    config_hash: str,
    validation_result: str,
    artifact_catalog_path: Path,
) -> Path:
    manifest = RunManifest(
        run_id=run_id,
        symbol=symbol,
        as_of=as_of,
        input_hash=input_hash,
        output_hash=output_hash,
        config_hash=config_hash,
        artifact_catalog_hash=file_sha256(artifact_catalog_path),
        validation_result=validation_result,
    )
    return write_json(output_dir / "run-manifest.json", manifest.model_dump(mode="json"))


def validate_run_manifest(output_dir: Path) -> RunManifestValidation:
    reasons: list[str] = []
    manifest_path = output_dir / "run-manifest.json"
    catalog_path = output_dir / "artifact-catalog.json"
    if not manifest_path.exists():
        reasons.append("run-manifest.json missing")
    if not catalog_path.exists():
        reasons.append("artifact-catalog.json missing")
    if reasons:
        return RunManifestValidation(status="fail", reasons=reasons)

    try:
        manifest = RunManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        catalog = ArtifactCatalog.model_validate_json(catalog_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validation failures are audit failures here.
        return RunManifestValidation(status="fail", reasons=[f"manifest schema invalid: {exc}"])

    if manifest.schema_version != "phase3.run_manifest.v1":
        reasons.append("unsupported run manifest schema_version")
    if catalog.schema_version != "phase3.artifact_catalog.v1":
        reasons.append("unsupported artifact catalog schema_version")
    if manifest.run_id != catalog.run_id:
        reasons.append("run_id mismatch between manifest and catalog")
    if manifest.artifact_catalog_hash != file_sha256(catalog_path):
        reasons.append("artifact catalog hash mismatch")
    if manifest.order_allowed:
        reasons.append("run manifest must keep order_allowed=false")
    if not manifest.human_required:
        reasons.append("run manifest must keep human_required=true")
    if catalog.order_allowed:
        reasons.append("artifact catalog must keep order_allowed=false")
    if not catalog.human_required:
        reasons.append("artifact catalog must keep human_required=true")

    roles = {artifact.role for artifact in catalog.artifacts}
    for required_role in {"report_markdown", "result_json", "audit_json", "audit_log"}:
        if required_role not in roles:
            reasons.append(f"required artifact missing from catalog: {required_role}")

    for artifact in catalog.artifacts:
        path = output_dir / artifact.path
        if not path.exists():
            reasons.append(f"artifact file missing: {artifact.path}")
            continue
        if path.stat().st_size != artifact.size_bytes:
            reasons.append(f"artifact size mismatch: {artifact.path}")
        if file_sha256(path) != artifact.sha256:
            reasons.append(f"artifact sha256 mismatch: {artifact.path}")

    return RunManifestValidation(
        status="fail" if reasons else "pass",
        reasons=reasons,
        manifest=manifest,
        catalog=catalog,
    )
