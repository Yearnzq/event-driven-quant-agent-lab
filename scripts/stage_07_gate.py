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
from quant_agent_lab.core.config import ModelProviderConfig, PipelineConfig  # noqa: E402
from quant_agent_lab.core.schemas import GateStatus, ModelCallAuditRecord  # noqa: E402
from quant_agent_lab.data.audit import ArtifactCatalog, file_sha256  # noqa: E402
from quant_agent_lab.models.fake_provider import (  # noqa: E402
    FakeStructuredModelProvider,
    run_fake_model_boundary_check,
)


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-07-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_artifact_catalog(output_dir: Path) -> None:
    catalog_path = output_dir / "artifact-catalog.json"
    _assert(catalog_path.exists(), "artifact catalog missing")
    catalog = ArtifactCatalog.model_validate_json(catalog_path.read_text(encoding="utf-8"))
    roles = {artifact.role for artifact in catalog.artifacts}
    for role in {
        "prompt_registry",
        "rendered_prompt_meta",
        "fake_agent_opinion",
        "model_call_audit",
        "model_boundary_result",
    }:
        _assert(role in roles, f"artifact role missing: {role}")
    _assert(catalog.order_allowed is False, "artifact catalog allowed orders")
    _assert(catalog.human_required is True, "artifact catalog disabled human review")
    for artifact in catalog.artifacts:
        path = output_dir / artifact.path
        _assert(path.exists(), f"artifact missing: {artifact.path}")
        _assert(file_sha256(path) == artifact.sha256, f"artifact hash mismatch: {artifact.path}")


def _assert_no_sensitive_text(output_dir: Path) -> None:
    forbidden = ["api_key", "secret", "private_key", "raw_content"]

    def has_rendered_prompt_key(value) -> bool:
        if isinstance(value, dict):
            if "rendered_prompt" in value:
                return True
            return any(has_rendered_prompt_key(item) for item in value.values())
        if isinstance(value, list):
            return any(has_rendered_prompt_key(item) for item in value)
        return False

    for path in output_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        payload = json.loads(path.read_text(encoding="utf-8"))
        _assert(not has_rendered_prompt_key(payload), f"rendered prompt leaked into {path.name}")
        for token in forbidden:
            _assert(token not in text, f"forbidden token leaked into {path.name}: {token}")


def run_stage_07_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_output_dir = output_dir / "model-boundary"
    result = run_fake_model_boundary_check(
        config=PipelineConfig(output_dir=output_dir / "reports"),
        output_dir=model_output_dir,
    )
    _assert(result.audit_record.status == GateStatus.PASS, "fake provider call did not pass")
    _assert(result.audit_record.provider == "fake", "non-fake provider used")
    _assert(result.audit_record.output_schema == "AgentOpinion", "unexpected output schema")
    _assert(result.audit_record.prompt_hash, "prompt hash missing")
    _assert(result.audit_record.output_hash, "output hash missing")
    _assert(result.audit_record.estimated_input_tokens > 0, "input token estimate missing")
    _assert(result.audit_record.estimated_output_tokens > 0, "output token estimate missing")
    _assert(result.audit_record.estimated_cost_usd == 0, "fake provider cost must be zero")
    _assert(result.audit_record.latency_ms == 0, "fake provider latency must be deterministic zero")
    _assert(result.audit_record.order_allowed is False, "model audit allowed orders")
    _assert(result.audit_record.human_required is True, "model audit disabled human review")

    audit_payload = json.loads((model_output_dir / "model-call-audit.json").read_text(encoding="utf-8"))
    ModelCallAuditRecord.model_validate(audit_payload)
    prompt_meta = json.loads((model_output_dir / "rendered-prompt-meta.json").read_text(encoding="utf-8"))
    _assert("rendered_prompt" not in prompt_meta, "rendered prompt text was written to prompt meta")
    _assert(prompt_meta["prompt_hash"] == result.audit_record.prompt_hash, "prompt hash mismatch")
    _validate_artifact_catalog(model_output_dir)
    _assert_no_sensitive_text(model_output_dir)

    try:
        FakeStructuredModelProvider(ModelProviderConfig(allow_network=True))
    except ValueError:
        network_blocked = True
    else:
        network_blocked = False
    _assert(network_blocked, "network-enabled fake provider config was accepted")

    cli_output_dir = output_dir / "cli-model-boundary"
    cli_stdout = StringIO()
    with redirect_stdout(cli_stdout):
        cli_status = cli_main(["--run-fake-model-call", "--output-dir", str(cli_output_dir)])
    _assert(cli_status == 0, "CLI fake model call failed")
    _assert("phase7.model_call_audit.v1" in cli_stdout.getvalue(), "CLI audit output missing")
    _assert((cli_output_dir / "model-call-audit.json").exists(), "CLI model audit missing")

    default_provider_config = ModelProviderConfig()
    _assert(default_provider_config.provider == "fake", "Phase 7 default provider is not fake")
    _assert(default_provider_config.allow_network is False, "Phase 7 default provider allows network")

    print(f"STAGE_07_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("FAKE_PROVIDER_ONLY_CHECK=PASS")
    print("DEFAULT_PROVIDER_FAKE_CHECK=PASS")
    print("PROMPT_REGISTRY_CHECK=PASS")
    print("STRUCTURED_OUTPUT_SCHEMA_CHECK=PASS")
    print("MODEL_CALL_AUDIT_CHECK=PASS")
    print("COST_LATENCY_HASH_CHECK=PASS")
    print("NO_NETWORK_PROVIDER_CHECK=PASS")
    print("NO_RAW_PROMPT_ARTIFACT_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 7 fake model provider boundary checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_07_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
