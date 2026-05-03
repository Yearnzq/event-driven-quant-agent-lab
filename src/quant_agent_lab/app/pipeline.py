from __future__ import annotations

from pathlib import Path

from quant_agent_lab.agents.mock import default_mock_agents
from quant_agent_lab.core.config import PipelineConfig
from quant_agent_lab.core.events import run_id
from quant_agent_lab.core.schemas import AdvisoryResult
from quant_agent_lab.data.audit import AuditRecord, append_jsonl, stable_hash, write_json
from quant_agent_lab.data.csv_loader import load_csv_market_snapshot
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.data.validation import validate_market_snapshot
from quant_agent_lab.decision.committee import build_recommendation_draft
from quant_agent_lab.reports.daily import render_daily_report
from quant_agent_lab.risk.gate import RiskGate
from quant_agent_lab.strategy.signals import build_signal_bundle


def _load_market(config: PipelineConfig):
    if config.data_source == "mock":
        return load_mock_market_snapshot(symbol=config.symbol, as_of=config.as_of_utc)
    if config.csv is None:
        raise ValueError("csv config is required when data_source='csv'")
    return load_csv_market_snapshot(
        symbol=config.symbol,
        as_of=config.as_of_utc,
        bars_1h_csv=config.csv.bars_1h_csv,
        bars_1d_csv=config.csv.bars_1d_csv,
        portfolio_json=config.csv.portfolio_json,
    )
    raise ValueError(f"unsupported data source: {config.data_source}")


def run_daily_pipeline(
    symbol: str = "BTC-USDT",
    output_dir: Path | None = None,
    config: PipelineConfig | None = None,
) -> AdvisoryResult:
    config = config or PipelineConfig(symbol=symbol, output_dir=output_dir or Path("artifacts/reports"))
    market = _load_market(config)
    current_run_id = run_id(config.symbol, market.as_of)
    data_validation = validate_market_snapshot(market)
    signals = build_signal_bundle(market)
    opinions = [agent.run(market, signals) for agent in default_mock_agents()]
    recommendation = build_recommendation_draft(signals, data_validation, opinions)
    risk_decision = RiskGate(
        max_position_pct=config.risk.max_position_pct,
        max_loss_budget_pct=config.risk.max_loss_budget_pct,
        max_existing_position_pct=config.risk.max_existing_position_pct,
        min_cash_pct=config.risk.min_cash_pct,
        max_hourly_return_vol=config.risk.max_hourly_return_vol,
    ).evaluate(recommendation, market=market, signals=signals)
    report = render_daily_report(
        run_id=current_run_id,
        signals=signals,
        data_validation=data_validation,
        opinions=opinions,
        recommendation=recommendation,
        risk_decision=risk_decision,
    )
    result = AdvisoryResult(
        run_id=current_run_id,
        symbol=symbol,
        as_of=market.as_of,
        market=market,
        data_validation=data_validation,
        signals=signals,
        agent_opinions=opinions,
        recommendation=recommendation,
        risk_decision=risk_decision,
        report_markdown=report,
    )
    target_dir = output_dir or config.output_dir
    if target_dir is not None:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / f"{current_run_id}.md").write_text(report, encoding="utf-8")
        result_payload = result.model_dump(mode="json")
        write_json(target_dir / f"{current_run_id}.json", result_payload)
        audit_record = AuditRecord(
            run_id=current_run_id,
            input_hash=stable_hash(
                {
                    "market": market.model_dump(mode="json"),
                    "config": config.model_dump(mode="json"),
                }
            ),
            output_hash=stable_hash(result_payload),
            validation_result=data_validation.status.value,
        )
        write_json(target_dir / f"{current_run_id}.audit.json", audit_record.model_dump(mode="json"))
        append_jsonl(target_dir / "audit-log.jsonl", audit_record.model_dump(mode="json"))
    return result
