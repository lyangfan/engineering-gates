"""Run git in its own process group, with a timeout and bounded lock retries.

Lock files are never deleted. A lock conflict (stderr contains both
``index.lock`` and ``File exists``) is retried at most five times for that
one invocation; the waits between those attempts add up to at most two
seconds. The caller gives recovery its own ``Git`` calls, so recovery gets
a separate budget.
"""

import os
import shutil
import signal
import subprocess
import time

# Five attempts total: the original call plus four retries.
LOCK_ATTEMPTS = 5
# Four gaps. 0.25 * 4 = 1.0s, within the 2s budget.
LOCK_WAIT_SECONDS = 0.25
TERM_GRACE_SECONDS = 10


class GitMissing(Exception):
    """``git`` is not on ``PATH``."""


class GitFailure(Exception):
    """A git call timed out, lost a lock retry, or failed unexpectedly."""

    def __init__(self, kind, message):
        Exception.__init__(self, message)
        self.kind = kind
        self.message = message


class GitResult(object):
    def __init__(self, code, out, err, timed_out):
        self.code = code
        self.out = out or b""
        self.err = err or b""
        self.timed_out = timed_out

    def text(self):
        return self.out.decode("utf-8", "replace")

    def err_text(self):
        return self.err.decode("utf-8", "replace")


def is_lock_error(err):
    return b"index.lock" in err and b"File exists" in err


def _clip(text, limit):
    text = (text or "").strip()
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def ensure_ok(result, what, ok=(0,)):
    """Raise ``GitFailure`` unless ``result.code`` is an accepted status."""
    if result.timed_out:
        raise GitFailure("timeout", "git 超时：%s" % what)
    if result.code in ok:
        return result
    if is_lock_error(result.err):
        raise GitFailure(
            "lock",
            "git 因 index.lock 被占用而失败（%s），重试后仍未成功" % what,
        )
    detail = _clip(result.err_text(), 800)
    raise GitFailure(
        "error",
        "git %s 失败：%s" % (what, detail or ("退出码 %s" % result.code)),
    )


class Git(object):
    def __init__(self, cwd, timeout):
        self.cwd = cwd
        self.timeout = timeout
        self.binary = shutil.which("git")
        self.env = os.environ.copy()

    def run(self, args, extra_env=None, writes=False):
        if not self.binary:
            raise GitMissing()
        cmd = list(args)
        if not writes:
            # Read-only calls must not refresh the index (that takes index.lock
            # and can change the index file under a concurrent checkpoint).
            cmd.insert(0, "--no-optional-locks")
        env = self.env
        if extra_env:
            env = dict(self.env)
            env.update(extra_env)
        last = None
        for attempt in range(LOCK_ATTEMPTS):
            if attempt:
                time.sleep(LOCK_WAIT_SECONDS)
            last = self._once(cmd, env)
            if last.timed_out or last.code == 0 or not is_lock_error(last.err):
                return last
        return last

    def _once(self, args, env):
        argv = [self.binary]
        argv.extend(args)
        proc = subprocess.Popen(
            argv,
            cwd=self.cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            try:
                out, err = proc.communicate(timeout=self.timeout)
                return GitResult(proc.returncode, out, err, False)
            except subprocess.TimeoutExpired:
                self._signal_group(proc, signal.SIGTERM)
                try:
                    out, err = proc.communicate(timeout=TERM_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    self._signal_group(proc, signal.SIGKILL)
                    out, err = proc.communicate()
                return GitResult(proc.returncode, out, err, True)
        except Exception:
            self._signal_group(proc, signal.SIGKILL)
            try:
                proc.communicate()
            except Exception:
                pass
            raise

    def _signal_group(self, proc, sig):
        try:
            os.killpg(proc.pid, sig)
        except OSError:
            try:
                proc.send_signal(sig)
            except OSError:
                pass
