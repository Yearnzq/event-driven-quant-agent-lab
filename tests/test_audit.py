from __future__ import annotations

from quant_agent_lab.data.audit import stable_hash


def test_stable_hash_is_order_independent_for_dicts() -> None:
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
