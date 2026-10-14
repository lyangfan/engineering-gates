"""EG-S1 fault-injection acceptance tests (strict tier): AC11, AC12, AC14, AC15.

Faults are injected with repository hooks, a `git` wrapper placed first on
PATH, signals and lock files. Every run has its own time limit; processes
started by a test are killed during cleanup.
"""

import ast
import os
import signal
import time
import unittest

from . import support
from .support import EgTestCase, RUN_ID, process_alive, read_jsonl, sha256

LOCK_CONTENT = 'held by the EG-S1 acceptance test\n'


class AC11FailureRecovery(EgTestCase):

    def test_ac11_failing_pre_commit_hook_refused_and_restored(self):
        # eg:ac EG-S1-AC11
        for case in ('tracked-file', 'new-file'):
            with self.subTest(case=case):
                fx = self.fixture()
                marker = os.path.join(fx.aux, 'hook-ran')
                fx.install_hook('pre-commit', '#!/bin/sh\n: > "%s"\nexit 1\n' % marker)
                rel = 'a.txt' if case == 'tracked-file' else 'docs/new.md'
                if case == 'tracked-file':
                    fx.append(rel, 'more\n')
                else:
                    fx.write(rel, 'new\n')
                pre_head = fx.head()
                before = fx.path_state(rel)
                res = fx.checkpoint('--kind', 'record', '--path', rel)
                self.assertRefused(res, [rel])
                self.assertTrue(os.path.exists(marker), 'the pre-commit hook was not run')
                # EG-S1-AC11-W1: retrying with --no-verify moves HEAD.
                self.assertEqual(fx.head(), pre_head)
                # EG-S1-AC11-W2: the listed path stays staged without restoration.
                self.assertEqual(fx.path_state(rel), before)

    def test_ac11_killed_between_add_and_commit(self):
        # eg:ac EG-S1-AC11
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        pre_head = fx.head()
        pre_entry = fx.index_entry('a.txt')
        bin_dir, log = fx.git_wrapper([
            {'sub': 'add', 'nth': 1, 'when': 'after', 'action': 'kill_parent'}])
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', path_prefix=[bin_dir])
        self.assertFalse(res.timed_out, res.describe())
        self.assertEqual(res.code, -signal.SIGKILL,
                         'eg should have been killed right after `git add`\n' + res.describe())
        self.assertEqual(fx.head(), pre_head)
        self.assertNotEqual(fx.index_entry('a.txt'), pre_entry, 'injection precondition')
        staged = fx.index_entry('a.txt')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        data = self.assertRefused(res, ['a.txt'])
        self.assertIn('git reset -q -- a.txt', data['message'], res.describe())
        self.assertEqual(fx.head(), pre_head)
        self.assertEqual(fx.index_entry('a.txt'), staged)

    def test_ac11_lock_held_after_add_reports_staged_paths(self):
        # eg:ac EG-S1-AC11
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        pre_head = fx.head()
        pre_entry = fx.index_entry('a.txt')
        lock = fx.path('.git/index.lock')
        bin_dir, log = fx.git_wrapper([
            {'sub': 'add', 'nth': 1, 'when': 'after', 'action': 'create_file',
             'args': {'path': lock, 'data': LOCK_CONTENT}}])
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', path_prefix=[bin_dir],
                            timeout=30)
        self.assertExit(res, 1)
        data = self.assertNotCommittedOutput(res, ['a.txt'], 'error')
        self.assertIsNone(data.get('commit'))
        self.assertEqual(fx.head(), pre_head)
        self.assertNotEqual(fx.index_entry('a.txt'), pre_entry, 'a.txt is still staged')
        self.assertIn('a.txt', data['message'])
        self.assertIn('git reset -q -- a.txt', data['message'], res.describe())
        # EG-S1-AC11-W3: deleting the lock to restore fails these two checks.
        self.assertTrue(os.path.exists(lock), 'index.lock was removed')
        with open(lock) as f:
            self.assertEqual(f.read(), LOCK_CONTENT)


class AC12CommitVerification(EgTestCase):

    def test_ac12_worktree_changed_after_commit_before_read_back(self):
        # eg:ac EG-S1-AC12
        fx = self.fixture()
        fx.write('a.txt', 'committed bytes\n')
        bin_dir, log = fx.git_wrapper([
            {'sub': 'commit', 'nth': 0, 'when': 'after', 'only_if_rc': 0,
             'action': 'append_file', 'args': {'path': fx.path('a.txt'),
                                               'data': 'edited after commit\n'}}])
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', path_prefix=[bin_dir])
        data = self.assertCommitted(res, fx, ['a.txt'])
        item = [p for p in data['paths'] if p['path'] == 'a.txt'][0]
        self.assertEqual(fx.read('a.txt'), b'committed bytes\nedited after commit\n',
                         'injection precondition')
        # EG-S1-AC12-W1: hashing the working file gives the edited bytes.
        self.assertEqual(item['sha256'], sha256(b'committed bytes\n'))
        self.assertNotEqual(item['sha256'], sha256(fx.read('a.txt')))

    def test_ac12_post_commit_hook_commits_again(self):
        # eg:ac EG-S1-AC12
        fx = self.fixture()
        fx.append('a.txt', 'mine\n')
        pre_head = fx.head()
        fx.install_hook('post-commit', (
            '#!/bin/sh\n'
            '# recursion guard: the commit made below must not re-trigger this hook\n'
            '[ -n "$EG_S1_TEST_IN_HOOK" ] && exit 0\n'
            'EG_S1_TEST_IN_HOOK=1; export EG_S1_TEST_IN_HOOK\n'
            'unset GIT_INDEX_FILE\n'
            'echo concurrent >> other.txt\n'
            'git add -- other.txt && git commit -q --no-verify -m concurrent -- other.txt\n'))
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        data = self.assertCommitted(res, fx, ['a.txt'])
        head = fx.head()
        self.assertEqual(fx.subject(head), 'concurrent', 'injection precondition')
        # EG-S1-AC12-W2: reading HEAD after the commit reports the hook's commit.
        self.assertNotEqual(data['commit'], head)
        self.assertEqual(fx.parents(head), [data['commit']])
        self.assertEqual(fx.parents(data['commit']), [pre_head])
        self.assertRegex(fx.trailer(data['commit'], 'EG-Run'), RUN_ID)

    def test_ac12_concurrent_commit_before_own_commit(self):
        # eg:ac EG-S1-AC12
        fx = self.fixture()
        fx.append('a.txt', 'mine\n')
        fx.append('other.txt', 'concurrent\n')
        pre_head = fx.head()
        bin_dir, log = fx.git_wrapper([
            {'sub': 'add', 'nth': 1, 'when': 'after', 'action': 'git',
             'args': {'cwd': fx.root, 'commands': [
                 ['add', '--', 'other.txt'],
                 ['-c', 'user.name=Other', '-c', 'user.email=other@example.invalid',
                  'commit', '-q', '--no-verify', '-m', 'concurrent', '--only', '--',
                  'other.txt']]}}])
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', path_prefix=[bin_dir])
        # EG-S1-AC12-W3: requiring parent == recorded HEAD rejects this commit.
        data = self.assertCommitted(res, fx, ['a.txt'])
        parent = fx.parents(data['commit'])
        self.assertEqual(len(parent), 1)
        self.assertEqual(fx.subject(parent[0]), 'concurrent', 'injection precondition')
        self.assertEqual(fx.parents(parent[0]), [pre_head])
        self.assertEqual(data['commit'], fx.head())

    def test_ac12_pre_commit_hook_alters_committed_paths(self):
        # eg:ac EG-S1-AC12
        fx = self.fixture()
        fx.append('a.txt', 'mine\n')
        pre_head = fx.head()
        fx.install_hook('pre-commit', (
            '#!/bin/sh\n'
            'echo injected > injected.txt\n'
            'git add -- injected.txt\n'))
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        self.assertExit(res, 1)
        data = self.assertNotCommittedOutput(res, ['a.txt'], 'error')
        head = fx.head()
        self.assertNotEqual(head, pre_head, 'injection precondition: a commit was made')
        self.assertEqual(fx.changed_paths(head), {'a.txt', 'injected.txt'})
        self.assertEqual(data.get('commit'), head)
        self.assertIn(head[:7], data['message'], res.describe())
        # The produced commit is not rewritten.
        self.assertEqual(fx.parents(head), [pre_head])


def _is_string_expr(node):
    """Whether an expression statically evaluates to a str (a command line)."""
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str)
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            return _is_string_expr(node.left) or _is_string_expr(node.right)
        if isinstance(node.op, ast.Mod):
            return _is_string_expr(node.left)
        return False
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in ('format', 'join'):
            return _is_string_expr(node.func.value)
    return False


def _sources_or_fail(testcase):
    sources = support.implementation_sources()
    testcase.assertIn(os.path.join('scripts', 'eg.py'), sources)
    return sources


class AC14Timeout(EgTestCase):

    def test_ac14_timeout_terminates_hook_process_group(self):
        # eg:ac EG-S1-AC14
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        pre_head = fx.head()
        pre_entry = fx.index_entry('a.txt')
        hook_pid = os.path.join(fx.aux, 'hook.pid')
        child_pid = os.path.join(fx.aux, 'child.pid')
        fx.install_hook('pre-commit', (
            '#!/bin/sh\n'
            'echo $$ > "%s"\n'
            'sleep 30 </dev/null >/dev/null 2>&1 &\n'
            'echo $! > "%s"\n'
            'sleep 6\n') % (hook_pid, child_pid))
        self.addCleanup(self._kill_pids, hook_pid, child_pid)
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                            env_extra={'EG_GIT_TIMEOUT_SECONDS': '1'}, timeout=40)
        # EG-S1-AC14-W1: without a timeout the hook finishes after 6 s and the
        # commit is made (HEAD check below); a hang hits the 40 s run limit.
        self.assertExit(res, 1)
        data = self.assertNotCommittedOutput(res, ['a.txt'], 'error')
        self.assertIsNone(data.get('commit'))
        self.assertEqual(fx.head(), pre_head)
        # EG-S1-AC14-W2: SIGKILL to git alone leaves index.lock and keeps the
        # hook alive, so the lock, restore and process checks below fail.
        self.assertFalse(os.path.exists(fx.path('.git/index.lock')), 'index.lock left behind')
        self.assertEqual(fx.index_entry('a.txt'), pre_entry)
        pids = []
        for p in (hook_pid, child_pid):
            self.assertTrue(os.path.exists(p), 'hook did not start: %s missing' % p)
            with open(p) as f:
                pids.append(int(f.read().strip()))
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and any(process_alive(pid) for pid in pids):
            time.sleep(0.05)
        for pid in pids:
            self.assertFalse(process_alive(pid), 'process %d still alive' % pid)

    def _kill_pids(self, *files):
        for p in files:
            try:
                with open(p) as f:
                    pid = int(f.read().strip())
            except (OSError, ValueError):
                continue
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass

    def test_ac14_invalid_timeout_values_exit_2(self):
        # eg:ac EG-S1-AC14
        for value in ('abc', '301', '0', '-5', '1.5'):
            with self.subTest(value=value):
                fx = self.fixture()
                fx.append('a.txt', 'more\n')
                before = fx.snapshot()
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                                    env_extra={'EG_GIT_TIMEOUT_SECONDS': value})
                self.assertUsageError(res, given_paths=['a.txt'])
                self.assertEqual(fx.snapshot(), before)

    def test_ac14_valid_timeout_values_accepted(self):
        # eg:ac EG-S1-AC14
        for value in ('300', '30'):
            with self.subTest(value=value):
                fx = self.fixture()
                fx.append('a.txt', 'more\n')
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                                    env_extra={'EG_GIT_TIMEOUT_SECONDS': value})
                self.assertCommitted(res, fx, ['a.txt'])

    def test_ac14_git_runs_in_its_own_process_group(self):
        # eg:ac EG-S1-AC14
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        bin_dir, log = fx.git_wrapper()
        proc = fx.start('checkpoint', ['--kind', 'record', '--path', 'a.txt'],
                        path_prefix=[bin_dir])
        # eg is started as a session leader, so its process group id is its pid.
        eg_pgid = proc.pid
        res = proc.finish()
        self.assertCommitted(res, fx, ['a.txt'])
        calls = read_jsonl(log)
        self.assertTrue(calls, 'git was not found through PATH')
        # C14 (supports EG-S1-AC14-W2): each git call gets its own process group,
        # which is what lets a timeout signal reach hooks and their children.
        for call in calls:
            self.assertNotEqual(call['pgid'], eg_pgid,
                                'git shares the process group of eg: %r' % call['argv'])

    def test_ac14_source_never_uses_a_shell(self):
        # eg:ac EG-S1-AC14
        string_cmd_funcs = ('run', 'Popen', 'call', 'check_call', 'check_output')
        for rel in _sources_or_fail(self):
            src, tree = support.parse_source(rel)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else (
                    func.id if isinstance(func, ast.Name) else None)
                owner = func.value.id if (isinstance(func, ast.Attribute)
                                          and isinstance(func.value, ast.Name)) else None
                where = '%s:%d' % (rel, node.lineno)
                # EG-S1-AC14-W3: shell=True (or a computed shell flag) is rejected.
                for kw in node.keywords:
                    if kw.arg == 'shell':
                        self.assertTrue(isinstance(kw.value, ast.Constant)
                                        and kw.value.value is False, where)
                self.assertFalse(owner == 'os' and name in ('system', 'popen'), where)
                self.assertFalse(name in ('getoutput', 'getstatusoutput'), where)
                if name in string_cmd_funcs and node.args:
                    self.assertFalse(_is_string_expr(node.args[0]),
                                     '%s: command passed as a string' % where)

    def test_ac14_paths_with_spaces_and_quotes(self):
        # eg:ac EG-S1-AC14
        fx = self.fixture()
        names = ['dir with space/it\'s "quoted".txt', 'a b.txt']
        for i, rel in enumerate(names):
            fx.write(rel, 'content %d\n' % i)
        fx.write('a.txt', 'changed\n')
        args = ['--kind', 'record']
        for rel in names + ['a.txt']:
            args += ['--path', rel]
        res = fx.checkpoint(*args)
        data = self.assertCommitted(res, fx, names + ['a.txt'])
        for i, rel in enumerate(names):
            self.assertEqual(fx.show(data['commit'], rel), b'content %d\n' % i)


class AC15LockRetry(EgTestCase):
    # the 20-fold concurrent repetition is in test_concurrency.py

    def test_ac15_held_lock_bounded_retries(self):
        # eg:ac EG-S1-AC15
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        lock = fx.path('.git/index.lock')
        with open(lock, 'w') as f:
            f.write(LOCK_CONTENT)
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', timeout=20)
        # EG-S1-AC15-W2: retrying forever exceeds the 6 s budget (and the 20 s limit).
        self.assertFalse(res.timed_out, res.describe())
        self.assertLessEqual(res.elapsed, 6.0, res.describe())
        self.assertExit(res, 1)
        data = self.assertNotCommittedOutput(res, ['a.txt'], 'error')
        self.assertIsNone(data.get('commit'))
        # EG-S1-AC15-W1: deleting the lock fails these checks.
        self.assertTrue(os.path.exists(lock), 'index.lock was removed')
        with open(lock) as f:
            self.assertEqual(f.read(), LOCK_CONTENT)
        self.assertEqual(fx.snapshot(), before)

    def test_ac15_lock_released_before_second_retry(self):
        # eg:ac EG-S1-AC15
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        lock = fx.path('.git/index.lock')
        with open(lock, 'w') as f:
            f.write(LOCK_CONTENT)
        bin_dir, log = fx.git_wrapper([
            {'sub': 'add', 'nth': 2, 'when': 'after', 'action': 'remove_file_if',
             'args': {'path': lock, 'data': LOCK_CONTENT}}])
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', path_prefix=[bin_dir],
                            timeout=20)
        # EG-S1-AC15-W3: failing on the first lock error never reaches the
        # attempt after the lock is gone.
        self.assertCommitted(res, fx, ['a.txt'])
        adds = [c for c in read_jsonl(log) if c['sub'] == 'add']
        self.assertGreaterEqual(len(adds), 3, 'expected the original attempt and two retries')
        self.assertFalse(os.path.exists(lock))


if __name__ == '__main__':
    unittest.main()
