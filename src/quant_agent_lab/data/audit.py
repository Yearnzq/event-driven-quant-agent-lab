from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0))
    schema_version: str = "phase1.advisory.v1"
    input_hash: str
    output_hash: str
    model_provider: str = "mock"
    model_name: str = "mock-agents"
    prompt_version: str = "mock.v1"
    validation_result: str


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    return path


def append_jsonl(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))
        handle.write("\n")
    return path
