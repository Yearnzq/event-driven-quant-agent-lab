from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RiskConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_position_pct: float = Field(default=0.10, ge=0, le=1)
    max_loss_budget_pct: float = Field(default=0.02, ge=0, le=1)
    max_existing_position_pct: float = Field(default=0.25, ge=0, le=1)
    min_cash_pct: float = Field(default=0.05, ge=0, le=1)
    max_hourly_return_vol: float = Field(default=0.03, ge=0, le=1)
    max_recent_drawdown_pct: float = Field(default=0.12, ge=0, le=1)
    max_downside_volatility: float = Field(default=0.025, ge=0, le=1)
    max_single_hour_loss_pct: float = Field(default=0.08, ge=0, le=1)
    max_portfolio_risk_budget_pct: float = Field(default=0.01, ge=0, le=1)


class CsvDataConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    bars_1h_csv: Path
    bars_1d_csv: Path
    portfolio_json: Path


class PipelineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str = "BTC-USDT"
    as_of: datetime = Field(default_factory=lambda: datetime(2026, 4, 29, tzinfo=timezone.utc))
    data_source: Literal["mock", "csv"] = "mock"
    csv: CsvDataConfig | None = None
    output_dir: Path = Path("artifacts/reports")
    risk: RiskConfig = Field(default_factory=RiskConfig)

    @property
    def as_of_utc(self) -> datetime:
        if self.as_of.tzinfo is None:
            return self.as_of.replace(tzinfo=timezone.utc)
        return self.as_of.astimezone(timezone.utc)
