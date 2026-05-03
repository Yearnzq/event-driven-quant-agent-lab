from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from quant_agent_lab.core.schemas import Bar, MarketSnapshot
from quant_agent_lab.data.mock import load_mock_market_snapshot


FIELD_ALIASES = {
    "ts": ("ts", "timestamp", "time", "datetime", "date", "open_time"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "vol", "base_volume", "amount"),
}


def _first_present(row: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    raise ValueError(f"missing required column; expected one of: {', '.join(names)}")


def _normalize_ts(value: str) -> str:
    stripped = value.strip()
    if stripped.isdigit():
        number = int(stripped)
        divisor = 1000 if number > 10_000_000_000 else 1
        return datetime.fromtimestamp(number / divisor, tz=timezone.utc).isoformat()
    return stripped.replace("Z", "+00:00")


def _normalize_row(row: dict[str, str], *, symbol: str, source: str) -> dict[str, str]:
    normalized = {
        "symbol": row.get("symbol") or row.get("instId") or row.get("pair") or symbol,
        "ts": _normalize_ts(_first_present(row, FIELD_ALIASES["ts"])),
        "open": _first_present(row, FIELD_ALIASES["open"]),
        "high": _first_present(row, FIELD_ALIASES["high"]),
        "low": _first_present(row, FIELD_ALIASES["low"]),
        "close": _first_present(row, FIELD_ALIASES["close"]),
        "volume": row.get("volume")
        or row.get("vol")
        or row.get("base_volume")
        or row.get("amount")
        or "0",
        "source": row.get("source") or source,
    }
    return {key: str(value) for key, value in normalized.items()}


def normalize_ohlcv_csv(
    input_path: Path,
    output_path: Path,
    *,
    symbol: str,
    source: str,
) -> Path:
    """Normalize common exchange OHLCV CSV exports into the project CSV schema."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8", newline="") as source_handle:
        reader = csv.DictReader(source_handle)
        with output_path.open("w", encoding="utf-8", newline="") as output_handle:
            fieldnames = ["symbol", "ts", "open", "high", "low", "close", "volume", "source"]
            writer = csv.DictWriter(output_handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in reader:
                writer.writerow(_normalize_row(row, symbol=symbol, source=source))
    return output_path


def write_bars_csv(path: Path, bars: list[Bar]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "symbol",
            "ts",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "source",
            "evidence_id",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "symbol": bar.symbol,
                    "ts": bar.ts.isoformat(),
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "source": bar.source,
                    "evidence_id": bar.evidence_id,
                }
            )
    return path


def write_portfolio_json(path: Path, snapshot: MarketSnapshot) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = snapshot.portfolio.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_sample_csv_dataset(
    output_dir: Path,
    *,
    symbol: str = "BTC-USDT",
    snapshot: MarketSnapshot | None = None,
) -> Path:
    snapshot = snapshot or load_mock_market_snapshot(symbol=symbol)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_bars_csv(output_dir / "bars_1h.csv", snapshot.bars_1h)
    write_bars_csv(output_dir / "bars_1d.csv", snapshot.bars_1d)
    write_portfolio_json(output_dir / "portfolio.json", snapshot)
    return output_dir
