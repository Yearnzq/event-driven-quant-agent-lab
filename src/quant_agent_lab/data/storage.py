from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def write_audit_record(path: Path, record: BaseModel | dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = record.model_dump(mode="json") if isinstance(record, BaseModel) else record
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
