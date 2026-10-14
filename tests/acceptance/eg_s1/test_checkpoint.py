"""EG-S1 acceptance tests for `eg.py checkpoint` (AC01-AC10, AC12, AC17).

Fault-injection scenarios live in test_faults.py, identity in test_identity.py,
the AC15 concurrency repetition in test_concurrency.py and AC16 in
test_environment.py.
"""

import os
import shutil
import tempfile
import unittest

from . import support
from .support import (EgTestCase, FIXTURE_EMAIL, HEX40, IDENTITY_ENV_VARS,
                      IDENTITY_OVERRIDE_KEYS, RUN_ID, read_jsonl, sha256)


class AC01OutputChannels(EgTestCase):

    def test_ac01_checkpoint_stdout_is_one_json_object(self):
        # eg:ac EG-S1-AC01
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'candidate', '--path', 'a.txt')
        self.assertExit(res, 0)
        # EG-S1-AC01-W1: a summary also written to stdout makes json.loads fail here.
        data = res.json()
        self.assertEqual(data.get('schema'), 'eg-checkpoint/v1')
        # C01: the readable summary goes to stderr.
        self.assertTrue(res.stderr.strip(), 'summary expected on stderr\n' + res.describe())

    def test_ac01_failure_stdout_is_one_json_object(self):
        # eg:ac EG-S1-AC01
        fx = self.fixture(branch='main')
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'candidate', '--path', 'a.txt')
        self.assertExit(res, 1)
        # EG-S1-AC01-W1
        self.assertEqual(res.json().get('schema'), 'eg-checkpoint/v1')

    def test_ac01_identity_stdout_is_one_json_object(self):
        # eg:ac EG-S1-AC01
        fx = self.fixture()
        res = fx.identity('--path', 'a.txt')
        self.assertExit(res, 0)
        # EG-S1-AC01-W1
        data = res.json()
        self.assertEqual(data.get('schema'), 'eg-identity/v1')
        self.assertTrue(res.stderr.strip(), 'summary expected on stderr\n' + res.describe())

    def test_ac01_no_pycache_after_running(self):
        # eg:ac EG-S1-AC01
        # Run a pristine copy of the project so that bytecode left by earlier
        # runs cannot hide (or fake) the result; the child environment has no
        # PYTHONDONTWRITEBYTECODE and no -B flag.
        copy_base = os.path.realpath(tempfile.mkdtemp(prefix='eg-s1-copy-'))
        self.addCleanup(shutil.rmtree, copy_base, True)
        copy_root = os.path.join(copy_base, 'project')
        shutil.copytree(support.REPO_ROOT, copy_root, symlinks=True,
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
        eg_copy = os.path.join(copy_root, 'scripts', 'eg.py')
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'candidate', '--path', 'a.txt', eg_py=eg_copy)
        self.assertExit(res, 0)
        res = fx.identity('--path', 'a.txt', eg_py=eg_copy)
        self.assertExit(res, 0)
        for top in (copy_root, fx.root):
            for dirpath, dirnames, filenames in os.walk(top):
                if '.git' in dirnames:
                    dirnames.remove('.git')
                self.assertNotIn('__pycache__', dirnames, 'found __pycache__ in ' + dirpath)
                self.assertFalse([n for n in filenames if n.endswith('.pyc')], dirpath)


class AC02ExitCodes(EgTestCase):

    def test_ac02_missing_kind_exit_2(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--path', 'a.txt')
        self.assertUsageError(res)
        self.assertEqual(fx.snapshot(), before)

    def test_ac02_unknown_kind_exit_2(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'other', '--path', 'a.txt')
        self.assertUsageError(res)
        self.assertEqual(fx.snapshot(), before)

    def test_ac02_not_a_git_repository_exit_2(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture()
        outside = os.path.join(fx.base, 'not-a-repo')
        os.makedirs(outside)
        with open(os.path.join(outside, 'a.txt'), 'w') as f:
            f.write('x\n')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', cwd=outside)
        # EG-S1-AC02-W2: exiting with 1 outside a repository fails here.
        self.assertUsageError(res)

    def test_ac02_git_not_on_path_exit_2(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        empty_bin = os.path.join(fx.aux, 'empty-bin')
        os.makedirs(empty_bin)
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                            env_extra={'PATH': empty_bin})
        self.assertUsageError(res)
        self.assertEqual(fx.snapshot(), before)

    def test_ac02_main_branch_refused_exit_1(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture(branch='main')
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        # EG-S1-AC02-W1: refusing a non-eg branch with exit 2 fails here.
        self.assertExit(res, 1)
        self.assertEqual(self.checkpoint_json(res).get('result'), 'refused')

    def test_ac02_path_checked_before_branch(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture(branch='main')
        fx.append('a.txt', 'more\n')
        absolute = fx.path('a.txt')
        res = fx.checkpoint('--kind', 'record', '--path', absolute)
        data = self.assertRefused(res, [absolute])
        # EG-S1-AC02-W3: checking the branch first yields a branch message
        # that does not point at the offending path.
        self.assertIn(absolute, data['message'], res.describe())

    def test_ac02_success_exit_0(self):
        # eg:ac EG-S1-AC02
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        self.assertCommitted(res, fx, ['a.txt'])


class AC03Paths(EgTestCase):

    BAD_PATHS = (
        ('typo', 'docs/spce.md'),
        ('absolute', None),
        ('dotdot', 'sub/../a.txt'),
        ('dot-slash', './a.txt'),
        ('dot-segment', 'sub/./c.txt'),
        ('trailing-slash', 'a.txt/'),
        ('double-slash', 'sub//c.txt'),
        ('dot-git', '.git/config'),
        ('directory', 'sub'),
        ('symlink', 'link.txt'),
    )

    def test_ac03_invalid_paths_refused_without_changes(self):
        # eg:ac EG-S1-AC03
        for name, bad in self.BAD_PATHS:
            with self.subTest(case=name):
                fx = self.fixture()
                os.symlink('a.txt', fx.path('link.txt'))
                if bad is None:
                    bad = fx.path('a.txt')
                fx.append('a.txt', 'more\n')
                fx.append('b.txt', 'more\n')
                fx.append('sub/c.txt', 'more\n')
                before = fx.snapshot()
                # A valid changed path is listed too, so silently skipping the
                # bad path would produce a commit.
                res = fx.checkpoint('--kind', 'record', '--path', bad, '--path', 'b.txt')
                data = self.assertRefused(res, [bad, 'b.txt'])
                self.assertIn(bad, data['message'], res.describe())
                # EG-S1-AC03-W1 (directory accepted and its files committed) and
                # EG-S1-AC03-W2 (symlink followed and target committed) both
                # change HEAD/index, which this snapshot comparison rejects.
                self.assertEqual(fx.snapshot(), before)

    def test_ac03_duplicate_path_refused(self):
        # eg:ac EG-S1-AC03
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        fx.append('b.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', '--path', 'b.txt',
                            '--path', 'a.txt')
        data = self.assertRefused(res, ['a.txt', 'b.txt', 'a.txt'])
        self.assertIn('a.txt', data['message'])
        self.assertEqual(fx.snapshot(), before)

    def test_ac03_missing_path_exit_2(self):
        # eg:ac EG-S1-AC03
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record')
        self.assertUsageError(res, given_paths=[])
        self.assertEqual(fx.snapshot(), before)

    def test_ac03_subdirectory_same_as_root(self):
        # eg:ac EG-S1-AC03
        results = []
        for cwd_rel in ('', 'sub'):
            fx = self.fixture()
            fx.append('a.txt', 'root change\n')
            fx.append('sub/a.txt', 'sub change\n')
            sub_before = fx.path_state('sub/a.txt')
            res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', '--path', 'b.txt',
                                cwd=os.path.join(fx.root, cwd_rel))
            # EG-S1-AC03-W3: resolving against the cwd commits sub/a.txt (wrong
            # file) or reports b.txt missing when run from sub/.
            data = self.assertCommitted(res, fx, ['a.txt'], unchanged=['b.txt'])
            self.assertEqual(fx.path_state('sub/a.txt'), sub_before)
            results.append((res.code, data['result'], data['branch'], data['kind'],
                            sorted((p['path'], p['status'], p['blob'], p['sha256'])
                                   for p in data['paths'])))
        self.assertEqual(results[0], results[1])


class AC04Branch(EgTestCase):

    def test_ac04_non_eg_branches_refused(self):
        # eg:ac EG-S1-AC04
        for case in ('main', 'feature/x', 'detached'):
            with self.subTest(case=case):
                if case == 'detached':
                    fx = self.fixture()
                    fx.git('checkout', '-q', '--detach')
                else:
                    fx = self.fixture(branch=case)
                fx.append('a.txt', 'more\n')
                fx.git('add', '--', 'a.txt')
                fx.append('b.txt', 'more\n')
                before = fx.snapshot()
                res = fx.checkpoint('--kind', 'record', '--path', 'b.txt')
                # EG-S1-AC04-W1 (only main refused) fails for feature/x;
                # EG-S1-AC04-W2 (detached HEAD commits) fails for detached.
                self.assertRefused(res, ['b.txt'])
                self.assertEqual(fx.snapshot(), before)

    def test_ac04_unborn_eg_branch_refused(self):
        # eg:ac EG-S1-AC04
        fx = self.fixture(init_branch='eg/x', branch='eg/x', initial_commit=False)
        fx.write('first.txt', 'first\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'first.txt')
        self.assertRefused(res, ['first.txt'])
        self.assertIsNone(fx.head())
        self.assertEqual(fx.snapshot(), before)

    def test_ac04_eg_branch_commits(self):
        # eg:ac EG-S1-AC04
        fx = self.fixture(branch='eg/v2')
        fx.append('a.txt', 'more\n')
        pre = fx.head()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        data = self.assertCommitted(res, fx, ['a.txt'], branch='eg/v2')
        self.assertEqual(fx.rev('refs/heads/eg/v2'), data['commit'])
        self.assertEqual(fx.parents(data['commit']), [pre])


class AC05Identity(EgTestCase):

    def test_ac05_unconfigured_identity_refused(self):
        # eg:ac EG-S1-AC05
        fx = self.fixture(identity=False)
        fx.append('a.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                            env_extra={'GIT_CONFIG_GLOBAL': os.devnull,
                                       'GIT_CONFIG_SYSTEM': os.devnull})
        # EG-S1-AC05-W1 (placeholder identity) and EG-S1-AC05-W2 (relying on
        # git, which auto-detects an identity, F-15) both produce a commit.
        data = self.assertRefused(res, ['a.txt'])
        self.assertEqual(fx.snapshot(), before)
        self.assertTrue('user.name' in data['message'] or 'user.email' in data['message'],
                        res.describe())

    def test_ac05_single_missing_identity_key_named(self):
        # eg:ac EG-S1-AC05
        for present, missing, value in (('user.email', 'user.name', FIXTURE_EMAIL),
                                        ('user.name', 'user.email', support.FIXTURE_NAME)):
            with self.subTest(missing=missing):
                fx = self.fixture(identity=False)
                fx.git('config', present, value)
                fx.append('a.txt', 'more\n')
                before = fx.snapshot()
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
                # EG-S1-AC05-W2: git would infer the missing half and commit.
                data = self.assertRefused(res, ['a.txt'])
                self.assertIn(missing, data['message'], res.describe())
                self.assertEqual(fx.snapshot(), before)

    def test_ac05_empty_user_name_refused(self):
        # eg:ac EG-S1-AC05
        fx = self.fixture()
        fx.git('config', 'user.name', '')
        fx.append('a.txt', 'more\n')
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        data = self.assertRefused(res, ['a.txt'])
        self.assertIn('user.name', data['message'], res.describe())
        self.assertEqual(fx.snapshot(), before)

    def test_ac05_identity_environment_variables_refused(self):
        # eg:ac EG-S1-AC05
        for var in IDENTITY_ENV_VARS:
            with self.subTest(var=var):
                fx = self.fixture()
                fx.append('a.txt', 'more\n')
                before = fx.snapshot()
                value = 'env@example.invalid' if var.endswith('EMAIL') else 'Env Override'
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt',
                                    env_extra={var: value})
                # EG-S1-AC05-W3: ignoring the variable commits with its identity (F-18).
                data = self.assertRefused(res, ['a.txt'])
                self.assertIn(var, data['message'], res.describe())
                self.assertEqual(fx.snapshot(), before)

    def test_ac05_identity_override_config_refused(self):
        # eg:ac EG-S1-AC05
        cases = [(key, 'repo') for key in IDENTITY_OVERRIDE_KEYS] + [('author.name', 'global')]
        for key, scope in cases:
            with self.subTest(key=key, scope=scope):
                fx = self.fixture()
                value = 'cfg@example.invalid' if key.endswith('email') else 'Config Override'
                if scope == 'repo':
                    fx.git('config', key, value)
                else:
                    fx.git('config', '--file', fx.global_config, key, value)
                fx.append('a.txt', 'more\n')
                before = fx.snapshot()
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
                # EG-S1-AC05-W4: checking only user.* commits with author.name (F-20).
                data = self.assertRefused(res, ['a.txt'])
                self.assertIn(key, data['message'], res.describe())
                self.assertEqual(fx.snapshot(), before)



class AC06StagedContent(EgTestCase):

    def test_ac06_user_staged_version_preserved(self):
        # eg:ac EG-S1-AC06
        cases = ('staged-differs-from-worktree', 'staged-equals-worktree', 'staged-new-file')
        for case in cases:
            with self.subTest(case=case):
                fx = self.fixture()
                if case == 'staged-differs-from-worktree':
                    rel = 'a.txt'
                    fx.stage(rel, 'user staged version\n')
                    fx.write(rel, 'working tree version\n')
                elif case == 'staged-equals-worktree':
                    rel = 'a.txt'
                    fx.stage(rel, 'user staged version\n')
                else:
                    rel = 'docs/new.md'
                    fx.stage(rel, 'new staged\n')
                    fx.write(rel, 'new working\n')
                staged_before = fx.index_entry(rel)
                before = fx.snapshot()
                res = fx.checkpoint('--kind', 'record', '--path', rel)
                # EG-S1-AC06-W1: `add` overwrites the staged version and commits.
                self.assertRefused(res, [rel])
                self.assertEqual(fx.index_entry(rel), staged_before)
                self.assertEqual(fx.snapshot(), before)


class AC07Changes(EgTestCase):

    def test_ac07_all_unchanged_refused(self):
        # eg:ac EG-S1-AC07
        fx = self.fixture()
        before = fx.snapshot()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', '--path', 'b.txt')
        # EG-S1-AC07-W1: an empty commit changes HEAD.
        self.assertRefused(res, ['a.txt', 'b.txt'])
        self.assertEqual(fx.snapshot(), before)

    def test_ac07_partially_unchanged_commits_changed_only(self):
        # eg:ac EG-S1-AC07
        fx = self.fixture()
        pre = fx.head()
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', '--path', 'b.txt')
        # EG-S1-AC07-W2: refusing as a whole fails the exit-0 assertion.
        self.assertCommitted(res, fx, ['a.txt'], unchanged=['b.txt'], pre_head=pre)

    def test_ac07_exec_bit_only_change_committed(self):
        # eg:ac EG-S1-AC07
        fx = self.fixture()
        self.assertEqual(fx.tree_mode('HEAD', 'script.sh'), '100644')
        os.chmod(fx.path('script.sh'), 0o755)
        res = fx.checkpoint('--kind', 'record', '--path', 'script.sh')
        # EG-S1-AC07-W3: comparing bytes only refuses with "no changes".
        data = self.assertCommitted(res, fx, ['script.sh'])
        self.assertEqual(fx.tree_mode(data['commit'], 'script.sh'), '100755')


class AC08CommitSteps(EgTestCase):

    def test_ac08_only_add_and_commit_are_written(self):
        # eg:ac EG-S1-AC08
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        fx.write('docs/new.md', 'brand new\n')
        fx.write('junk.txt', 'unrelated untracked\n')
        bin_dir, log = fx.git_wrapper()
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', '--path', 'docs/new.md',
                            path_prefix=[bin_dir])
        # EG-S1-AC08-W1: committing the untracked file without `add` fails (F-16).
        data = self.assertCommitted(res, fx, ['a.txt', 'docs/new.md'])
        self.assertEqual(fx.show(data['commit'], 'docs/new.md'), b'brand new\n')
        calls = read_jsonl(log)
        self.assertTrue(calls, 'git was not invoked through PATH')
        writes = [c for c in calls if support.is_write_invocation(c)]
        self.assertEqual([c['sub'] for c in writes], ['add', 'commit'],
                         'write invocations: %r' % [c['argv'] for c in writes])
        listed = {'a.txt', 'docs/new.md'}
        add_opts, add_paths = support.split_pathspec(support.args_after_subcommand(writes[0]))
        commit_opts, commit_paths = support.split_pathspec(
            support.args_after_subcommand(writes[1]))
        self.assertIn('--', writes[0]['rest'])
        self.assertEqual(set(add_paths), listed)
        self.assertIn('--', writes[1]['rest'])
        self.assertEqual(set(commit_paths), listed)
        self.assertIn('--only', commit_opts)
        self.assertTrue('-F' in commit_opts or any(o.startswith('-F') for o in commit_opts))
        # EG-S1-AC08-W2: `add -A` / `add .` / `commit -a` are rejected here.
        for opt in ('-A', '--all', '.', '-a', '-u', '--update'):
            self.assertNotIn(opt, add_opts + add_paths, writes[0]['argv'])
            self.assertNotIn(opt, commit_opts + commit_paths, writes[1]['argv'])
        for call in calls:
            self.assertNotIn('--no-verify', call['argv'])
            for i, a in enumerate(call['argv'][:-1]):
                if a == '-c':
                    self.assertFalse(call['argv'][i + 1].split('=')[0].lower() in (
                        'user.name', 'user.email', 'author.name', 'author.email',
                        'committer.name', 'committer.email'), call['argv'])
        self.assertNotIn('-n', commit_opts)
        self.assertEqual(fx.index_entry('junk.txt'), '')

    def test_ac08_new_untracked_file_committed(self):
        # eg:ac EG-S1-AC08
        fx = self.fixture()
        fx.write('docs/fresh.md', 'fresh\n')
        res = fx.checkpoint('--kind', 'spec-freeze', '--spec', 'EG-S1',
                            '--path', 'docs/fresh.md')
        # EG-S1-AC08-W1
        data = self.assertCommitted(res, fx, ['docs/fresh.md'], kind='spec-freeze')
        self.assertEqual(fx.show(data['commit'], 'docs/fresh.md'), b'fresh\n')


class AC09UnrelatedPaths(EgTestCase):

    UNRELATED = ('b.txt', 'sub/c.txt', 'notes.txt')

    def _prepare(self, fx):
        fx.stage('b.txt', 'bravo staged\n')
        fx.write('b.txt', 'bravo staged then edited\n')
        fx.append('sub/c.txt', 'unstaged edit\n')
        fx.write('notes.txt', 'untracked notes\n')
        fx.append('a.txt', 'listed change\n')
        return dict((rel, fx.path_state(rel)) for rel in self.UNRELATED)

    def test_ac09_unrelated_state_preserved(self):
        # eg:ac EG-S1-AC09
        for case in ('committed', 'branch-refused', 'hook-failed'):
            with self.subTest(case=case):
                fx = self.fixture(branch='main' if case == 'branch-refused' else 'eg/v2')
                if case == 'hook-failed':
                    fx.install_hook('pre-commit', '#!/bin/sh\nexit 1\n')
                before = self._prepare(fx)
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
                if case == 'committed':
                    # EG-S1-AC09-W1: committing without --only also commits b.txt.
                    self.assertCommitted(res, fx, ['a.txt'])
                else:
                    self.assertRefused(res, ['a.txt'])
                after = dict((rel, fx.path_state(rel)) for rel in self.UNRELATED)
                # EG-S1-AC09-W2: a path-less `git reset` drops the staged b.txt.
                self.assertEqual(after, before)


class AC10Message(EgTestCase):

    def test_ac10_message_format_and_trailers(self):
        # eg:ac EG-S1-AC10
        fx = self.fixture()
        fx.write('docs/spec.md', '# spec v0.4\n')
        res = fx.checkpoint('--kind', 'spec-freeze', '--spec', 'EG-S1', '--message',
                            'freeze v0.4', '--path', 'docs/spec.md')
        data = self.assertCommitted(res, fx, ['docs/spec.md'], kind='spec-freeze')
        self.assertEqual(data.get('spec'), 'EG-S1')
        commit = data['commit']
        # EG-S1-AC10-W1: without trailers the trailer queries return ''.
        self.assertEqual(fx.trailer(commit, 'EG-Kind'), 'spec-freeze')
        self.assertEqual(fx.trailer(commit, 'EG-Spec'), 'EG-S1')
        run_id = fx.trailer(commit, 'EG-Run')
        self.assertRegex(run_id, RUN_ID)
        lines = fx.message(commit).rstrip('\n').split('\n')
        self.assertEqual(lines, ['eg(spec-freeze): EG-S1 freeze v0.4', '',
                                 'EG-Kind: spec-freeze', 'EG-Spec: EG-S1',
                                 'EG-Run: ' + run_id])

    def test_ac10_defaults(self):
        # eg:ac EG-S1-AC10
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
        data = self.assertCommitted(res, fx, ['a.txt'], kind='record')
        commit = data['commit']
        run_id = fx.trailer(commit, 'EG-Run')
        self.assertRegex(run_id, RUN_ID)
        lines = fx.message(commit).rstrip('\n').split('\n')
        self.assertEqual(lines, ['eg(record): - checkpoint', '', 'EG-Kind: record',
                                 'EG-Spec: -', 'EG-Run: ' + run_id])

    def test_ac10_run_ids_differ(self):
        # eg:ac EG-S1-AC10
        run_ids = []
        # Two runs back to back in one repository ...
        fx = self.fixture()
        for i in range(2):
            fx.append('a.txt', 'change %d\n' % i)
            res = fx.checkpoint('--kind', 'record', '--path', 'a.txt')
            data = self.assertCommitted(res, fx, ['a.txt'])
            run_ids.append(fx.trailer(data['commit'], 'EG-Run'))
        # ... and identical inputs in two identical repositories.
        for i in range(2):
            fy = self.fixture()
            fy.append('a.txt', 'same change\n')
            res = fy.checkpoint('--kind', 'record', '--path', 'a.txt')
            data = self.assertCommitted(res, fy, ['a.txt'])
            run_ids.append(fy.trailer(data['commit'], 'EG-Run'))
        for run_id in run_ids:
            self.assertRegex(run_id, RUN_ID)
        # EG-S1-AC10-W4: a fixed, timestamp- or input-derived run id repeats.
        self.assertEqual(len(set(run_ids)), len(run_ids), run_ids)

    def test_ac10_invalid_arguments_exit_2(self):
        # eg:ac EG-S1-AC10
        cases = [
            # EG-S1-AC10-W2: any --kind accepted.
            ('kind-other', ['--kind', 'other']),
            ('kind-empty', ['--kind', '']),
            # EG-S1-AC10-W3: a newline lets a forged `EG-Kind:` line become a trailer.
            ('message-newline', ['--kind', 'record', '--message',
                                 'innocent\n\nEG-Kind: review']),
            ('message-cr', ['--kind', 'record', '--message', 'a\rb']),
            ('message-empty', ['--kind', 'record', '--message', '']),
            ('spec-space', ['--kind', 'record', '--spec', 'EG S1']),
            ('spec-empty', ['--kind', 'record', '--spec', '']),
            ('spec-slash', ['--kind', 'record', '--spec', 'EG/S1']),
            ('unknown-option', ['--kind', 'record', '--bogus']),
        ]
        for name, args in cases:
            with self.subTest(case=name):
                fx = self.fixture()
                fx.append('a.txt', 'more\n')
                before = fx.snapshot()
                res = fx.checkpoint(*(args + ['--path', 'a.txt']))
                self.assertUsageError(res, given_paths=['a.txt'])
                self.assertEqual(fx.snapshot(), before)


class AC12ReadBack(EgTestCase):
    # fault-injected cases are in test_faults.py

    def test_ac12_identities_read_back_from_commit(self):
        # eg:ac EG-S1-AC12
        fx = self.fixture()
        pre = fx.head()
        fx.write('a.txt', 'alpha v2\n')
        fx.write('docs/new.md', 'new doc\n')
        res = fx.checkpoint('--kind', 'candidate', '--path', 'a.txt', '--path', 'docs/new.md',
                            '--path', 'b.txt')
        data = self.assertCommitted(res, fx, ['a.txt', 'docs/new.md'], unchanged=['b.txt'],
                                    pre_head=pre)
        self.assertRegex(data['commit'], HEX40)
        for item in data['paths']:
            commit = data['commit'] if item['status'] == 'committed' else pre
            raw = fx.git('cat-file', 'blob', '%s:%s' % (commit, item['path'])).stdout
            self.assertEqual(item['sha256'], sha256(raw))


class AC17FailureOutput(EgTestCase):
    # EG-S1-AC17-W1: empty/text-only stdout fails checkpoint_json();
    # EG-S1-AC17-W2: filled-in sha256 fails the null checks in assertNotCommittedOutput().

    def test_ac17_branch_refusal_output(self):
        # eg:ac EG-S1-AC17
        fx = self.fixture(branch='main')
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'review', '--spec', 'EG-S1', '--path', 'a.txt',
                            '--path', 'b.txt')
        data = self.assertRefused(res, ['a.txt', 'b.txt'])
        self.assertIsNone(data.get('commit'))
        self.assertEqual(data.get('branch'), 'main')
        self.assertEqual(data.get('kind'), 'review')
        self.assertEqual(data.get('spec'), 'EG-S1')

    def test_ac17_hook_failure_output(self):
        # eg:ac EG-S1-AC17
        fx = self.fixture()
        fx.install_hook('pre-commit', '#!/bin/sh\nexit 1\n')
        fx.append('a.txt', 'more\n')
        res = fx.checkpoint('--kind', 'candidate', '--path', 'a.txt', '--path', 'b.txt')
        data = self.assertRefused(res, ['a.txt', 'b.txt'])
        self.assertIsNone(data.get('commit'))
        self.assertEqual(data.get('branch'), 'eg/v2')
        self.assertEqual(data.get('kind'), 'candidate')
        self.assertIn('spec', data)
        self.assertIsNone(data.get('spec'))

    def test_ac17_argument_error_output(self):
        # eg:ac EG-S1-AC17
        cases = [
            ('kind-invalid', ['--kind', 'other', '--spec', 'EG-S1'], None, 'EG-S1'),
            ('kind-missing', ['--spec', 'EG-S1'], None, 'EG-S1'),
            ('spec-invalid', ['--kind', 'review', '--spec', 'bad spec'], 'review', None),
            ('unknown-option', ['--kind', 'review', '--frobnicate'], None, None),
        ]
        for name, args, kind, spec in cases:
            with self.subTest(case=name):
                fx = self.fixture()
                fx.append('a.txt', 'more\n')
                res = fx.checkpoint(*(args + ['--path', 'a.txt', '--path', 'b.txt']))
                data = self.assertUsageError(res, given_paths=['a.txt', 'b.txt'])
                if name != 'unknown-option':
                    self.assertIn('kind', data)
                    self.assertIn('spec', data)
                    self.assertEqual(data.get('kind'), kind)
                    self.assertEqual(data.get('spec'), spec)

    def test_ac17_environment_usage_errors_output(self):
        # eg:ac EG-S1-AC17
        fx = self.fixture()
        fx.append('a.txt', 'more\n')
        empty_bin = os.path.join(fx.aux, 'empty-bin')
        os.makedirs(empty_bin)
        outside = os.path.join(fx.base, 'not-a-repo')
        os.makedirs(outside)
        with open(os.path.join(outside, 'a.txt'), 'w') as f:
            f.write('x\n')
        for name, kw in (('no-git-on-path', {'env_extra': {'PATH': empty_bin}}),
                         ('not-a-repository', {'cwd': outside})):
            with self.subTest(case=name):
                res = fx.checkpoint('--kind', 'record', '--path', 'a.txt', **kw)
                data = self.assertUsageError(res, given_paths=['a.txt'])
                self.assertEqual(data.get('kind'), 'record')


if __name__ == '__main__':
    unittest.main()
