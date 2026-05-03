from __future__ import annotations

import json
from datetime import datetime, timezone

from quant_agent_lab.app.cli import main
from quant_agent_lab.data.text_cleaning import (
    clean_news_jsonl,
    clean_text_evidence,
    content_hash,
    extract_entities,
    summarize_text,
)


def test_summarize_text_strips_html_and_truncates() -> None:
    summary = summarize_text("<p>BTC rallied after the FOMC update.</p> More text here.", max_chars=28)

    assert "<p>" not in summary
    assert summary.endswith("...")


def test_extract_entities_is_deterministic() -> None:
    entities = extract_entities("BTC liquidity rose while the Fed and ETF desks watched.")

    assert entities == ["BTC", "ETF", "FED"]


def test_clean_text_evidence_keeps_hash_not_raw_body() -> None:
    cleaned = clean_text_evidence(
        source="unit-test",
        published_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
        title="BTC liquidity improves",
        raw_text="BTC market depth improved after ETF inflows.",
        url="https://example.com/story",
    )

    assert cleaned.evidence_id.startswith("text:unit-test:")
    assert cleaned.content_hash == content_hash("BTC liquidity improves\nBTC market depth improved after ETF inflows.")
    assert cleaned.entities == ["BTC", "ETF"]
    assert "market depth" in cleaned.summary


def test_clean_news_jsonl_writes_schema_safe_rows(tmp_path) -> None:
    raw = tmp_path / "raw.jsonl"
    cleaned = tmp_path / "cleaned.jsonl"
    raw.write_text(
        json.dumps(
            {
                "source": "example",
                "published_at": "2026-05-03T00:00:00Z",
                "title": "BTC update",
                "content": "<article>BTC and USDT liquidity improved.</article>",
                "url": "https://example.com/a",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    clean_news_jsonl(raw, cleaned)

    row = json.loads(cleaned.read_text(encoding="utf-8"))
    assert row["source"] == "example"
    assert row["entities"] == ["BTC", "USDT"]
    assert "article" not in row["summary"]
    assert "content" not in row


def test_cli_clean_news_jsonl(tmp_path) -> None:
    raw = tmp_path / "raw.jsonl"
    output = tmp_path / "cleaned.jsonl"
    raw.write_text(
        json.dumps(
            {
                "published_at": "2026-05-03T00:00:00Z",
                "title": "FOMC watch",
                "text": "BTC traders watched the FOMC calendar.",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["--clean-news-jsonl", str(raw), "--cleaned-news-output", str(output)])

    assert exit_code == 0
    assert output.exists()
