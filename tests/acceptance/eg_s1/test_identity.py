"""EG-S1 acceptance tests for `eg.py identity` (AC13)."""

import os
import unittest

from .support import EgTestCase, HEX40, sha256


class AC13Identity(EgTestCase):

    def assertIdentity(self, res, code, result, commit, blob, digest, working, matches):
        self.assertExit(res, code)
        data = self.identity_json(res)
        for key in ('result', 'path', 'commit', 'blob', 'sha256', 'working_sha256',
                    'matches', 'message'):
            self.assertIn(key, data, res.describe())
        self.assertEqual(data['result'], result, res.describe())
        self.assertEqual(data['commit'], commit, res.describe())
        self.assertEqual(data['blob'], blob, res.describe())
        self.assertEqual(data['sha256'], digest, res.describe())
        self.assertEqual(data['working_sha256'], working, res.describe())
        self.assertIs(data['matches'], matches, res.describe())
        return data

    def test_ac13_unmodified_file_matches(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        head = fx.head()
        content = fx.read('a.txt')
        res = fx.identity('--path', 'a.txt')
        data = self.assertIdentity(res, 0, 'match', head, fx.blob(head, 'a.txt'),
                                   sha256(content), sha256(content), True)
        self.assertEqual(data['path'], 'a.txt')
        self.assertRegex(data['commit'], HEX40)

    def test_ac13_modified_file_mismatch_same_size_and_mtime(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        head = fx.head()
        original = fx.read('a.txt')
        st = os.stat(fx.path('a.txt'))
        changed = b'ALPHA\n'
        self.assertEqual(len(changed), len(original))
        fx.write('a.txt', changed)
        os.utime(fx.path('a.txt'), ns=(st.st_atime_ns, st.st_mtime_ns))
        res = fx.identity('--path', 'a.txt')
        # EG-S1-AC13-W1: comparing size or mtime reports a match here.
        self.assertIdentity(res, 1, 'mismatch', head, fx.blob(head, 'a.txt'),
                            sha256(original), sha256(changed), False)

    def test_ac13_deleted_file_against_old_commit(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        old = fx.head()
        old_bytes = fx.show(old, 'b.txt')
        fx.git('rm', '-q', '--', 'b.txt')
        fx.setup_commit('remove b.txt')
        self.assertFalse(os.path.exists(fx.path('b.txt')))
        res = fx.identity('--path', 'b.txt', '--at', old)
        # EG-S1-AC13-W3: rejecting the missing working file drops the commit identity.
        # EG-S1-AC13-W2: reading HEAD (where b.txt is gone) yields missing/null blob.
        self.assertIdentity(res, 1, 'mismatch', old, fx.blob(old, 'b.txt'),
                            sha256(old_bytes), None, False)

    def test_ac13_at_selects_the_commit(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        old = fx.head()
        v1 = fx.read('a.txt')
        fx.write('a.txt', 'alpha v2\n')
        fx.git('add', '--', 'a.txt')
        fx.setup_commit('a v2')
        fx.write('a.txt', v1)
        fx.git('add', '--', 'a.txt')
        for at in (old, 'HEAD~1', old[:12]):
            with self.subTest(at=at):
                res = fx.identity('--path', 'a.txt', '--at', at)
                # EG-S1-AC13-W2: ignoring --at compares against HEAD (alpha v2).
                self.assertIdentity(res, 0, 'match', old, fx.blob(old, 'a.txt'),
                                    sha256(v1), sha256(v1), True)

    def test_ac13_path_not_in_commit_is_missing(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        head = fx.head()
        fx.write('docs/untracked.md', 'not committed\n')
        res = fx.identity('--path', 'docs/untracked.md')
        self.assertIdentity(res, 1, 'missing', head, None, None,
                            sha256(b'not committed\n'), False)
        res = fx.identity('--path', 'nowhere.txt')
        self.assertIdentity(res, 1, 'missing', head, None, None, None, False)

    def test_ac13_unresolvable_at_exit_2(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        res = fx.identity('--path', 'a.txt', '--at', 'no-such-revision')
        self.assertExit(res, 2)
        data = self.identity_json(res)
        self.assertIn('commit', data)
        self.assertIsNone(data['commit'])
        self.assertEqual(data.get('result'), 'error')
        self.assertIs(data.get('matches'), False)

    def test_ac13_invalid_paths_error(self):
        # eg:ac EG-S1-AC13
        cases = (('directory', 'sub'), ('dotdot', 'sub/../a.txt'), ('dot-slash', './a.txt'),
                 ('trailing-slash', 'a.txt/'), ('dot-git', '.git/config'),
                 ('absolute', None), ('symlink', 'link.txt'))
        for name, rel in cases:
            with self.subTest(case=name):
                fx = self.fixture()
                os.symlink('a.txt', fx.path('link.txt'))
                if rel is None:
                    rel = fx.path('a.txt')
                res = fx.identity('--path', rel)
                data = self.assertIdentity(res, 1, 'error', None, None, None, None, False)
                self.assertTrue(isinstance(data['message'], str) and data['message'].strip(),
                                res.describe())

    def test_ac13_runs_from_subdirectory(self):
        # eg:ac EG-S1-AC13
        fx = self.fixture()
        head = fx.head()
        content = fx.read('a.txt')
        res = fx.identity('--path', 'a.txt', cwd=fx.path('sub'))
        self.assertIdentity(res, 0, 'match', head, fx.blob(head, 'a.txt'),
                            sha256(content), sha256(content), True)


if __name__ == '__main__':
    unittest.main()
