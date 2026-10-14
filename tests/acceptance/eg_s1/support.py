"""Shared fixtures for the EG-S1 acceptance tests.

The tests are black-box: the implementation is only exercised as a subprocess
(`python scripts/eg.py checkpoint|identity ...`) whose cwd is a throw-away git
repository created under `tempfile`. Git configuration and identity-related
environment variables of the fixture are fully controlled here so that the
machine's global configuration cannot leak in.
"""

import ast
import hashlib
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.realpath(
    os.environ.get('EG_REPO_ROOT') or os.path.join(HERE, '..', '..', '..'))
EG_PY = os.path.join(REPO_ROOT, 'scripts', 'eg.py')
BASE_COMMIT = '26f2e0c'
BASELINE_SCRIPTS = (
    'scripts/__init__.py',
    'scripts/decision_coverage.py',
    'scripts/digest_table.py',
    'scripts/engineering.py',
    'scripts/run_tests.py',
    'scripts/snapshots.py',
    'scripts/tests/test_engineering.py',
)

REAL_GIT = shutil.which('git')
PYTHON = sys.executable

HEX40 = re.compile(r'^[0-9a-f]{40}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
RUN_ID = re.compile(r'^[0-9a-f]{32}$')
KINDS = ('spec-freeze', 'tests-freeze', 'candidate', 'review', 'record')

FIXTURE_NAME = 'EG Fixture'
FIXTURE_EMAIL = 'fixture@example.invalid'
IDENTITY_ENV_VARS = ('GIT_AUTHOR_NAME', 'GIT_AUTHOR_EMAIL',
                     'GIT_COMMITTER_NAME', 'GIT_COMMITTER_EMAIL')
IDENTITY_OVERRIDE_KEYS = ('author.name', 'author.email',
                          'committer.name', 'committer.email')

DEFAULT_RUN_TIMEOUT = 30

BASE_FILES = {
    'a.txt': b'alpha\n',
    'b.txt': b'bravo\n',
    'other.txt': b'other\n',
    'docs/spec.md': b'# spec\n',
    'sub/a.txt': b'sub alpha\n',
    'sub/c.txt': b'charlie\n',
    'script.sh': b'#!/bin/sh\necho hi\n',
}

_STRIP_ENV = frozenset((
    'PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX', 'PYTHONPATH',
    'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT', 'PYTHONUSERBASE',
    'PYTHONSAFEPATH', 'EMAIL', 'EDITOR', 'VISUAL', 'LANGUAGE',
))

_LIVE_PROCS = []


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def base_env(tmp_base, global_config, home):
    env = {}
    for key, value in os.environ.items():
        if key.startswith('GIT_') or key.startswith('EG_') or key in _STRIP_ENV:
            continue
        env[key] = value
    env.update({
        'HOME': home,
        'XDG_CONFIG_HOME': os.path.join(home, '.config'),
        'GIT_CONFIG_GLOBAL': global_config,
        'GIT_CONFIG_SYSTEM': os.devnull,
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_TERMINAL_PROMPT': '0',
        'GIT_CEILING_DIRECTORIES': os.path.dirname(tmp_base),
        'LC_ALL': 'C',
        'LANG': 'C',
    })
    return env


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    out = subprocess.run(['ps', '-o', 'stat=', '-p', str(pid)],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         universal_newlines=True).stdout.strip()
    return bool(out) and not out.startswith('Z')


def kill_tree_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def cleanup_live_processes():
    while _LIVE_PROCS:
        proc = _LIVE_PROCS.pop()
        if proc.poll() is None:
            kill_tree_group(proc)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass


class EgResult(object):
    def __init__(self, args, code, stdout, stderr, elapsed, timed_out):
        self.args = args
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed = elapsed
        self.timed_out = timed_out

    def describe(self):
        return ('eg args=%r\nexit=%r timed_out=%r elapsed=%.2fs\n--- stdout ---\n%s\n'
                '--- stderr ---\n%s' % (self.args, self.code, self.timed_out,
                                        self.elapsed, self.stdout, self.stderr))

    def json(self):
        try:
            data = json.loads(self.stdout)
        except ValueError as exc:
            raise AssertionError('stdout is not a single JSON value (%s)\n%s'
                                 % (exc, self.describe()))
        if not isinstance(data, dict):
            raise AssertionError('stdout JSON is not an object\n' + self.describe())
        return data


class EgProcess(object):
    """A started eg process (used for concurrency and kill scenarios)."""

    def __init__(self, args, popen, started):
        self.args = args
        self.popen = popen
        self.started = started

    @property
    def pid(self):
        return self.popen.pid

    def finish(self, timeout=DEFAULT_RUN_TIMEOUT):
        timed_out = False
        try:
            out, err = self.popen.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree_group(self.popen)
            out, err = self.popen.communicate()
        elapsed = time.monotonic() - self.started
        if self.popen in _LIVE_PROCS:
            _LIVE_PROCS.remove(self.popen)
        return EgResult(self.args, self.popen.returncode,
                        out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace'),
                        elapsed, timed_out)


def start_eg(subcmd, args, cwd, env, eg_py=None):
    argv = [PYTHON, eg_py or EG_PY, subcmd] + list(args)
    started = time.monotonic()
    popen = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
    _LIVE_PROCS.append(popen)
    return EgProcess(argv[2:], popen, started)


class Fixture(object):
    """A temporary git repository used as cwd for eg."""

    def __init__(self, testcase, branch='eg/v2', init_branch='main',
                 identity=True, initial_commit=True, files=None):
        self.base = os.path.realpath(tempfile.mkdtemp(prefix='eg-s1-'))
        testcase.addCleanup(shutil.rmtree, self.base, True)
        self.root = os.path.join(self.base, 'repo')
        self.home = os.path.join(self.base, 'home')
        self.aux = os.path.join(self.base, 'aux')
        for d in (self.root, self.home, self.aux):
            os.makedirs(d)
        self.global_config = os.path.join(self.base, 'gitconfig-global')
        open(self.global_config, 'w').close()
        self.env = base_env(self.base, self.global_config, self.home)
        self.git('init', '-q', '-b', init_branch, '.')
        for key, value in (('commit.gpgsign', 'false'), ('gc.auto', '0'),
                           ('maintenance.auto', 'false'), ('core.filemode', 'true'),
                           ('core.autocrlf', 'false'), ('core.fsmonitor', 'false')):
            self.git('config', key, value)
        if identity:
            self.git('config', 'user.name', FIXTURE_NAME)
            self.git('config', 'user.email', FIXTURE_EMAIL)
        if initial_commit:
            for rel, data in (files or BASE_FILES).items():
                self.write(rel, data)
            self.git('add', '-A')
            self.setup_commit('fixture: base')
            if branch != init_branch:
                self.git('checkout', '-q', '-b', branch)

    # ---- plumbing -------------------------------------------------------
    def git(self, *args, **kw):
        check = kw.pop('check', True)
        env = dict(self.env)
        env.update(kw.pop('env_extra', {}) or {})
        cwd = kw.pop('cwd', self.root)
        proc = subprocess.run([REAL_GIT] + list(args), cwd=cwd, env=env,
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=60)
        if check and proc.returncode != 0:
            raise AssertionError('fixture git %r failed: %s'
                                 % (args, proc.stderr.decode('utf-8', 'replace')))
        return proc

    def out(self, *args, **kw):
        return self.git(*args, **kw).stdout.decode('utf-8', 'replace').strip()

    def setup_commit(self, message, *paths):
        args = ['-c', 'user.name=' + FIXTURE_NAME, '-c', 'user.email=' + FIXTURE_EMAIL,
                'commit', '-q', '--no-verify', '-m', message]
        if paths:
            args += ['--'] + list(paths)
        self.git(*args)
        return self.head()

    def path(self, rel):
        return os.path.join(self.root, rel)

    def write(self, rel, data, executable=None):
        if isinstance(data, str):
            data = data.encode('utf-8')
        p = self.path(rel)
        d = os.path.dirname(p)
        if not os.path.isdir(d):
            os.makedirs(d)
        with open(p, 'wb') as f:
            f.write(data)
        if executable is not None:
            mode = os.stat(p).st_mode
            os.chmod(p, (mode | 0o111) if executable else (mode & ~0o111))

    def append(self, rel, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        with open(self.path(rel), 'ab') as f:
            f.write(data)

    def read(self, rel):
        with open(self.path(rel), 'rb') as f:
            return f.read()

    def stage(self, rel, data):
        self.write(rel, data)
        self.git('add', '--', rel)

    def install_hook(self, name, body):
        hooks = os.path.join(self.root, '.git', 'hooks')
        if not os.path.isdir(hooks):
            os.makedirs(hooks)
        p = os.path.join(hooks, name)
        with open(p, 'w') as f:
            f.write(body)
        os.chmod(p, 0o755)
        return p

    # ---- queries --------------------------------------------------------
    def head(self):
        proc = self.git('rev-parse', '-q', '--verify', 'HEAD', check=False)
        if proc.returncode != 0:
            return None
        return proc.stdout.decode().strip()

    def rev(self, spec):
        return self.out('rev-parse', '--verify', spec)

    def show(self, commit, rel):
        return self.git('show', '%s:%s' % (commit, rel)).stdout

    def blob(self, commit, rel):
        return self.out('rev-parse', '%s:%s' % (commit, rel))

    def index_entry(self, rel):
        """`git ls-files -s` line for rel ('' when not in the index)."""
        return self.out('ls-files', '-s', '--', rel)

    def head_entry(self, rel):
        return self.out('ls-tree', 'HEAD', '--', rel)

    def tree_mode(self, commit, rel):
        line = self.out('ls-tree', commit, '--', rel)
        return line.split()[0] if line else None

    def parents(self, commit):
        return self.out('rev-list', '--parents', '-n', '1', commit).split()[1:]

    def changed_paths(self, commit):
        parents = self.parents(commit)
        if len(parents) != 1:
            return None
        raw = self.git('diff-tree', '--no-commit-id', '-r', '--name-only', '-z',
                       parents[0], commit).stdout.decode('utf-8')
        return set(p for p in raw.split('\0') if p)

    def commits_between(self, old, new='HEAD'):
        raw = self.out('rev-list', '%s..%s' % (old, new))
        return [c for c in raw.split() if c]

    def message(self, commit):
        return self.git('log', '-1', '--format=%B', commit).stdout.decode('utf-8')

    def subject(self, commit):
        return self.out('log', '-1', '--format=%s', commit)

    def trailer(self, commit, key):
        return self.git('log', '-1', '--format=%%(trailers:key=%s,valueonly)' % key,
                        commit).stdout.decode('utf-8').strip()

    def lock_files(self):
        found = []
        gitdir = os.path.join(self.root, '.git')
        for dirpath, dirnames, filenames in os.walk(gitdir):
            for name in filenames:
                if name.endswith('.lock'):
                    found.append(os.path.relpath(os.path.join(dirpath, name), self.root))
        return sorted(found)

    def worktree(self):
        state = {}
        for dirpath, dirnames, filenames in os.walk(self.root):
            if dirpath == self.root and '.git' in dirnames:
                dirnames.remove('.git')
            for name in sorted(dirnames + filenames):
                p = os.path.join(dirpath, name)
                rel = os.path.relpath(p, self.root)
                st = os.lstat(p)
                if stat.S_ISLNK(st.st_mode):
                    state[rel] = ('link', os.readlink(p))
                elif stat.S_ISDIR(st.st_mode):
                    state[rel] = ('dir',)
                else:
                    with open(p, 'rb') as f:
                        state[rel] = ('file', bool(st.st_mode & 0o100), f.read())
        return state

    def snapshot(self):
        sym = self.git('symbolic-ref', '-q', 'HEAD', check=False)
        return {
            'HEAD': self.head(),
            'symbolic-ref': sym.stdout.decode().strip() if sym.returncode == 0 else None,
            'refs': self.out('for-each-ref', '--format=%(refname) %(objectname)'),
            'index': self.git('ls-files', '-s', '-z').stdout,
            'worktree': self.worktree(),
            'locks': self.lock_files(),
        }

    def path_state(self, rel):
        """Index entry plus working-tree bytes/exec bit of one path."""
        p = self.path(rel)
        if os.path.lexists(p):
            st = os.lstat(p)
            with open(p, 'rb') as f:
                wt = (bool(st.st_mode & 0o100), f.read())
        else:
            wt = None
        return (self.index_entry(rel), wt)

    # ---- running eg -----------------------------------------------------
    def env_for(self, env_extra=None, env_remove=(), path_prefix=None):
        env = dict(self.env)
        if path_prefix:
            env['PATH'] = os.pathsep.join(list(path_prefix) + [env.get('PATH', '')])
        env.update(env_extra or {})
        for key in env_remove:
            env.pop(key, None)
        return env

    def start(self, subcmd, args, cwd=None, env_extra=None, env_remove=(),
              path_prefix=None, eg_py=None):
        env = self.env_for(env_extra, env_remove, path_prefix)
        return start_eg(subcmd, args, cwd or self.root, env, eg_py=eg_py)

    def run(self, subcmd, args, cwd=None, env_extra=None, env_remove=(),
            path_prefix=None, timeout=DEFAULT_RUN_TIMEOUT, eg_py=None):
        return self.start(subcmd, args, cwd, env_extra, env_remove, path_prefix,
                          eg_py).finish(timeout)

    def checkpoint(self, *args, **kw):
        return self.run('checkpoint', list(args), **kw)

    def identity(self, *args, **kw):
        return self.run('identity', list(args), **kw)

    # ---- fault injection helpers ---------------------------------------
    def git_wrapper(self, rules=()):
        """Install a `git` wrapper; returns (bin_dir, log_path).

        The wrapper logs each invocation (argv, pid, ppid, process groups and
        the content of the `commit -F` message file) and then either execs
        the real git, or runs it as a child and performs `after` actions.
        """
        bin_dir = os.path.join(self.aux, 'wrapper-bin')
        os.makedirs(bin_dir)
        log_path = os.path.join(self.aux, 'git-calls.jsonl')
        open(log_path, 'w').close()
        conf = {'real_git': REAL_GIT, 'log': log_path, 'rules': list(rules),
                'env': self.env}
        script = os.path.join(bin_dir, 'git')
        with open(script, 'w') as f:
            f.write(WRAPPER_TEMPLATE.replace('@PYTHON@', PYTHON)
                    .replace('@CONF@', repr(json.dumps(conf))))
        os.chmod(script, 0o755)
        return bin_dir, log_path

    def audit_site(self):
        """Directory with a sitecustomize installing an audit hook; returns
        (env_extra, log_path) recording any deletion/rename of *.lock files."""
        site_dir = os.path.join(self.aux, 'audit-site')
        os.makedirs(site_dir)
        with open(os.path.join(site_dir, 'sitecustomize.py'), 'w') as f:
            f.write(AUDIT_SITECUSTOMIZE)
        log_path = os.path.join(self.aux, 'audit.jsonl')
        open(log_path, 'w').close()
        return {'PYTHONPATH': site_dir, 'EG_TEST_AUDIT_LOG': log_path}, log_path


def read_jsonl(path):
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


WRITE_SUBCOMMANDS_ALWAYS = frozenset((
    'add', 'commit', 'reset', 'rm', 'mv', 'restore', 'checkout', 'switch',
    'stash', 'apply', 'am', 'merge', 'rebase', 'cherry-pick', 'revert', 'tag',
    'write-tree', 'commit-tree', 'update-ref', 'read-tree', 'mktree', 'gc',
    'prune', 'repack', 'notes', 'clean', 'pull', 'push', 'fetch', 'clone',
    'init', 'worktree', 'replace', 'filter-branch', 'maintenance', 'checkout-index',
    'merge-file', 'reflog',
))
READ_ONLY_SUBCOMMANDS = frozenset((
    'rev-parse', 'cat-file', 'show', 'log', 'ls-files', 'ls-tree', 'diff',
    'diff-index', 'diff-files', 'diff-tree', 'status', 'rev-list',
    'for-each-ref', 'var', 'version', 'check-ignore', 'check-attr', 'name-rev',
    'describe', 'merge-base', 'show-ref', 'interpret-trailers', 'count-objects',
    'help', 'grep', 'blame', 'shortlog', 'check-ref-format', 'whatchanged',
    'show-branch', 'cherry', 'fsck', 'verify-commit', 'get-tar-commit-id',
))
REFRESH_ONLY_UPDATE_INDEX_FLAGS = frozenset((
    '-q', '--refresh', '--really-refresh', '--ignore-missing', '--unmerged',
    '--ignore-submodules',
))


def is_write_invocation(entry):
    """Whether a logged git invocation can change refs, index content or files."""
    sub = entry.get('sub')
    rest = entry.get('rest') or []
    if sub in READ_ONLY_SUBCOMMANDS or sub is None:
        return False
    if sub in WRITE_SUBCOMMANDS_ALWAYS:
        return True
    if sub == 'update-index':
        # A pure stat refresh does not change index content; anything else does.
        return not all(a in REFRESH_ONLY_UPDATE_INDEX_FLAGS for a in rest)
    if sub == 'hash-object':
        return '-w' in rest
    if sub == 'symbolic-ref':
        positional = [a for a in rest if not a.startswith('-')]
        return len(positional) > 1 or '-d' in rest or '--delete' in rest
    if sub == 'branch':
        allowed = ('--show-current', '--list', '-l', '--contains', '--format',
                   '-v', '-vv', '-a', '-r', '--no-color', '--points-at')
        return any(not (a in allowed or a.startswith('--format=')) for a in rest)
    if sub == 'config':
        flags = [a for a in rest if a.startswith('-')]
        positional = [a for a in rest if not a.startswith('-')]
        writing = ('--unset', '--unset-all', '--add', '--replace-all',
                   '--rename-section', '--remove-section', '--edit', '-e')
        if any(f in writing for f in flags):
            return True
        if any(f in ('--get', '--get-all', '--get-regexp', '--list', '-l')
               or f.startswith('--get') for f in flags):
            return False
        return len(positional) > 1
    return True


def args_after_subcommand(entry):
    return list(entry.get('rest') or [])


def split_pathspec(args):
    if '--' in args:
        i = args.index('--')
        return args[:i], args[i + 1:]
    return args, []


WRAPPER_TEMPLATE = r'''#!@PYTHON@ -S
import fcntl, json, os, signal, subprocess, sys

CONF = json.loads(@CONF@)
REAL = CONF["real_git"]
WITH_ARG = ("-c", "-C", "--git-dir", "--work-tree", "--namespace", "--config-env",
            "--super-prefix", "--list-cmds")


def split(argv):
    cdirs = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in WITH_ARG:
            if a == "-C" and i + 1 < len(argv):
                cdirs.append(argv[i + 1])
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a, argv[i + 1:], cdirs
    return None, [], cdirs


argv = sys.argv[1:]
sub, rest, cdirs = split(argv)
cwd = os.getcwd()
for d in cdirs:
    cwd = os.path.join(cwd, d)
entry = {"argv": argv, "sub": sub, "rest": rest, "pid": os.getpid(),
         "ppid": os.getppid(), "pgid": os.getpgrp(), "cwd": cwd}
try:
    entry["ppgid"] = os.getpgid(os.getppid())
except OSError:
    entry["ppgid"] = None
if sub == "commit":
    msg_file = None
    for i, a in enumerate(rest):
        if a == "--":
            break
        if a in ("-F", "--file") and i + 1 < len(rest):
            msg_file = rest[i + 1]
        elif a.startswith("--file="):
            msg_file = a[len("--file="):]
        elif a.startswith("-F") and len(a) > 2:
            msg_file = a[2:]
    if msg_file:
        try:
            with open(os.path.join(cwd, msg_file), "rb") as f:
                entry["message"] = f.read().decode("utf-8", "replace")
        except OSError:
            entry["message"] = None

with open(CONF["log"], "a") as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    f.write(json.dumps(entry) + "\n")
    f.flush()
    with open(CONF["log"]) as r:
        nth = sum(1 for line in r if line.strip() and json.loads(line).get("sub") == sub)
    fcntl.flock(f, fcntl.LOCK_UN)


def act(rule):
    action = rule["action"]
    p = rule.get("args", {})
    if action == "kill_parent":
        os.kill(os.getppid(), signal.SIGKILL)
    elif action == "create_file":
        fd = os.open(p["path"], os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        os.write(fd, p["data"].encode("utf-8"))
        os.close(fd)
    elif action == "remove_file_if":
        try:
            with open(p["path"], "rb") as f:
                data = f.read()
        except OSError:
            return
        if data == p["data"].encode("utf-8"):
            os.remove(p["path"])
    elif action == "append_file":
        with open(p["path"], "ab") as f:
            f.write(p["data"].encode("utf-8"))
    elif action == "git":
        for cmd in p["commands"]:
            subprocess.run([REAL] + cmd, cwd=p["cwd"], env=CONF["env"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)


matching = [r for r in CONF["rules"] if r["sub"] == sub and r.get("nth", 0) in (0, nth)]
for r in matching:
    if r.get("when") == "before":
        act(r)
after = [r for r in matching if r.get("when") == "after"]
if not after:
    os.execv(REAL, [REAL] + argv)
rc = subprocess.call([REAL] + argv)
for r in after:
    if r.get("only_if_rc") is None or r.get("only_if_rc") == rc:
        act(r)
sys.exit(rc)
'''


AUDIT_SITECUSTOMIZE = r'''
import os as _os
_LOG = _os.environ.get("EG_TEST_AUDIT_LOG")
if _LOG:
    import json as _json
    import sys as _sys

    def _s(x):
        try:
            x = _os.fspath(x)
        except TypeError:
            return None
        if isinstance(x, bytes):
            x = x.decode("utf-8", "replace")
        return x if isinstance(x, str) else None

    def _record(event, detail):
        try:
            with open(_LOG, "a") as f:
                f.write(_json.dumps({"pid": _os.getpid(), "event": event,
                                     "detail": detail}) + "\n")
        except Exception:
            pass

    def _git_lock(n):
        n = n.replace(_os.sep, "/")
        return n.endswith(".lock") and ("/.git/" in n or n.startswith(".git/")
                                        or _os.path.basename(n) == "index.lock")

    def _hook(event, args):
        if event in ("os.remove", "os.rename", "os.rmdir", "os.truncate",
                     "shutil.rmtree", "shutil.move"):
            names = [n for n in (_s(a) for a in args) if n]
            if any(_git_lock(n) for n in names[:1]):
                _record(event, names)
            elif event in ("shutil.rmtree", "os.rmdir") and any(
                    _os.path.basename(n.rstrip("/")) == ".git" for n in names):
                _record(event, names)
        elif event == "subprocess.Popen":
            try:
                argv = [_s(a) or "" for a in (args[1] if not isinstance(args[1], (str, bytes))
                                               else [args[1]])]
            except Exception:
                argv = []
            exe = _os.path.basename(_s(args[0]) or (argv[0] if argv else ""))
            if exe in ("rm", "unlink", "mv", "find") and any(".lock" in a for a in argv):
                _record(event, argv)

    _sys.addaudithook(_hook)
    _record("audit-start", [])
'''


def implementation_sources():
    """Python files of the implementation: scripts/*.py not present at the base commit."""
    baseline = None
    if REAL_GIT and os.path.isdir(os.path.join(REPO_ROOT, '.git')):
        env = dict((k, v) for k, v in os.environ.items() if not k.startswith('GIT_'))
        proc = subprocess.run([REAL_GIT, 'ls-tree', '-r', '--name-only', BASE_COMMIT,
                               '--', 'scripts'], cwd=REPO_ROOT, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if proc.returncode == 0:
            baseline = set(proc.stdout.decode('utf-8').split())
    if baseline is None:
        baseline = set(BASELINE_SCRIPTS)
    found = []
    scripts = os.path.join(REPO_ROOT, 'scripts')
    for dirpath, dirnames, filenames in os.walk(scripts):
        dirnames[:] = [d for d in dirnames if d != '__pycache__']
        for name in filenames:
            if name.endswith('.py'):
                rel = os.path.relpath(os.path.join(dirpath, name), REPO_ROOT)
                if rel.replace(os.sep, '/') not in baseline:
                    found.append(rel)
    return sorted(found)


def parse_source(rel):
    with open(os.path.join(REPO_ROOT, rel), 'rb') as f:
        src = f.read()
    return src, ast.parse(src, filename=rel)


class EgTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.addCleanup(cleanup_live_processes)
        self.assertTrue(os.path.isfile(EG_PY), 'entry point missing: %s' % EG_PY)
        self.assertIsNotNone(REAL_GIT, 'git not found on PATH of the test runner')

    def fixture(self, **kw):
        return Fixture(self, **kw)

    # ---- generic output assertions -------------------------------------
    def assertExit(self, res, code):
        self.assertFalse(res.timed_out, 'eg did not finish in time\n' + res.describe())
        self.assertEqual(res.code, code, res.describe())

    def checkpoint_json(self, res):
        data = res.json()
        self.assertEqual(data.get('schema'), 'eg-checkpoint/v1', res.describe())
        return data

    def identity_json(self, res):
        data = res.json()
        self.assertEqual(data.get('schema'), 'eg-identity/v1', res.describe())
        return data

    def assertMessageNonEmpty(self, data, res):
        msg = data.get('message')
        self.assertIsInstance(msg, str, res.describe())
        self.assertTrue(msg.strip(), 'message must be non-empty\n' + res.describe())

    def assertNotCommittedOutput(self, res, given_paths, result):
        """C17: failure output of checkpoint."""
        data = self.checkpoint_json(res)
        self.assertEqual(data.get('result'), result, res.describe())
        self.assertMessageNonEmpty(data, res)
        paths = data.get('paths')
        self.assertIsInstance(paths, list, res.describe())
        self.assertEqual(sorted(p.get('path') for p in paths), sorted(given_paths),
                         res.describe())
        for item in paths:
            self.assertEqual(item.get('status'), 'not_committed', res.describe())
            self.assertIn('blob', item, res.describe())
            self.assertIn('sha256', item, res.describe())
            self.assertIsNone(item.get('blob'), res.describe())
            self.assertIsNone(item.get('sha256'), res.describe())
        return data

    def assertRefused(self, res, given_paths):
        self.assertExit(res, 1)
        return self.assertNotCommittedOutput(res, given_paths, 'refused')

    def assertUsageError(self, res, given_paths=None):
        self.assertExit(res, 2)
        data = self.checkpoint_json(res)
        self.assertEqual(data.get('result'), 'error', res.describe())
        self.assertIsNone(data.get('commit'), res.describe())
        self.assertMessageNonEmpty(data, res)
        if given_paths is not None:
            self.assertNotCommittedOutput(res, given_paths, 'error')
        return data

    def assertCommitted(self, res, fx, committed, unchanged=(), pre_head=None,
                        kind=None, branch='eg/v2'):
        """C12 success output, with identities read back from the commit."""
        self.assertExit(res, 0)
        data = self.checkpoint_json(res)
        self.assertEqual(data.get('result'), 'committed', res.describe())
        commit = data.get('commit')
        self.assertIsInstance(commit, str, res.describe())
        self.assertRegex(commit, HEX40)
        self.assertEqual(fx.rev(commit + '^{commit}'), commit)
        self.assertEqual(data.get('branch'), branch, res.describe())
        if kind is not None:
            self.assertEqual(data.get('kind'), kind, res.describe())
        self.assertEqual(fx.changed_paths(commit), set(committed),
                         'commit %s must change exactly the changed listed paths' % commit)
        by_path = {}
        for item in data.get('paths') or []:
            by_path[item.get('path')] = item
        self.assertEqual(sorted(by_path), sorted(list(committed) + list(unchanged)),
                         res.describe())
        for rel in committed:
            item = by_path[rel]
            self.assertEqual(item.get('status'), 'committed', res.describe())
            self.assertEqual(item.get('blob'), fx.blob(commit, rel), res.describe())
            self.assertEqual(item.get('sha256'), sha256(fx.show(commit, rel)), res.describe())
        base = pre_head or fx.parents(commit)[0]
        for rel in unchanged:
            item = by_path[rel]
            self.assertEqual(item.get('status'), 'unchanged', res.describe())
            self.assertEqual(item.get('blob'), fx.blob(base, rel), res.describe())
            self.assertEqual(item.get('sha256'), sha256(fx.show(base, rel)), res.describe())
        return data
