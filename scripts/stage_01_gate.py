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
from quant_agent_lab.core.config import CsvDataConfig, PipelineConfig  # noqa: E402
from quant_agent_lab.data.connectors import write_binance_csv_dataset  # noqa: E402
from quant_agent_lab.data.csv_loader import load_bars_csv  # noqa: E402
from quant_agent_lab.data.importers import write_sample_csv_dataset  # noqa: E402
from quant_agent_lab.data.text_cleaning import clean_news_jsonl  # noqa: E402
from quant_agent_lab.research.evaluation import (  # noqa: E402
    evaluate_ma_crossover,
    render_signal_evaluation_markdown,
)


DEFAULT_OUTPUT_DIR = Path("/tmp/qal-stage-01-gate")


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_artifact_text(path: Path) -> str:
    if path.suffix.lower() not in {".md", ".json", ".jsonl"}:
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def assert_report_boundaries(report_dir: Path) -> None:
    _assert(report_dir.exists(), "reports dir missing")
    files = [path for path in report_dir.rglob("*") if path.is_file()]
    _assert(files, "no report artifacts generated")
    text_blob = "\n".join(_read_artifact_text(path) for path in files)
    lower = text_blob.lower()
    _assert("advisory" in lower or "辅助决策" in text_blob, "advisory-only wording missing")
    _assert("order_allowed" in lower or "order allowed" in lower, "order_allowed field missing")
    _assert('"order_allowed": true' not in lower, "order_allowed=true is forbidden in phase 1")
    _assert("auto trade" not in lower, "auto trade wording should not appear as allowed behavior")


def assert_cleaned_news_boundaries(path: Path) -> None:
    _assert(path.exists(), "cleaned news output missing")
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    _assert(lines, "cleaned output empty")
    for item in lines:
        _assert("content" not in item, "raw content field leaked")
        _assert("raw_content" not in item, "raw_content field leaked")
        serialized = json.dumps(item, ensure_ascii=False)
        _assert("<p>" not in serialized and "</p>" not in serialized, "HTML leaked")
        _assert("published_at" in item, "published_at missing")
        _assert("source" in item, "source missing")


def run_offline_gate(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_dir = output_dir / "sample"
    report_dir = output_dir / "reports"
    research_dir = output_dir / "research"
    evidence_dir = output_dir / "evidence"

    write_sample_csv_dataset(sample_dir, symbol="BTC-USDT")
    csv_config = CsvDataConfig(
        bars_1h_csv=sample_dir / "bars_1h.csv",
        bars_1d_csv=sample_dir / "bars_1d.csv",
        portfolio_json=sample_dir / "portfolio.json",
    )

    mock_result = run_daily_pipeline(output_dir=report_dir / "mock")
    csv_result = run_daily_pipeline(
        config=PipelineConfig(
            data_source="csv",
            csv=csv_config,
            output_dir=report_dir / "csv",
        )
    )
    _assert(mock_result.risk_decision.order_allowed is False, "mock run allowed orders")
    _assert(csv_result.risk_decision.order_allowed is False, "csv run allowed orders")
    assert_report_boundaries(report_dir)

    bars_1d = load_bars_csv(csv_config.bars_1d_csv, symbol="BTC-USDT", timeframe="1d")
    summary = evaluate_ma_crossover(bars_1d)
    research_dir.mkdir(parents=True, exist_ok=True)
    (research_dir / f"{summary.strategy_name}.md").write_text(
        render_signal_evaluation_markdown(summary),
        encoding="utf-8",
    )
    _write_json(research_dir / f"{summary.strategy_name}.json", summary.model_dump(mode="json"))
    _assert((research_dir / f"{summary.strategy_name}.md").exists(), "research markdown missing")
    _assert((research_dir / f"{summary.strategy_name}.json").exists(), "research json missing")

    raw_news = evidence_dir / "raw_news.jsonl"
    cleaned_news = evidence_dir / "cleaned_news.jsonl"
    raw_news.parent.mkdir(parents=True, exist_ok=True)
    raw_news.write_text(
        json.dumps(
            {
                "source": "manual",
                "published_at": "2026-05-03T00:00:00Z",
                "title": "BTC liquidity update",
                "content": "<p>BTC and USDT liquidity improved while ETF flows stayed active.</p>",
                "url": "https://example.com",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    clean_news_jsonl(raw_news, cleaned_news)
    assert_cleaned_news_boundaries(cleaned_news)

    print(f"STAGE_01_OFFLINE_GATE=PASS output_dir={output_dir}")


def run_binance_best_effort(output_dir: Path) -> None:
    binance_dir = output_dir / "binance"
    try:
        data_dir = write_binance_csv_dataset(binance_dir / "data", symbol="BTC-USDT", allow_network=True)
        csv_config = CsvDataConfig(
            bars_1h_csv=data_dir / "bars_1h.csv",
            bars_1d_csv=data_dir / "bars_1d.csv",
            portfolio_json=data_dir / "portfolio.json",
        )
        metadata = json.loads((data_dir / "metadata.json").read_text(encoding="utf-8"))
        result = run_daily_pipeline(
            config=PipelineConfig(
                data_source="csv",
                as_of=metadata["as_of"],
                csv=csv_config,
                output_dir=binance_dir / "reports",
            )
        )
        _assert(result.risk_decision.order_allowed is False, "binance run allowed orders")
        print(f"BINANCE_CHECK=PASS output_dir={binance_dir}")
    except Exception as exc:  # noqa: BLE001 - best-effort network gate must not fail stage 1.
        print(f"BINANCE_CHECK=WAIVED_NETWORK_FAILURE reason={type(exc).__name__}: {exc}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 offline engineering gate checks.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--try-binance", action="store_true", help="Run Binance public data best-effort check.")
    args = parser.parse_args(argv)

    print(f"python={sys.version.split()[0]}")
    run_offline_gate(args.output_dir)
    if args.try_binance:
        run_binance_best_effort(args.output_dir)
    else:
        print("BINANCE_CHECK=SKIPPED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
