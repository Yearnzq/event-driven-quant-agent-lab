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

from quant_agent_lab.a2a.mock import A2AClient, A2AClientAgent, MockA2AAgentServer  # noqa: E402
from quant_agent_lab.agents.model import SingleModelRecommendationAgent  # noqa: E402
from quant_agent_lab.app.cli import main as cli_main  # noqa: E402
from quant_agent_lab.app.pipeline import run_daily_pipeline  # noqa: E402
from quant_agent_lab.core.config import PipelineConfig  # noqa: E402
from quant_agent_lab.core.schemas import Action, GateStatus  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-09-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _assert_no_secret_or_raw_prompt(output_dir: Path) -> None:
    forbidden = ["api_key", "secret", "private_key", "rendered_prompt"]
    for path in output_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            _assert(token not in text, f"forbidden text leaked into {path.name}: {token}")


def _run_a2a_fake(output_dir: Path) -> None:
    config = PipelineConfig(output_dir=output_dir)
    server = MockA2AAgentServer(SingleModelRecommendationAgent(config.model_provider))
    client = A2AClient(server, timeout_seconds=5.0, max_retries=1)
    result = run_daily_pipeline(config=config, agents=[A2AClientAgent(client)])

    _assert(result.a2a_agent_cards, "A2A agent card missing from result")
    _assert(result.a2a_agent_cards[0].order_allowed is False, "A2A card allowed orders")
    _assert(result.a2a_agent_cards[0].human_required is True, "A2A card skipped human review")
    _assert(result.a2a_trace_records, "A2A trace missing from result")
    _assert(result.a2a_trace_records[0].run_id == result.run_id, "A2A trace run_id mismatch")
    _assert(result.a2a_trace_records[0].status == GateStatus.PASS, "A2A fake trace did not pass")
    _assert(result.a2a_trace_records[0].request_hash, "A2A request hash missing")
    _assert(result.a2a_trace_records[0].response_hash, "A2A response hash missing")
    _assert("A2A Trace" in result.report_markdown, "A2A report section missing")
    _assert(result.recommendation.order_allowed is False, "A2A recommendation allowed orders")
    _assert(result.risk_decision.order_allowed is False, "A2A risk decision allowed orders")
    _assert((output_dir / "a2a-agent-card.json").exists(), "A2A agent card artifact missing")
    _assert((output_dir / "a2a-trace.json").exists(), "A2A trace artifact missing")
    manifest = validate_run_manifest(output_dir, required_roles={"a2a_agent_card", "a2a_trace"})
    _assert(manifest.status == "pass", f"A2A manifest failed: {manifest.reasons}")
    card_payload = json.loads((output_dir / "a2a-agent-card.json").read_text(encoding="utf-8"))[0]
    trace_payload = json.loads((output_dir / "a2a-trace.json").read_text(encoding="utf-8"))[0]
    _assert(card_payload["schema_version"] == "phase9.agent_card.v1", "A2A card schema mismatch")
    _assert(trace_payload["schema_version"] == "phase9.a2a_trace.v1", "A2A trace schema mismatch")
    _assert_no_secret_or_raw_prompt(output_dir)


def _run_a2a_timeout(output_dir: Path) -> None:
    config = PipelineConfig(output_dir=output_dir)
    server = MockA2AAgentServer(
        SingleModelRecommendationAgent(config.model_provider),
        response_delay_seconds=0.05,
    )
    client = A2AClient(server, timeout_seconds=0.01, max_retries=1)
    result = run_daily_pipeline(config=config, agents=[A2AClientAgent(client)])

    _assert(result.agent_opinions[0].status == GateStatus.FAIL, "A2A timeout did not fail agent")
    _assert(
        result.agent_opinions[0].action_bias == Action.INSUFFICIENT_EVIDENCE,
        "A2A timeout did not degrade to insufficient evidence",
    )
    _assert(result.agent_opinions[0].error_message == "TimeoutError: redacted", "A2A timeout leaked error")
    _assert(result.a2a_trace_records[0].status == GateStatus.FAIL, "A2A timeout trace did not fail")
    _assert(result.a2a_trace_records[0].attempt_count == 2, "A2A retry count mismatch")
    _assert(result.risk_decision.order_allowed is False, "A2A timeout allowed orders")
    _assert_no_secret_or_raw_prompt(output_dir)


def run_stage_09_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _run_a2a_fake(output_dir / "a2a-fake")
    _run_a2a_timeout(output_dir / "a2a-timeout")

    cli_dir = output_dir / "cli-a2a-fake"
    cli_stdout = StringIO()
    with redirect_stdout(cli_stdout):
        cli_status = cli_main(["--run-a2a-advisory", "--output-dir", str(cli_dir)])
    _assert(cli_status == 0, "A2A CLI failed")
    _assert("A2A Trace" in cli_stdout.getvalue(), "A2A CLI report missing trace section")
    _assert((cli_dir / "a2a-agent-card.json").exists(), "A2A CLI card missing")
    _assert((cli_dir / "a2a-trace.json").exists(), "A2A CLI trace missing")

    print(f"STAGE_09_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("A2A_AGENT_CARD_CHECK=PASS")
    print("A2A_CLIENT_SERVER_CHECK=PASS")
    print("A2A_TIMEOUT_RETRY_CHECK=PASS")
    print("A2A_TRACE_ARTIFACT_CHECK=PASS")
    print("A2A_ERROR_REDACTION_CHECK=PASS")
    print("A2A_DATA_RISK_BOUNDARY_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 9 A2A service-boundary gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_09_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
