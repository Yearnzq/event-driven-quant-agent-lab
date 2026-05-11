from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from io import StringIO
import json
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from quant_agent_lab.agents.model import SingleModelRecommendationAgent  # noqa: E402
from quant_agent_lab.app.cli import main as cli_main  # noqa: E402
from quant_agent_lab.app.pipeline import run_daily_pipeline  # noqa: E402
from quant_agent_lab.core.config import ModelProviderConfig, PipelineConfig  # noqa: E402
from quant_agent_lab.core.schemas import Action, GateStatus, ModelCallAuditRecord  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-08-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read_model_audit(output_dir: Path) -> list[ModelCallAuditRecord]:
    path = output_dir / "model-call-audit.json"
    _assert(path.exists(), f"model call audit missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [ModelCallAuditRecord.model_validate(item) for item in payload]


def _assert_no_raw_error_or_secret(output_dir: Path) -> None:
    forbidden = ["deterministic mock failure", "api_key", "secret", "private_key"]
    for path in output_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            _assert(token not in text, f"forbidden text leaked into {path.name}: {token}")


def run_stage_08_gate(output_dir: Path, *, allow_real_model_call: bool = False) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fake_dir = output_dir / "single-model-fake"
    fake_config = PipelineConfig(output_dir=fake_dir)
    fake_result = run_daily_pipeline(
        config=fake_config,
        agents=[SingleModelRecommendationAgent(fake_config.model_provider)],
    )
    _assert(fake_result.model_call_audits, "single fake model did not record audits")
    _assert(fake_result.model_call_audits[0].provider == "fake", "single fake model used wrong provider")
    _assert(fake_result.model_call_audits[0].status == GateStatus.PASS, "single fake model audit did not pass")
    _assert("Model Call Audit" in fake_result.report_markdown, "model call audit missing from report")
    _assert("input_tokens" in fake_result.report_markdown, "model token audit missing from report")
    _assert(fake_result.recommendation.order_allowed is False, "single fake model recommendation allowed orders")
    _assert(fake_result.risk_decision.order_allowed is False, "single fake model risk decision allowed orders")
    manifest_validation = validate_run_manifest(fake_dir, required_roles={"model_call_audit"})
    _assert(manifest_validation.status == "pass", f"single fake model manifest failed: {manifest_validation.reasons}")
    _assert_no_raw_error_or_secret(fake_dir)

    missing_key_dir = output_dir / "single-model-openai-missing-key"
    missing_key_env = "QAL_STAGE08_INTENTIONALLY_MISSING_OPENAI_API_KEY"
    os.environ.pop(missing_key_env, None)
    previous_provider_enabled = os.environ.get("QAL_ENABLE_OPENAI_PROVIDER")
    os.environ["QAL_ENABLE_OPENAI_PROVIDER"] = "1"
    missing_key_config = PipelineConfig(
        output_dir=missing_key_dir,
        model_provider=ModelProviderConfig(
            provider="openai",
            model_name="gpt-5.4-mini",
            allow_network=True,
            api_key_env=missing_key_env,
        ),
    )
    missing_key_result = run_daily_pipeline(
        config=missing_key_config,
        agents=[SingleModelRecommendationAgent(missing_key_config.model_provider)],
    )
    if previous_provider_enabled is None:
        os.environ.pop("QAL_ENABLE_OPENAI_PROVIDER", None)
    else:
        os.environ["QAL_ENABLE_OPENAI_PROVIDER"] = previous_provider_enabled
    _assert(missing_key_result.agent_opinions[0].status == GateStatus.FAIL, "missing key did not fail agent")
    _assert(missing_key_result.recommendation.action == Action.INSUFFICIENT_EVIDENCE, "missing key did not fail closed")
    _assert(missing_key_result.risk_decision.final_action == Action.INSUFFICIENT_EVIDENCE, "missing key final action mismatch")
    _assert(missing_key_result.risk_decision.order_allowed is False, "missing key scenario allowed orders")
    missing_key_audit = _read_model_audit(missing_key_dir)[0]
    _assert(missing_key_audit.provider == "openai", "missing key audit provider mismatch")
    _assert(missing_key_audit.status == GateStatus.FAIL, "missing key audit did not fail")
    _assert(missing_key_audit.error_message == "RuntimeError: redacted", "missing key error was not redacted")
    _assert_no_raw_error_or_secret(missing_key_dir)

    cli_dir = output_dir / "cli-single-model-fake"
    cli_stdout = StringIO()
    with redirect_stdout(cli_stdout):
        cli_status = cli_main(["--run-single-model-advisory", "--output-dir", str(cli_dir)])
    _assert(cli_status == 0, "single model CLI failed")
    _assert("Model Call Audit" in cli_stdout.getvalue(), "single model CLI report missing audit section")
    _assert((cli_dir / "model-call-audit.json").exists(), "single model CLI audit missing")

    if allow_real_model_call:
        real_dir = output_dir / "single-model-openai-real"
        real_provider_config = ModelProviderConfig(
            provider="openai",
            model_name="gpt-5.4-mini",
            allow_network=True,
        )
        if os.environ.get("QAL_ENABLE_OPENAI_PROVIDER") != "1":
            print("REAL_MODEL_OPTIONAL_CHECK=SKIPPED_PROVIDER_DISABLED")
            real_provider_config = None
        elif not os.environ.get(real_provider_config.api_key_env):
            print("REAL_MODEL_OPTIONAL_CHECK=SKIPPED_MISSING_OPENAI_API_KEY")
            real_provider_config = None
        if real_provider_config is not None:
            real_config = PipelineConfig(
                output_dir=real_dir,
                model_provider=real_provider_config,
            )
            real_result = run_daily_pipeline(
                config=real_config,
                agents=[SingleModelRecommendationAgent(real_config.model_provider)],
            )
            _assert(real_result.model_call_audits, "real model run did not write audit")
            _assert(real_result.model_call_audits[0].provider == "openai", "real model audit provider mismatch")
            _assert(real_result.model_call_audits[0].status == GateStatus.PASS, "real model run did not pass")
            _assert(real_result.risk_decision.order_allowed is False, "real model run allowed orders")
            print("REAL_MODEL_OPTIONAL_CHECK=PASS")
    else:
        print("REAL_MODEL_OPTIONAL_CHECK=SKIPPED")

    print(f"STAGE_08_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("SINGLE_MODEL_AGENT_CHECK=PASS")
    print("SINGLE_MODEL_REPORT_CHECK=PASS")
    print("OPENAI_PROVIDER_FAIL_CLOSED_CHECK=PASS")
    print("MODEL_AUDIT_ARTIFACT_CHECK=PASS")
    print("MODEL_ERROR_REDACTION_CHECK=PASS")
    print("DATA_RISK_GATE_BOUNDARY_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 8 single-model advisory gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--allow-real-model-call", action="store_true")
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_08_gate(args.output_dir, allow_real_model_call=args.allow_real_model_call)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
