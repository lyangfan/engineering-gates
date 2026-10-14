"""``eg.py identity`` (EG-S1)."""

import os

from .common import (
    emit_json,
    file_sha256,
    kind_message,
    parse_timeout,
    path_form_error,
    path_kind,
)
from .gitrun import Git, GitFailure, GitMissing, is_lock_error


def run_identity(argv):
    try:
        return Identity(argv).run()
    except GitMissing:
        return _emit("", "error", None, None, None, None, False, "找不到 git 可执行文件", 2)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        message = "内部错误：%s: %s" % (type(exc).__name__, exc)
        return _emit("", "error", None, None, None, None, False, message, 1)


class Identity(object):
    def __init__(self, argv):
        self.argv = argv
        self.path = ""
        self.at = "HEAD"
        self.git = None
        self.root = None

    def run(self):
        errors = self._parse()
        _timeout, timeout_error = parse_timeout(os.environ.get("EG_GIT_TIMEOUT_SECONDS"))
        timeout = _timeout
        problems = [item for item in (errors, timeout_error) if item]
        if problems:
            return self._done("error", None, None, None, None, False, "；".join(problems), 2)
        self.git = Git(os.getcwd(), timeout)
        if not self.git.binary:
            return self._done("error", None, None, None, None, False, "找不到 git 可执行文件", 2)
        try:
            root = self._discover()
        except GitFailure as exc:
            return self._done("error", None, None, None, None, False, exc.message, 1)
        if root is None:
            return self._done("error", None, None, None, None, False, "当前目录不在 git 仓库中", 2)
        self.root = root
        self.git.cwd = root
        problem = self._path_problem()
        if problem:
            return self._done("error", None, None, None, None, False, problem, 1)
        try:
            commit = self._resolve()
        except GitFailure as exc:
            return self._done("error", None, None, None, None, False, exc.message, 1)
        if commit is None:
            return self._done(
                "error", None, None, None, None, False,
                "无法解析 --at：%s" % self.at, 2,
            )
        try:
            blob, digest = self._lookup(commit)
            working = self._working_sha()
        except GitFailure as exc:
            return self._done("error", commit, None, None, None, False, exc.message, 1)
        except OSError as exc:
            return self._done(
                "error", commit, None, None, None, False,
                "无法读取工作区文件 %s：%s" % (self.path, exc), 1,
            )
        if blob is None:
            return self._done("missing", commit, None, None, working, False, "", 1)
        if working is None or working != digest:
            return self._done("mismatch", commit, blob, digest, working, False, "", 1)
        return self._done("match", commit, blob, digest, working, True, "", 0)

    def _parse(self):
        path = None
        path_count = 0
        at = "HEAD"
        at_given = False
        errors = []
        index = 0
        argv = self.argv
        while index < len(argv):
            arg = argv[index]
            if arg in ("--path", "--at"):
                if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                    errors.append("参数 %s 缺少取值" % arg)
                    index += 1
                    continue
                value = argv[index + 1]
                index += 2
                if arg == "--path":
                    path_count += 1
                    if path is None:
                        path = value
                    else:
                        errors.append("参数 --path 重复")
                else:
                    if at_given:
                        errors.append("参数 --at 重复")
                    at_given = True
                    at = value
            else:
                errors.append("未知参数 %s" % arg)
                index += 1
        if path_count == 0:
            errors.append("缺少必需参数 --path")
        self.path = path if path is not None else ""
        self.at = at
        return "；".join(errors)

    def _discover(self):
        result = self.git.run(["rev-parse", "--show-toplevel"])
        if result.timed_out:
            raise GitFailure("timeout", "git 超时：rev-parse --show-toplevel")
        if result.code == 0:
            root = result.text().strip()
            return root or None
        if is_lock_error(result.err):
            raise GitFailure(
                "lock",
                "git 因 index.lock 被占用而失败（rev-parse），重试后仍未成功",
            )
        err = result.err_text()
        if "not a git repository" in err.lower():
            return None
        raise GitFailure(
            "error",
            "git rev-parse --show-toplevel 失败：%s" % (err.strip() or result.code),
        )

    def _path_problem(self):
        reason = path_form_error(self.path)
        if reason:
            return "路径 %s %s" % (self.path, reason)
        kind = path_kind(self.root, self.path)
        if kind == "missing":
            return None
        if kind != "file":
            return "路径 %s %s" % (self.path, kind_message(kind))
        return None

    def _resolve(self):
        spec = "%s^{commit}" % self.at
        result = self.git.run(["rev-parse", "--verify", "--end-of-options", spec])
        if result.timed_out:
            raise GitFailure("timeout", "git 超时：rev-parse")
        if result.code == 0:
            commit = result.text().strip()
            return commit or None
        if is_lock_error(result.err):
            raise GitFailure(
                "lock",
                "git 因 index.lock 被占用而失败（rev-parse），重试后仍未成功",
            )
        return None

    def _lookup(self, commit):
        spec = "%s:%s" % (commit, self.path)
        rev = self.git.run(["rev-parse", "--verify", "--quiet", "--end-of-options", spec])
        if rev.timed_out:
            raise GitFailure("timeout", "git 超时：rev-parse")
        if rev.code != 0:
            if is_lock_error(rev.err):
                raise GitFailure(
                    "lock",
                    "git 因 index.lock 被占用而失败（rev-parse），重试后仍未成功",
                )
            return None, None
        blob = rev.text().strip()
        kind = self.git.run(["cat-file", "-t", blob])
        if kind.timed_out:
            raise GitFailure("timeout", "git 超时：cat-file")
        if kind.code != 0 or kind.text().strip() != "blob":
            if is_lock_error(kind.err):
                raise GitFailure(
                    "lock",
                    "git 因 index.lock 被占用而失败（cat-file），重试后仍未成功",
                )
            return None, None
        data = self.git.run(["cat-file", "blob", blob])
        if data.timed_out:
            raise GitFailure("timeout", "git 超时：cat-file")
        if data.code != 0:
            if is_lock_error(data.err):
                raise GitFailure(
                    "lock",
                    "git 因 index.lock 被占用而失败（cat-file），重试后仍未成功",
                )
            raise GitFailure(
                "error",
                "git cat-file 失败：%s" % (data.err_text().strip() or data.code),
            )
        import hashlib
        return blob, hashlib.sha256(data.out).hexdigest()

    def _working_sha(self):
        if path_kind(self.root, self.path) != "file":
            return None
        return file_sha256(os.path.join(self.root, self.path))

    def _done(self, result, commit, blob, digest, working, matches, message, code):
        if result == "match":
            summary = "match %s" % self.path
        elif message:
            summary = "%s: %s" % (result, message)
        else:
            summary = "%s %s" % (result, self.path)
        return _emit(self.path, result, commit, blob, digest, working, matches, message, code, summary)


def _emit(path, result, commit, blob, digest, working, matches, message, code, summary=None):
    payload = {
        "schema": "eg-identity/v1",
        "result": result,
        "path": path,
        "commit": commit,
        "blob": blob,
        "sha256": digest,
        "working_sha256": working,
        "matches": matches,
        "message": message,
    }
    if summary is None:
        summary = message or result
    return emit_json(payload, summary, code)
