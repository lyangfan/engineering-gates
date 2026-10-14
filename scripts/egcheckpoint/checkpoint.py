"""``eg.py checkpoint`` (EG-S1).

Hook refusal is not a distinct git exit code: a failing hook returns 1 and
may write nothing. Each ``git commit`` is traced with ``GIT_TRACE2_EVENT``.
A hook ``child_exit`` whose code is not 0 is a refusal; any other non-zero
commit is an error (timeout and ``index.lock`` are classified first). If git
produced no trace events at all, an executable pre-commit / prepare-commit-msg
/ commit-msg hook plus exit code 1 and no ``fatal:`` line is treated the same
way. That rule does not depend on being under a test.
"""

import hashlib
import json
import os
import secrets
import tempfile

from .common import (
    IDENTITY_ENV,
    KINDS,
    OVERRIDE_KEYS,
    SPEC_RE,
    emit_json,
    failure_path_items,
    kind_message,
    message_ok,
    parse_timeout,
    path_form_error,
    path_kind,
    reset_command,
    split_z,
)
from .gitrun import Git, GitFailure, GitMissing, ensure_ok, is_lock_error

HOOK_NAMES = ("pre-commit", "prepare-commit-msg", "commit-msg")


def run_checkpoint(argv):
    try:
        return Checkpoint(argv).run()
    except GitMissing:
        return _crash(None, "找不到 git 可执行文件", 2)
    except Exception as exc:
        return _crash(exc, "内部错误：%s: %s" % (type(exc).__name__, exc), 1)


def _crash(exc, message, code):
    if exc is not None:
        import traceback
        traceback.print_exc()
    payload = {
        "schema": "eg-checkpoint/v1",
        "result": "error",
        "commit": None,
        "branch": None,
        "kind": None,
        "spec": None,
        "paths": [],
        "message": message,
    }
    return emit_json(payload, message, code)


class Checkpoint(object):
    def __init__(self, argv):
        self.argv = argv
        self.paths = []
        self.branch = None
        self.out_kind = None
        self.out_spec = None
        self.use_kind = None
        self.use_spec = "-"
        self.use_summary = "checkpoint"
        self.git = None
        self.root = None
        self.recorded = None
        self.unchanged_ids = {}

    def run(self):
        parse_error = self._parse()
        timeout, timeout_error = parse_timeout(os.environ.get("EG_GIT_TIMEOUT_SECONDS"))
        problems = [item for item in (parse_error, timeout_error) if item]
        if problems:
            return self.usage("；".join(problems))
        self.git = Git(os.getcwd(), timeout)
        if not self.git.binary:
            return self.usage("找不到 git 可执行文件")
        try:
            root = self._discover()
        except GitFailure as exc:
            return self.error(exc.message)
        if root is None:
            return self.usage("当前目录不在 git 仓库中")
        self.root = root
        self.git.cwd = root
        try:
            message = self._check_paths()
            if message:
                return self.refused(message)
            message = self._check_branch()
            if message:
                return self.refused(message)
            message = self._check_identity()
            if message:
                return self.refused(message)
            message = self._check_staged()
            if message:
                return self.refused(message)
            changed, unchanged = self._partition()
        except GitFailure as exc:
            return self.error(exc.message)
        if not changed:
            return self.refused("列出的路径都没有改动，拒绝产生空提交")
        return self._commit(changed, unchanged)

    def _parse(self):
        paths = []
        kind = None
        spec = None
        summary = None
        kind_given = False
        spec_given = False
        summary_given = False
        errors = []
        index = 0
        argv = self.argv
        while index < len(argv):
            arg = argv[index]
            if arg in ("--kind", "--spec", "--message", "--path"):
                if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
                    errors.append("参数 %s 缺少取值" % arg)
                    index += 1
                    continue
                value = argv[index + 1]
                index += 2
                if arg == "--path":
                    paths.append(value)
                elif arg == "--kind":
                    if kind_given:
                        errors.append("参数 --kind 重复")
                    kind_given = True
                    kind = value
                elif arg == "--spec":
                    if spec_given:
                        errors.append("参数 --spec 重复")
                    spec_given = True
                    spec = value
                else:
                    if summary_given:
                        errors.append("参数 --message 重复")
                    summary_given = True
                    summary = value
            else:
                errors.append("未知参数 %s" % arg)
                index += 1
        if not kind_given:
            errors.append("缺少必需参数 --kind")
        elif kind not in KINDS:
            errors.append("--kind 取值非法：%s" % kind)
        if not paths:
            errors.append("缺少必需参数 --path")
        if spec_given and not SPEC_RE.match(spec or ""):
            errors.append("--spec 取值非法：%s" % spec)
        if summary_given and not message_ok(summary):
            errors.append("--message 必须是不含换行或回车的非空单行文字")
        self.paths = paths
        self.out_kind = kind if kind_given and kind in KINDS else None
        self.out_spec = spec if spec_given and SPEC_RE.match(spec or "") else None
        self.use_kind = self.out_kind
        self.use_spec = self.out_spec if spec_given else "-"
        if summary_given and message_ok(summary):
            self.use_summary = summary
        else:
            self.use_summary = "checkpoint"
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

    def _check_paths(self):
        seen = set()
        for path in self.paths:
            reason = path_form_error(path)
            if reason:
                return "路径 %s %s" % (path, reason)
            if path in seen:
                return "路径 %s 重复出现" % path
            seen.add(path)
            kind = path_kind(self.root, path)
            if kind != "file":
                return "路径 %s %s" % (path, kind_message(kind))
        return None

    def _check_branch(self):
        result = self.git.run(["symbolic-ref", "--quiet", "HEAD"])
        if result.timed_out:
            raise GitFailure("timeout", "git 超时：symbolic-ref")
        if result.code != 0:
            if is_lock_error(result.err):
                raise GitFailure(
                    "lock",
                    "git 因 index.lock 被占用而失败（symbolic-ref），重试后仍未成功",
                )
            if result.code != 1:
                raise GitFailure(
                    "error",
                    "git symbolic-ref 失败：%s" % (result.err_text().strip() or result.code),
                )
            self.branch = None
            return "当前处于分离 HEAD，不能提交"
        ref = result.text().strip()
        if not ref.startswith("refs/heads/"):
            self.branch = None
            return "当前处于分离 HEAD，不能提交"
        name = ref[len("refs/heads/"):]
        self.branch = name
        if not name.startswith("eg/"):
            return "当前分支 %s 不以 eg/ 开头" % name
        head = self.git.run(["rev-parse", "--verify", "--quiet", "HEAD"])
        if head.timed_out:
            raise GitFailure("timeout", "git 超时：rev-parse HEAD")
        if head.code != 0 and is_lock_error(head.err):
            raise GitFailure(
                "lock",
                "git 因 index.lock 被占用而失败（rev-parse HEAD），重试后仍未成功",
            )
        if head.code != 0 or not head.text().strip():
            return "分支 %s 尚无提交，须先有一个初始提交" % name
        return None

    def _config_get(self, key):
        result = self.git.run(["config", "--get", "--null", key])
        if result.timed_out:
            raise GitFailure("timeout", "git 超时：config %s" % key)
        if result.code == 0:
            raw = result.out.split(b"\0", 1)[0]
            return raw.decode("utf-8", "replace")
        if is_lock_error(result.err):
            raise GitFailure(
                "lock",
                "git 因 index.lock 被占用而失败（config %s），重试后仍未成功" % key,
            )
        if result.code == 1:
            return None
        raise GitFailure(
            "error",
            "git config %s 失败：%s" % (key, result.err_text().strip() or result.code),
        )

    def _check_identity(self):
        present = [name for name in IDENTITY_ENV if name in os.environ]
        if present:
            return "环境变量会覆盖提交者身份：%s" % "、".join(present)
        overrides = []
        for key in OVERRIDE_KEYS:
            if self._config_get(key) is not None:
                overrides.append(key)
        if overrides:
            return "git 配置了会覆盖 user.* 的项：%s" % "、".join(overrides)
        missing = []
        for key in ("user.name", "user.email"):
            value = self._config_get(key)
            if value is None or value == "":
                missing.append(key)
        if missing:
            return "缺少 git 配置项：%s" % "、".join(missing)
        return None

    def _check_staged(self):
        result = self.git.run(
            ["diff", "--cached", "--name-only", "-z", "HEAD", "--"] + self.paths
        )
        ensure_ok(result, "diff --cached", ok=(0, 1))
        names = set(split_z(result.out))
        staged = [path for path in self.paths if path in names]
        if not staged:
            return None
        return "路径 %s 的暂存内容与 HEAD 不一致。恢复命令：%s" % (
            "、".join(staged),
            reset_command(staged),
        )

    def _partition(self):
        listed = self.git.run(["ls-tree", "-z", "--name-only", "HEAD", "--"] + self.paths)
        ensure_ok(listed, "ls-tree")
        in_head = set(split_z(listed.out))
        tracked = [path for path in self.paths if path in in_head]
        differ = set()
        if tracked:
            diff = self.git.run(["diff", "--name-only", "-z", "HEAD", "--"] + tracked)
            ensure_ok(diff, "diff", ok=(0, 1))
            differ = set(split_z(diff.out))
        changed = []
        unchanged = []
        for path in self.paths:
            if path not in in_head or path in differ:
                changed.append(path)
            else:
                unchanged.append(path)
        return changed, unchanged

    def _read_head(self):
        result = self.git.run(["rev-parse", "--verify", "HEAD"])
        ensure_ok(result, "rev-parse HEAD")
        return result.text().strip()

    def _identities(self, commit, paths):
        found = {}
        for path in paths:
            spec = "%s:%s" % (commit, path)
            rev = self.git.run(["rev-parse", "--verify", "--end-of-options", spec])
            ensure_ok(rev, "rev-parse")
            blob = rev.text().strip()
            data = self.git.run(["cat-file", "blob", blob])
            ensure_ok(data, "cat-file")
            found[path] = (blob, hashlib.sha256(data.out).hexdigest())
        return found

    def _commit(self, changed, unchanged):
        msg_path = None
        trace_path = None
        try:
            try:
                self.recorded = self._read_head()
                self.unchanged_ids = self._identities(self.recorded, unchanged)
                add = self.git.run(["add", "--"] + changed, writes=True)
                ensure_ok(add, "add")
            except GitFailure as exc:
                if exc.kind == "timeout":
                    return self._finish_restore(changed, exc.message, False)
                return self.error(exc.message)
            run_id = secrets.token_hex(16)
            msg_path = _write_message(self.use_kind, self.use_spec, self.use_summary, run_id)
            trace_path = _trace_file()
            result = self.git.run(
                ["commit", "--only", "--cleanup=verbatim", "-F", msg_path, "--"] + changed,
                extra_env={"GIT_TRACE2_EVENT": trace_path},
                writes=True,
            )
            if result.timed_out or result.code != 0:
                reason, hook = self._classify_commit(result, trace_path)
                return self._finish_restore(changed, reason, hook)
            try:
                return self._verify(changed, unchanged, run_id)
            except GitFailure as exc:
                return self.error(exc.message)
        finally:
            for path in (msg_path, trace_path):
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def _classify_commit(self, result, trace_path):
        if result.timed_out:
            return "git 超时：commit", False
        if is_lock_error(result.err):
            return "git 因 index.lock 被占用而失败（commit），重试后仍未成功", False
        failed, saw = _hook_failures(trace_path)
        if failed:
            reason = "钩子 %s 拒绝了本次提交" % "、".join(_unique(failed))
            detail = result.err_text().strip()
            if detail:
                reason = "%s：%s" % (reason, detail[:800])
            return reason, True
        if not saw:
            names = self._guess_hooks()
            if names and result.code == 1 and b"fatal:" not in result.err:
                return "钩子 %s 拒绝了本次提交" % "、".join(names), True
        detail = result.err_text().strip()
        return "git commit 失败：%s" % (detail[:800] or ("退出码 %s" % result.code)), False

    def _guess_hooks(self):
        directory = None
        try:
            configured = self._config_get("core.hooksPath")
        except GitFailure:
            configured = None
        if configured:
            if os.path.isabs(configured):
                directory = configured
            else:
                directory = os.path.join(self.root, configured)
        else:
            result = self.git.run(["rev-parse", "--git-path", "hooks"])
            if result.code == 0 and not result.timed_out:
                hook_dir = result.text().strip()
                if hook_dir and not os.path.isabs(hook_dir):
                    hook_dir = os.path.join(self.git.cwd, hook_dir)
                directory = hook_dir
        if not directory:
            return []
        found = []
        for name in HOOK_NAMES:
            path = os.path.join(directory, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                found.append(name)
        return found

    def _finish_restore(self, paths, reason, hook):
        if self._restore(paths):
            if hook:
                return self.refused(reason)
            return self.error(reason)
        still = self._still_staged(paths)
        shown = still or list(paths)
        return self.error(
            "%s。无法恢复暂存区。仍处于已暂存状态的路径：%s。恢复命令：%s"
            % (reason, "、".join(shown), reset_command(shown))
        )

    def _restore(self, paths):
        if not paths:
            return True
        result = self.git.run(["reset", "-q", "--"] + list(paths), writes=True)
        return (not result.timed_out) and result.code == 0

    def _still_staged(self, paths):
        result = self.git.run(
            ["diff", "--cached", "--name-only", "-z", "HEAD", "--"] + list(paths)
        )
        if result.timed_out or result.code not in (0, 1):
            return list(paths)
        names = set(split_z(result.out))
        return [path for path in paths if path in names]

    def _verify(self, changed, unchanged, run_id):
        listing = self.git.run(["rev-list", "%s..HEAD" % self.recorded])
        ensure_ok(listing, "rev-list")
        found = []
        for sha in listing.text().split():
            trailer = self.git.run(
                ["log", "-1", "--format=%(trailers:key=EG-Run,valueonly)", sha]
            )
            ensure_ok(trailer, "log")
            if trailer.text().strip() == run_id:
                found.append(sha)
        if len(found) != 1:
            if not found:
                return self.error(
                    "git commit 已返回成功，但在记录的 HEAD 与当前 HEAD 之间没有找到带有本次 EG-Run 的提交"
                )
            return self.error("找到多个带有本次 EG-Run 的提交：%s" % "、".join(found))
        sha = found[0]
        parent, changed_paths = self._commit_paths(sha)
        if parent is None or set(changed_paths) != set(changed):
            return self.error(
                "提交 %s 未通过核对：父提交或改动路径与本次有改动的路径不一致" % sha,
                commit=sha,
            )
        committed = self._identities(sha, changed)
        items = []
        for path in self.paths:
            if path in committed:
                blob, digest = committed[path]
                status = "committed"
            else:
                blob, digest = self.unchanged_ids[path]
                status = "unchanged"
            items.append(
                {"path": path, "status": status, "blob": blob, "sha256": digest}
            )
        return self.emit(0, "committed", "", commit=sha, items=items, success=True)

    def _commit_paths(self, sha):
        listed = self.git.run(["rev-list", "--parents", "-n", "1", sha])
        ensure_ok(listed, "rev-list")
        parts = listed.text().split()
        if len(parts) != 2:
            return None, []
        parent = parts[1]
        diff = self.git.run(
            ["diff-tree", "--no-commit-id", "-r", "--name-only", "-z", parent, sha]
        )
        ensure_ok(diff, "diff-tree", ok=(0, 1))
        return parent, split_z(diff.out)

    def emit(self, code, result, message, commit=None, items=None, success=False):
        if items is None:
            items = failure_path_items(self.paths)
        payload = {
            "schema": "eg-checkpoint/v1",
            "result": result,
            "commit": commit,
            "branch": self.branch,
            "kind": self.use_kind if success else self.out_kind,
            "spec": self.use_spec if success else self.out_spec,
            "paths": items,
            "message": message,
        }
        if success:
            summary = "committed %s on %s" % (commit, self.branch or "")
        else:
            summary = "%s: %s" % (result, message)
        return emit_json(payload, summary, code)

    def usage(self, message):
        return self.emit(2, "error", message)

    def refused(self, message):
        return self.emit(1, "refused", message)

    def error(self, message, commit=None):
        return self.emit(1, "error", message, commit=commit)


def _write_message(kind, spec, summary, run_id):
    text = "eg(%s): %s %s\n\nEG-Kind: %s\nEG-Spec: %s\nEG-Run: %s\n" % (
        kind,
        spec,
        summary,
        kind,
        spec,
        run_id,
    )
    fd, path = tempfile.mkstemp(prefix="eg-checkpoint-msg-")
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)
    return path


def _trace_file():
    fd, path = tempfile.mkstemp(prefix="eg-checkpoint-trace-")
    os.close(fd)
    return path


def _unique(names):
    found = []
    for name in names:
        if name not in found:
            found.append(name)
    return found


def _hook_failures(path):
    """Return ``(failed hook names, saw any trace event)``."""
    names = {}
    failed = []
    saw = False
    try:
        handle = open(path, "r", encoding="utf-8", errors="replace")
    except OSError:
        return [], False
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            saw = True
            child = str(event.get("child_id"))
            if event.get("event") == "child_start" and event.get("child_class") == "hook":
                names[child] = event.get("hook_name") or "hook"
            elif event.get("event") == "child_exit" and child in names:
                if event.get("code") not in (0, None):
                    failed.append(names[child])
    return failed, saw
