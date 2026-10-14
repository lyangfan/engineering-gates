"""Coverage checks for the A/B requirement catalogue."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


class CoverageError(ValueError):
    pass


def expected_ids(gate: str) -> set[str]:
    if gate == "A":
        return {f"A{i}" for i in range(1, 10)}
    if gate == "B":
        return {f"B{i}" for i in range(1, 8)}
    raise CoverageError("gate must be A or B")


def coverage(requirements: list[dict[str, Any]], gate: str) -> dict[str, Any]:
    ids = [item.get("id") for item in requirements]
    if any(not isinstance(item, str) for item in ids):
        raise CoverageError("every requirement needs a string id")
    duplicate = sorted({item for item in ids if ids.count(item) > 1})
    actual = set(ids)
    expected = expected_ids(gate)
    return {
        "gate": gate,
        "expected": sorted(expected),
        "actual": sorted(actual),
        "missing": sorted(expected - actual),
        "extra": sorted(actual - expected),
        "duplicates": duplicate,
        "complete": not (expected - actual or actual - expected or duplicate),
    }


def assert_complete(requirements: list[dict[str, Any]], gate: str) -> None:
    result = coverage(requirements, gate)
    if not result["complete"]:
        raise CoverageError(json.dumps(result, ensure_ascii=False, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    value = json.loads(args.contract.read_text(encoding="utf-8"))
    result = coverage(value.get("requirements", []), value.get("gate", ""))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
