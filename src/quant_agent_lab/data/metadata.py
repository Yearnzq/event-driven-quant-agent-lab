from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


DATASET_SCHEMA_VERSION = "phase2.dataset.v1"


class DataAssetMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    path: str
    sha256: str
    size_bytes: int = Field(ge=0)
    required: bool = True


class DatasetManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = DATASET_SCHEMA_VERSION
    dataset_id: str
    symbol: str
    as_of: datetime
    source: str
    bars_1h_csv: str = "bars_1h.csv"
    bars_1d_csv: str = "bars_1d.csv"
    portfolio_json: str = "portfolio.json"
    assets: list[DataAssetMetadata]
    quality_rules: list[str] = Field(default_factory=list)
    order_allowed: bool = False
    human_required: bool = True


class DatasetManifestValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    reasons: list[str] = Field(default_factory=list)
    manifest: DatasetManifest | None = None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _asset(root: Path, role: str, relative_path: str) -> DataAssetMetadata:
    path = root / relative_path
    return DataAssetMetadata(
        role=role,
        path=relative_path,
        sha256=file_sha256(path),
        size_bytes=path.stat().st_size,
    )


def build_dataset_manifest(
    dataset_dir: Path,
    *,
    symbol: str,
    as_of: datetime,
    source: str,
    dataset_id: str | None = None,
    bars_1h_csv: str = "bars_1h.csv",
    bars_1d_csv: str = "bars_1d.csv",
    portfolio_json: str = "portfolio.json",
) -> DatasetManifest:
    as_of_utc = as_of.astimezone(timezone.utc) if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
    normalized_id = dataset_id or f"{source}:{symbol}:{as_of_utc.isoformat()}"
    quality_rules = [
        "required_files_present",
        "asset_sha256_matches",
        "bars_have_schema",
        "data_gate_checks_staleness_gaps_duplicates_symbols",
        "cleaned_text_only_no_raw_body",
    ]
    return DatasetManifest(
        dataset_id=normalized_id,
        symbol=symbol,
        as_of=as_of_utc,
        source=source,
        bars_1h_csv=bars_1h_csv,
        bars_1d_csv=bars_1d_csv,
        portfolio_json=portfolio_json,
        assets=[
            _asset(dataset_dir, "bars_1h", bars_1h_csv),
            _asset(dataset_dir, "bars_1d", bars_1d_csv),
            _asset(dataset_dir, "portfolio", portfolio_json),
        ],
        quality_rules=quality_rules,
    )


def write_dataset_manifest(
    dataset_dir: Path,
    *,
    symbol: str,
    as_of: datetime,
    source: str,
    dataset_id: str | None = None,
) -> Path:
    manifest = build_dataset_manifest(
        dataset_dir,
        symbol=symbol,
        as_of=as_of,
        source=source,
        dataset_id=dataset_id,
    )
    path = dataset_dir / "metadata.json"
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return path


def load_dataset_manifest(path: Path) -> DatasetManifest:
    return DatasetManifest.model_validate_json(path.read_text(encoding="utf-8"))


def validate_dataset_manifest(dataset_dir: Path) -> DatasetManifestValidation:
    manifest_path = dataset_dir / "metadata.json"
    reasons: list[str] = []
    if not manifest_path.exists():
        return DatasetManifestValidation(status="fail", reasons=["metadata.json missing"])

    try:
        manifest = load_dataset_manifest(manifest_path)
    except Exception as exc:  # noqa: BLE001 - report schema failures as data quality failures.
        return DatasetManifestValidation(status="fail", reasons=[f"metadata schema invalid: {exc}"])

    if manifest.schema_version != DATASET_SCHEMA_VERSION:
        reasons.append("unsupported dataset schema_version")
    if manifest.order_allowed:
        reasons.append("dataset manifest must keep order_allowed=false")
    if not manifest.human_required:
        reasons.append("dataset manifest must keep human_required=true")

    roles = {asset.role for asset in manifest.assets}
    for required_role in {"bars_1h", "bars_1d", "portfolio"}:
        if required_role not in roles:
            reasons.append(f"required asset missing from manifest: {required_role}")

    for asset in manifest.assets:
        path = dataset_dir / asset.path
        if not path.exists():
            reasons.append(f"asset file missing: {asset.path}")
            continue
        if path.stat().st_size != asset.size_bytes:
            reasons.append(f"asset size mismatch: {asset.path}")
        if file_sha256(path) != asset.sha256:
            reasons.append(f"asset sha256 mismatch: {asset.path}")

    status = "fail" if reasons else "pass"
    return DatasetManifestValidation(status=status, reasons=reasons, manifest=manifest)
