from __future__ import annotations

import json

from quant_agent_lab.data.connectors import fetch_binance_klines, write_binance_csv_dataset


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def _kline(open_time_ms: int, close: str = "64050"):
    return [
        open_time_ms,
        "64000",
        "64100",
        "63900",
        close,
        "123",
        open_time_ms + 3_599_999,
        "0",
        10,
        "0",
        "0",
        "0",
    ]


def test_fetch_binance_klines_maps_public_response(monkeypatch) -> None:
    captured_urls: list[str] = []

    def fake_urlopen(request, timeout):
        captured_urls.append(request.full_url)
        return _FakeResponse([_kline(1777417200000)])

    monkeypatch.setattr("quant_agent_lab.data.connectors.urlopen", fake_urlopen)

    bars = fetch_binance_klines(symbol="BTC-USDT", timeframe="1h", limit=1)

    assert "symbol=BTCUSDT" in captured_urls[0]
    assert "interval=1h" in captured_urls[0]
    assert bars[0].symbol == "BTC-USDT"
    assert bars[0].source == "binance"
    assert bars[0].close == 64050
    assert bars[0].ts.isoformat() == "2026-04-28T23:00:00+00:00"


def test_write_binance_csv_dataset_writes_metadata(monkeypatch, tmp_path) -> None:
    def fake_urlopen(request, timeout):
        if "interval=1h" in request.full_url:
            return _FakeResponse([_kline(1777413600000), _kline(1777417200000)])
        return _FakeResponse([_kline(1777334400000), _kline(1777420800000)])

    monkeypatch.setattr("quant_agent_lab.data.connectors.urlopen", fake_urlopen)

    output_dir = write_binance_csv_dataset(tmp_path / "binance", hourly_limit=2, daily_limit=2)

    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["exchange"] == "binance"
    assert metadata["as_of"] == "2026-04-28T23:00:00+00:00"
    assert (output_dir / "bars_1h.csv").exists()
    assert (output_dir / "bars_1d.csv").exists()
    assert (output_dir / "portfolio.json").exists()
