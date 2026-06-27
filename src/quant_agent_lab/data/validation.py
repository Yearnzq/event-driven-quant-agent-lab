from __future__ import annotations

from datetime import timedelta

from quant_agent_lab.core.schemas import DataQuality, DataValidationResult, GateStatus, MarketSnapshot


def _has_duplicate_timestamps(timestamps: list[object]) -> bool:
    return len(set(timestamps)) != len(timestamps)


def _has_gap(timestamps: list[object], expected_delta: timedelta) -> bool:
    if len(timestamps) < 2:
        return False
    return any((right - left) != expected_delta for left, right in zip(timestamps, timestamps[1:]))


def validate_market_snapshot(snapshot: MarketSnapshot) -> DataValidationResult:
    reasons: list[str] = []
    hourly_timestamps = [bar.ts for bar in snapshot.bars_1h]
    daily_timestamps = [bar.ts for bar in snapshot.bars_1d]

    if snapshot.bars_1h[-1].ts < snapshot.as_of - timedelta(hours=2):
        reasons.append("latest 1h bar is stale")
    if snapshot.bars_1d[-1].ts < snapshot.as_of - timedelta(days=2):
        reasons.append("latest 1d bar is stale")
    if len(snapshot.bars_1h) < 24:
        reasons.append("fewer than 24 hourly bars")
    if len(snapshot.bars_1d) < 30:
        reasons.append("fewer than 30 daily bars")
    if snapshot.portfolio.as_of != snapshot.as_of:
        reasons.append("portfolio snapshot timestamp does not match market snapshot")

    expected_1h = sorted(hourly_timestamps)
    expected_1d = sorted(daily_timestamps)
    if expected_1h != hourly_timestamps:
        reasons.append("hourly bars are not sorted")
    if expected_1d != daily_timestamps:
        reasons.append("daily bars are not sorted")
    if _has_duplicate_timestamps(hourly_timestamps):
        reasons.append("hourly bars contain duplicate timestamps")
    if _has_duplicate_timestamps(daily_timestamps):
        reasons.append("daily bars contain duplicate timestamps")
    if expected_1h == hourly_timestamps and _has_gap(hourly_timestamps, timedelta(hours=1)):
        reasons.append("hourly bars contain gaps")
    if expected_1d == daily_timestamps and _has_gap(daily_timestamps, timedelta(days=1)):
        reasons.append("daily bars contain gaps")
    if any(bar.symbol != snapshot.symbol for bar in snapshot.bars_1h + snapshot.bars_1d):
        reasons.append("bar symbol does not match market snapshot symbol")

    status = GateStatus.FAIL if reasons else GateStatus.PASS
    quality = DataQuality.FAIL if reasons else DataQuality.PASS
    return DataValidationResult(
        status=status,
        data_quality=quality,
        reasons=reasons,
        evidence_ids=snapshot.evidence_ids,
    )
