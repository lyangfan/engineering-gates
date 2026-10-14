"""Deterministic directory snapshots used as engineering evidence."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from digest_table import sha256_file, write_json_no_clobber


def iter_files(root: Path, exclude: Iterable[str] = ()) -> list[Path]:
    root = root.resolve()
    excluded = set(exclude)
    result: list[Path] = []
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(
            d for d in dirs
            if d not in excluded and not (current_path / d).is_symlink()
        )
        for name in sorted(files):
            path = current_path / name
            if path.is_symlink():
                continue
            result.append(path)
    return sorted(result)


def snapshot(root: Path, exclude: Iterable[str] = ()) -> dict:
    root = root.resolve()
    rows = []
    for path in iter_files(root, exclude):
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        })
    return {"schema": "agent-gates.eng-snapshot/v1", "root": str(root), "files": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("-o", "--out", type=Path)
    parser.add_argument("--exclude", action="append", default=[])
    args = parser.parse_args()
    value = snapshot(args.root, args.exclude)
    if args.out:
        write_json_no_clobber(args.out, value)
        print(args.out)
    else:
        print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
