"""Shared parsing, path rules, and JSON output for EG-S1."""

import hashlib
import json
import os
import re
import shlex
import stat
import sys

KINDS = ("spec-freeze", "tests-freeze", "candidate", "review", "record")
SPEC_RE = re.compile(r"^[A-Za-z0-9._-]+$")
IDENTITY_ENV = (
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
)
OVERRIDE_KEYS = (
    "author.name",
    "author.email",
    "committer.name",
    "committer.email",
)
DEFAULT_TIMEOUT = 300


def parse_timeout(raw):
    """Return ``(seconds, error)``. Unset means the default 300s."""
    if raw is None:
        return DEFAULT_TIMEOUT, None
    if re.fullmatch(r"[0-9]+", raw):
        value = int(raw)
        if 1 <= value <= DEFAULT_TIMEOUT:
            return value, None
    return None, "EG_GIT_TIMEOUT_SECONDS 必须是 1 到 300 的整数，当前为 %s" % raw


def emit_json(payload, summary, code):
    raw = json.dumps(payload, ensure_ascii=False)
    sys.stdout.buffer.write(raw.encode("utf-8"))
    sys.stdout.buffer.write(b"\n")
    sys.stdout.buffer.flush()
    if not summary or not str(summary).strip():
        summary = payload.get("result") or "eg"
    line = str(summary).replace("\r", " ").replace("\n", " ")
    sys.stderr.buffer.write(line.encode("utf-8"))
    sys.stderr.buffer.write(b"\n")
    sys.stderr.buffer.flush()
    return code


def split_z(data):
    found = []
    for part in data.split(b"\0"):
        if part:
            found.append(part.decode("utf-8", "surrogateescape"))
    return found


def path_form_error(path):
    """Return why ``path`` breaks C03's form rules, or None."""
    if path is None or path == "" or os.path.isabs(path) or path.startswith("/") or path.startswith("\\"):
        return "不是相对于仓库根目录的相对路径"
    if "\\" in path:
        return "必须使用 / 作为分隔符"
    if "\n" in path or "\r" in path or "\x00" in path:
        return "含有换行或空字节"
    if path.endswith("/"):
        return "以 / 结尾"
    if "//" in path:
        return "含有连续的 /"
    parts = path.split("/")
    if any(part in (".", "..") or part == "" for part in parts):
        return "含有 . 或 .. 段"
    if ".git" in parts:
        return "位于 .git 下"
    return None


def path_kind(root, rel):
    """``missing``, ``symlink``, ``dir``, ``file``, or ``other``. Does not follow links."""
    try:
        st = os.lstat(os.path.join(root, rel))
    except OSError:
        return "missing"
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if stat.S_ISDIR(st.st_mode):
        return "dir"
    if stat.S_ISREG(st.st_mode):
        return "file"
    return "other"


def kind_message(kind):
    if kind == "missing":
        return "在工作区中不存在"
    if kind == "symlink":
        return "是符号链接，不是普通文件"
    if kind == "dir":
        return "是目录，不是普通文件"
    return "不是普通文件"


def failure_path_items(paths):
    return [
        {"path": path, "status": "not_committed", "blob": None, "sha256": None}
        for path in paths
    ]


def reset_command(paths):
    quoted = [shlex.quote(path) for path in paths]
    return "git reset -q -- " + " ".join(quoted)


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def message_ok(text):
    return bool(text) and "\n" not in text and "\r" not in text
