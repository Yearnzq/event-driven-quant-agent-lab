from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from quant_agent_lab.core.events import evidence_id
from quant_agent_lab.core.schemas import CleanedTextEvidence


DEFAULT_MARKET_ENTITIES = (
    "BTC",
    "ETH",
    "USDT",
    "USD",
    "CPI",
    "FOMC",
    "FED",
    "ETF",
    "BINANCE",
)


def _parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def content_hash(value: str) -> str:
    return hashlib.sha256(_canonical_text(value).encode("utf-8")).hexdigest()


def extract_entities(text: str, *, known_entities: tuple[str, ...] = DEFAULT_MARKET_ENTITIES) -> list[str]:
    normalized = text.upper()
    found = [entity for entity in known_entities if re.search(rf"\b{re.escape(entity)}\b", normalized)]
    return sorted(set(found))


def summarize_text(raw_text: str, *, max_chars: int = 500) -> str:
    cleaned = _canonical_text(raw_text)
    if len(cleaned) <= max_chars:
        return cleaned
    boundary = cleaned.rfind(".", 0, max_chars)
    if boundary < max_chars // 2:
        boundary = max_chars
    return cleaned[:boundary].rstrip(" ,.;:") + "..."


def clean_text_evidence(
    *,
    source: str,
    published_at: datetime,
    title: str,
    raw_text: str,
    url: str | None = None,
    known_entities: tuple[str, ...] = DEFAULT_MARKET_ENTITIES,
    max_summary_chars: int = 500,
) -> CleanedTextEvidence:
    cleaned_title = _canonical_text(title)
    summary = summarize_text(raw_text, max_chars=max_summary_chars)
    combined = f"{cleaned_title} {summary}"
    entities = extract_entities(combined, known_entities=known_entities)
    relevance = min(1.0, len(entities) / 3)
    digest = content_hash(f"{cleaned_title}\n{raw_text}")
    return CleanedTextEvidence(
        evidence_id=evidence_id("text", source, digest[:12]),
        source=source,
        published_at=published_at,
        title=cleaned_title,
        summary=summary,
        entities=entities,
        market_relevance=round(relevance, 4),
        url=url,
        content_hash=digest,
    )


def _row_value(row: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value)
    return None


def clean_news_jsonl(input_path: Path, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as input_handle:
        with output_path.open("w", encoding="utf-8") as output_handle:
            for line_number, line in enumerate(input_handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                published_at = _row_value(row, "published_at", "publishedAt", "time", "ts")
                title = _row_value(row, "title", "headline")
                raw_text = _row_value(row, "content", "body", "text", "summary")
                if not published_at or not title or not raw_text:
                    raise ValueError(f"line {line_number} missing published_at, title, or text content")
                cleaned = clean_text_evidence(
                    source=str(row.get("source") or "news-jsonl"),
                    published_at=_parse_dt(published_at),
                    title=title,
                    raw_text=raw_text,
                    url=_row_value(row, "url", "link"),
                )
                output_handle.write(json.dumps(cleaned.model_dump(mode="json"), ensure_ascii=False) + "\n")
    return output_path
