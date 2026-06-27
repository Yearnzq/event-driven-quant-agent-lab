from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from quant_agent_lab.agents.base import TypedAgent
from quant_agent_lab.agents.mock import default_mock_agents
from quant_agent_lab.core.config import PipelineConfig
from quant_agent_lab.core.events import evidence_id, run_id
from quant_agent_lab.core.schemas import (
    A2AAgentCard,
    A2ATraceRecord,
    Action,
    AdvisoryResult,
    AgentOpinion,
    Bar,
    DataQuality,
    DataValidationResult,
    GateStatus,
    MarketSnapshot,
    ModelCallAuditRecord,
    PortfolioSnapshot,
)
from quant_agent_lab.data.audit import (
    AuditRecord,
    append_jsonl,
    stable_hash,
    write_artifact_catalog,
    write_json,
    write_run_manifest,
)
from quant_agent_lab.data.csv_loader import load_csv_market_snapshot
from quant_agent_lab.data.mock import load_mock_market_snapshot
from quant_agent_lab.data.validation import validate_market_snapshot
from quant_agent_lab.decision.committee import build_recommendation_draft
from quant_agent_lab.reports.daily import render_daily_report
from quant_agent_lab.risk.gate import RiskGate
from quant_agent_lab.strategy.signals import build_signal_bundle


def load_market(config: PipelineConfig):
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


def _fallback_market_snapshot(config: PipelineConfig) -> MarketSnapshot:
    as_of = config.as_of_utc
    bars_1h = [
        Bar(
            symbol=config.symbol,
            timeframe="1h",
            ts=as_of.replace(minute=0, second=0, microsecond=0) - timedelta(hours=24 - index),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=0.0,
            source="data_loader_failure",
            evidence_id=evidence_id("fallback", config.symbol, "1h", index),
        )
        for index in range(25)
    ]
    bars_1d = [
        Bar(
            symbol=config.symbol,
            timeframe="1d",
            ts=as_of.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=29 - index),
            open=100.0,
            high=100.0,
            low=100.0,
            close=100.0,
            volume=0.0,
            source="data_loader_failure",
            evidence_id=evidence_id("fallback", config.symbol, "1d", index),
        )
        for index in range(30)
    ]
    return MarketSnapshot(
        symbol=config.symbol,
        as_of=as_of,
        bars_1h=bars_1h,
        bars_1d=bars_1d,
        portfolio=PortfolioSnapshot(
            as_of=as_of,
            equity=1.0,
            cash=1.0,
            positions={config.symbol: 0.0},
            source="data_loader_failure",
            evidence_id=evidence_id("fallback", "portfolio", config.symbol, as_of.isoformat()),
        ),
    )


def _model_metadata(
    config: PipelineConfig,
    *,
    model_call_audits: list[ModelCallAuditRecord],
    a2a_agent_cards: list[A2AAgentCard],
) -> tuple[str, str, str]:
    if model_call_audits:
        audit = model_call_audits[0]
        return audit.provider, audit.model_name, audit.prompt_version
    if a2a_agent_cards:
        return (
            "a2a",
            ",".join(sorted(card.agent_id for card in a2a_agent_cards)),
            "phase9.agent_card.v1",
        )
    if config.model_provider.provider != "fake":
        return (
            config.model_provider.provider,
            config.model_provider.model_name,
            config.model_provider.prompt_registry_version,
        )
    return "mock", "mock-agents", "mock.v1"


def _run_agents_safely(market, signals, agents: list[TypedAgent]) -> list[AgentOpinion]:
    opinions: list[AgentOpinion] = []
    for agent in agents:
        agent_name = getattr(agent, "name", agent.__class__.__name__)
        try:
            opinions.append(agent.run(market, signals))
        except Exception as exc:
            error_summary = f"{type(exc).__name__}: redacted"
            opinions.append(
                AgentOpinion(
                    agent_name=agent_name,
                    status=GateStatus.FAIL,
                    action_bias=Action.INSUFFICIENT_EVIDENCE,
                    confidence=0.0,
                    rationale=[f"{agent_name} failed; degraded to insufficient evidence"],
                    risk_flags=[f"agent_failed:{agent_name}"],
                    evidence_ids=signals.evidence_ids,
                    error_message=error_summary,
                    generated_at=market.as_of,
                )
            )
    return opinions


def _collect_model_call_audits(agents: list[TypedAgent]) -> list[ModelCallAuditRecord]:
    audits: list[ModelCallAuditRecord] = []
    for agent in agents:
        audit = getattr(agent, "last_audit_record", None)
        if isinstance(audit, ModelCallAuditRecord):
            audits.append(audit)
    return audits


def _collect_a2a_agent_cards(agents: list[TypedAgent]) -> list[A2AAgentCard]:
    cards: list[A2AAgentCard] = []
    for agent in agents:
        card = getattr(agent, "agent_card", None)
        if isinstance(card, A2AAgentCard):
            cards.append(card)
    return cards


def _collect_a2a_trace_records(agents: list[TypedAgent]) -> list[A2ATraceRecord]:
    traces: list[A2ATraceRecord] = []
    for agent in agents:
        trace = getattr(agent, "last_a2a_trace_record", None)
        if isinstance(trace, A2ATraceRecord):
            traces.append(trace)
    return traces


def run_daily_pipeline(
    symbol: str = "BTC-USDT",
    output_dir: Path | None = None,
    config: PipelineConfig | None = None,
    agents: list[TypedAgent] | None = None,
) -> AdvisoryResult:
    config = config or PipelineConfig(symbol=symbol, output_dir=output_dir or Path("artifacts/reports"))
    load_error: Exception | None = None
    try:
        market = load_market(config)
        data_validation = validate_market_snapshot(market)
        signals = build_signal_bundle(market)
    except Exception as exc:  # noqa: BLE001 - malformed data must still produce audit artifacts.
        load_error = exc
        market = _fallback_market_snapshot(config)
        data_validation = DataValidationResult(
            status=GateStatus.FAIL,
            data_quality=DataQuality.FAIL,
            reasons=[f"market data loading failed: {type(exc).__name__}: redacted"],
            evidence_ids=market.evidence_ids,
        )
        signals = build_signal_bundle(market)
    current_run_id = run_id(config.symbol, market.as_of)
    agents_to_run = [] if load_error is not None or data_validation.status == GateStatus.FAIL else agents or default_mock_agents()
    opinions = _run_agents_safely(market, signals, agents_to_run)
    model_call_audits = _collect_model_call_audits(agents_to_run)
    a2a_agent_cards = _collect_a2a_agent_cards(agents_to_run)
    a2a_trace_records = _collect_a2a_trace_records(agents_to_run)
    model_provider, model_name, prompt_version = _model_metadata(
        config,
        model_call_audits=model_call_audits,
        a2a_agent_cards=a2a_agent_cards,
    )
    recommendation = build_recommendation_draft(signals, data_validation, opinions)
    risk_decision = RiskGate(
        max_position_pct=config.risk.max_position_pct,
        max_loss_budget_pct=config.risk.max_loss_budget_pct,
        max_existing_position_pct=config.risk.max_existing_position_pct,
        min_cash_pct=config.risk.min_cash_pct,
        max_hourly_return_vol=config.risk.max_hourly_return_vol,
        max_recent_drawdown_pct=config.risk.max_recent_drawdown_pct,
        max_downside_volatility=config.risk.max_downside_volatility,
        max_single_hour_loss_pct=config.risk.max_single_hour_loss_pct,
        max_portfolio_risk_budget_pct=config.risk.max_portfolio_risk_budget_pct,
    ).evaluate(recommendation, market=market, signals=signals)
    report = render_daily_report(
        run_id=current_run_id,
        signals=signals,
        data_validation=data_validation,
        opinions=opinions,
        recommendation=recommendation,
        risk_decision=risk_decision,
        model_call_audits=model_call_audits,
        a2a_trace_records=a2a_trace_records,
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
        model_call_audits=model_call_audits,
        a2a_agent_cards=a2a_agent_cards,
        a2a_trace_records=a2a_trace_records,
    )
    target_dir = output_dir or config.output_dir
    if target_dir is not None:
        target_dir.mkdir(parents=True, exist_ok=True)
        report_path = target_dir / f"{current_run_id}.md"
        result_path = target_dir / f"{current_run_id}.json"
        audit_path = target_dir / f"{current_run_id}.audit.json"
        audit_log_path = target_dir / "audit-log.jsonl"
        model_call_audit_path = target_dir / "model-call-audit.json"
        a2a_agent_card_path = target_dir / "a2a-agent-card.json"
        a2a_trace_path = target_dir / "a2a-trace.json"

        report_path.write_text(report, encoding="utf-8")
        result_payload = result.model_dump(mode="json")
        write_json(result_path, result_payload)
        hash_config_payload = config.model_dump(mode="json", exclude={"output_dir"})
        input_hash = stable_hash(
            {
                "market": market.model_dump(mode="json"),
                "config": hash_config_payload,
            }
        )
        output_hash = stable_hash(result_payload)
        config_hash = stable_hash(hash_config_payload)
        audit_record = AuditRecord(
            run_id=current_run_id,
            created_at=market.as_of,
            input_hash=input_hash,
            output_hash=output_hash,
            model_provider=model_provider,
            model_name=model_name,
            prompt_version=prompt_version,
            validation_result=data_validation.status.value,
        )
        write_json(audit_path, audit_record.model_dump(mode="json"))
        append_jsonl(audit_log_path, audit_record.model_dump(mode="json"))
        artifacts = [
            ("report_markdown", report_path),
            ("result_json", result_path),
            ("audit_json", audit_path),
            ("audit_log", audit_log_path),
        ]
        if model_call_audits:
            write_json(
                model_call_audit_path,
                [audit.model_dump(mode="json") for audit in model_call_audits],
            )
            artifacts.append(("model_call_audit", model_call_audit_path))
        if a2a_agent_cards:
            write_json(
                a2a_agent_card_path,
                [card.model_dump(mode="json") for card in a2a_agent_cards],
            )
            artifacts.append(("a2a_agent_card", a2a_agent_card_path))
        if a2a_trace_records:
            write_json(
                a2a_trace_path,
                [trace.model_dump(mode="json") for trace in a2a_trace_records],
            )
            artifacts.append(("a2a_trace", a2a_trace_path))
        catalog_path = write_artifact_catalog(
            target_dir,
            run_id=current_run_id,
            artifacts=artifacts,
            created_at=market.as_of,
        )
        write_run_manifest(
            target_dir,
            run_id=current_run_id,
            symbol=config.symbol,
            as_of=market.as_of,
            input_hash=input_hash,
            output_hash=output_hash,
            config_hash=config_hash,
            validation_result=data_validation.status.value,
            artifact_catalog_path=catalog_path,
            created_at=market.as_of,
            model_provider=model_provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
    return result
