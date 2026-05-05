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

from quant_agent_lab.app.pipeline import run_daily_pipeline  # noqa: E402
from quant_agent_lab.core.config import PipelineConfig, RiskConfig  # noqa: E402
from quant_agent_lab.core.schemas import GateStatus, MarketSnapshot  # noqa: E402
from quant_agent_lab.data.audit import validate_run_manifest  # noqa: E402
from quant_agent_lab.data.mock import load_mock_market_snapshot  # noqa: E402
from quant_agent_lab.data.validation import validate_market_snapshot  # noqa: E402
from quant_agent_lab.decision.committee import build_recommendation_draft  # noqa: E402
from quant_agent_lab.risk.gate import RiskGate  # noqa: E402
from quant_agent_lab.strategy.signals import build_signal_bundle  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-05-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _with_hourly_closes(snapshot: MarketSnapshot, closes: list[float]) -> MarketSnapshot:
    bars = []
    for bar, close in zip(snapshot.bars_1h, closes):
        bars.append(
            bar.model_copy(
                update={
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                }
            )
        )
    return snapshot.model_copy(update={"bars_1h": bars})


def _risk_for_snapshot(snapshot: MarketSnapshot, gate: RiskGate):
    validation = validate_market_snapshot(snapshot)
    signals = build_signal_bundle(snapshot)
    draft = build_recommendation_draft(signals, validation, [])
    return gate.evaluate(draft, market=snapshot, signals=signals)


def run_stage_05_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    default_dir = output_dir / "reports" / "default"
    default_result = run_daily_pipeline(output_dir=default_dir)
    _assert(default_result.risk_decision.order_allowed is False, "default run allowed orders")
    _assert(default_result.recommendation.human_required is True, "default run disabled human review")
    for metric in {
        "existing_position_pct",
        "cash_pct",
        "recent_drawdown_pct",
        "downside_volatility",
        "worst_hourly_return",
        "portfolio_risk_budget_pct",
        "hourly_return_vol",
    }:
        _assert(metric in default_result.risk_decision.risk_metrics, f"risk metric missing: {metric}")
        _assert(metric in default_result.report_markdown, f"risk metric missing from report: {metric}")

    validation = validate_run_manifest(default_dir)
    _assert(validation.status == "pass", f"default run manifest failed: {validation.reasons}")
    result_payload = json.loads((default_dir / f"{default_result.run_id}.json").read_text(encoding="utf-8"))
    _assert("risk_metrics" in result_payload["risk_decision"], "risk metrics missing from result JSON")

    drawdown_snapshot = _with_hourly_closes(
        load_mock_market_snapshot(),
        [100.0 + index for index in range(60)]
        + [158.0, 150.0, 140.0, 132.0, 126.0, 120.0, 118.0, 116.0, 114.0, 112.0, 110.0, 108.0],
    )
    drawdown_risk = _risk_for_snapshot(
        drawdown_snapshot,
        RiskGate(max_recent_drawdown_pct=0.05),
    )
    _assert(drawdown_risk.status == GateStatus.FAIL, "drawdown scenario did not fail")
    _assert("recent drawdown exceeds limit" in drawdown_risk.reasons, "drawdown reason missing")

    downside_snapshot = _with_hourly_closes(
        load_mock_market_snapshot(),
        [100.0 + index * 0.1 for index in range(60)]
        + [106.0, 95.0, 96.0, 84.0, 85.0, 74.0, 75.0, 73.0, 74.0, 72.0, 73.0, 71.0],
    )
    downside_risk = _risk_for_snapshot(
        downside_snapshot,
        RiskGate(max_downside_volatility=0.02, max_single_hour_loss_pct=0.05),
    )
    _assert(downside_risk.status == GateStatus.FAIL, "downside scenario did not fail")
    _assert("downside volatility exceeds limit" in downside_risk.reasons, "downside volatility reason missing")
    _assert("single hour loss exceeds limit" in downside_risk.reasons, "single hour loss reason missing")

    budget_risk = _risk_for_snapshot(
        load_mock_market_snapshot(),
        RiskGate(max_portfolio_risk_budget_pct=0.000001),
    )
    _assert(budget_risk.status == GateStatus.FAIL, "portfolio risk budget scenario did not fail")
    _assert("portfolio risk budget exceeds limit" in budget_risk.reasons, "portfolio budget reason missing")

    strict_result = run_daily_pipeline(
        config=PipelineConfig(
            output_dir=output_dir / "reports" / "strict",
            risk=RiskConfig(max_recent_drawdown_pct=0.000001),
        )
    )
    _assert(strict_result.risk_decision.status == GateStatus.FAIL, "strict risk config did not fail")
    _assert(strict_result.risk_decision.order_allowed is False, "strict run allowed orders")

    print(f"STAGE_05_OFFLINE_GATE=PASS output_dir={output_dir}")
    print("RISK_METRICS_CHECK=PASS")
    print("DRAWDOWN_RULE_CHECK=PASS")
    print("DOWNSIDE_VOLATILITY_RULE_CHECK=PASS")
    print("SINGLE_HOUR_LOSS_RULE_CHECK=PASS")
    print("PORTFOLIO_RISK_BUDGET_RULE_CHECK=PASS")
    print("RISK_CONFIG_AUDIT_CHECK=PASS")
    print("ORDER_ALLOWED_TRUE_COUNT=0")
    print("HUMAN_REQUIRED=true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 5 deterministic risk rule gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_stage_05_gate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
