from __future__ import annotations

from quant_agent_lab.data.importers import write_bad_csv_dataset, write_sample_csv_dataset
from quant_agent_lab.data.metadata import load_dataset_manifest, validate_dataset_manifest


def test_sample_dataset_writes_valid_phase2_manifest(tmp_path) -> None:
    sample_dir = write_sample_csv_dataset(tmp_path / "sample", symbol="BTC-USDT")

    result = validate_dataset_manifest(sample_dir)
    manifest = load_dataset_manifest(sample_dir / "metadata.json")

    assert result.status == "pass"
    assert manifest.schema_version == "phase2.dataset.v1"
    assert manifest.symbol == "BTC-USDT"
    assert manifest.order_allowed is False
    assert manifest.human_required is True
    assert {asset.role for asset in manifest.assets} == {"bars_1h", "bars_1d", "portfolio"}


def test_dataset_manifest_detects_asset_tampering(tmp_path) -> None:
    sample_dir = write_sample_csv_dataset(tmp_path / "sample", symbol="BTC-USDT")
    with (sample_dir / "bars_1h.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    result = validate_dataset_manifest(sample_dir)

    assert result.status == "fail"
    assert "asset size mismatch: bars_1h.csv" in result.reasons
    assert "asset sha256 mismatch: bars_1h.csv" in result.reasons


def test_bad_dataset_manifest_can_be_valid_while_data_gate_fails(tmp_path) -> None:
    bad_dir = write_bad_csv_dataset(tmp_path / "bad", symbol="BTC-USDT")

    result = validate_dataset_manifest(bad_dir)

    assert result.status == "pass"
