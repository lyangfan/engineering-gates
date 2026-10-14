"""Small, dependency-free identity helpers for engineering-gates."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Iterable


HASH_HEX_LENGTH = 64


class IdentityError(ValueError):
    """Raised when an artifact identity cannot be established."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise IdentityError("file does not exist: %s" % path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != HASH_HEX_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def require_sha256(value: Any, label: str = "sha256") -> str:
    if not is_sha256(value):
        raise IdentityError("%s must be 64 hexadecimal characters" % label)
    return str(value).lower()


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise IdentityError("JSON file does not exist: %s" % path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IdentityError("cannot read JSON %s: %s" % (path, exc)) from exc
    if not isinstance(value, dict):
        raise IdentityError("JSON root must be an object: %s" % path)
    return value


def write_json_no_clobber(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise IdentityError("refusing to overwrite existing path: %s" % path)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with path.open("x", encoding="utf-8") as handle:
        handle.write(payload)


def git_head(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def git_path_status(root: Path, relative_path: str) -> str:
    """Return porcelain status for one path, or an empty string when clean."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain", "--", relative_path],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise IdentityError("cannot inspect git status for %s: %s" % (relative_path, exc)) from exc
    return result.stdout


def git_file_commit(root: Path, relative_path: str) -> str | None:
    """Return the commit containing the current HEAD version of a file."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%H", "HEAD", "--", relative_path],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def canonical_path(path: Path) -> Path:
    return Path(os.path.realpath(path))


def hash_table(paths: Iterable[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.append({"path": str(path), "sha256": sha256_file(path)})
    return rows
