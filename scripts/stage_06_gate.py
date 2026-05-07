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

from quant_agent_lab.agents.mock import (  # noqa: E402
    MockContrarianAgent,
    MockFailingAgent,
    MockNoTradeAgent,
    MockRecommendationDraftAgent,
)
from quant_agent_lab.app.pipeline import run_daily_pipeline  # noqa: E402
from quant_agent_lab.core.schemas import Action, GateStatus, ModelDisagreement  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-06-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_manifest(output_dir: Path) -> None:
    validation = validate_run_manifest(output_dir)
    _assert(validation.status == "pass", f"run manifest failed: {validation.reasons}")


def run_stage_06_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    failure_dir = output_dir / "reports" / "agent_failure"
    failure_result = run_daily_pipeline(
        output_dir=failure_dir,
        agents=[MockRecommendationDraftAgent(), MockFailingAgent()],
    )
    _assert(failure_result.recommendation.action == Action.REVIEW_REQUIRED, "agent failure did not force review")
    _assert(failure_result.recommendation.model_disagreement == ModelDisagreement.HIGH, "agent failure did not mark high disagreement")
    _assert(failure_result.recommendation.decision_trace.failed_agent_count == 1, "failed agent was not counted")
    _assert("agent_failed:mock_failing_agent" in failure_result.recommendation.decision_trace.fallback_reasons, "failure fallback reason missing")
    _assert(failure_result.risk_decision.order_allowed is False, "failure scenario allowed orders")
    _assert("Decision Trace" in failure_result.report_markdown, "decision trace missing from report")
    _validate_manifest(failure_dir)

    conflict_result = run_daily_pipeline(
        agents=[MockRecommendationDraftAgent(), MockContrarianAgent()],
    )
    _assert(conflict_result.recommendation.action == Action.REVIEW_REQUIRED, "direction conflict did not force review")
    _assert("conflicting_directional_actions" in conflict_result.recommendation.decision_trace.disagreement_reasons, "direction conflict reason missing")
    _assert(conflict_result.risk_decision.order_allowed is False, "conflict scenario allowed orders")

    no_trade_result = run_daily_pipeline(agents=[MockNoTradeAgent()])
    _assert(no_trade_result.recommendation.action == Action.NO_TRADE, "no_trade vote was not preserved")
    _assert(no_trade_result.recommendation.target_position_pct == 0, "no_trade target position was not zero")
    _assert("no_trade_vote_present" in no_trade_result.recommendation.decision_trace.disagreement_reasons, "no_trade trace reason missing")
    _assert(no_trade_result.risk_decision.order_allowed is False, "no_trade scenario allowed orders")

    all_failed_result = run_daily_pipeline(agents=[MockFailingAgent()])
    _assert(all_failed_result.recommendation.action == Action.INSUFFICIENT_EVIDENCE, "all-failed agents did not force insufficient evidence")
    _assert(all_failed_result.recommendation.confidence == 0, "all-failed confidence was not zero")
    _assert(all_failed_result.risk_decision.status == GateStatus.FAIL, "all-failed risk gate did not fail")
    _assert(all_failed_result.risk_decision.final_action == Action.INSUFFICIENT_EVIDENCE, "all-failed final action mismatch")

    result_payload = json.loads((failure_dir / f"{failure_result.run_id}.json").read_text(encoding="utf-8"))
    _assert("decision_trace" in result_payload["recommendation"], "decision trace missing from result JSON")
    _assert(result_payload["recommendation"]["decision_trace"]["schema_version"] == "phase6.decision_trace.v1", "decision trace schema mismatch")

    print(f"STAGE_06_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("AGENT_FAILURE_DEGRADATION_CHECK=PASS")
    print("DISAGREEMENT_EXPLANATION_CHECK=PASS")
    print("NO_TRADE_DECISION_CHECK=PASS")
    print("INSUFFICIENT_EVIDENCE_FALLBACK_CHECK=PASS")
    print("DECISION_TRACE_AUDIT_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 6 advisory decision layer gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_06_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
