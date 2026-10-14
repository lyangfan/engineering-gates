"""EG-S1-AC15 concurrent repetition (long-running, kept in its own class)."""

import re
import unittest

from .support import EgTestCase, RUN_ID, read_jsonl

REPETITIONS = 20
PER_RUN_TIMEOUT = 30
RUN_LINE = re.compile(r'^EG-Run: ([0-9a-f]{32})\s*$', re.M)


class AC15ConcurrentCheckpoints(EgTestCase):

    def test_ac15_two_concurrent_checkpoints_keep_invariants(self):
        # eg:ac EG-S1-AC15
        # Stops at the first failing round so a hanging implementation costs
        # at most one PER_RUN_TIMEOUT.
        for iteration in range(REPETITIONS):
            try:
                self._one_round(iteration)
            except AssertionError as exc:
                raise AssertionError('round %d of %d: %s' % (iteration + 1, REPETITIONS, exc))

    def _one_round(self, iteration):
        fx = self.fixture()
        fx.append('a.txt', 'round %d\n' % iteration)
        fx.append('b.txt', 'round %d\n' % iteration)
        base = fx.head()
        pre_entries = {'a.txt': fx.index_entry('a.txt'), 'b.txt': fx.index_entry('b.txt')}
        bin_dir, git_log = fx.git_wrapper()
        audit_env, audit_log = fx.audit_site()
        procs = {}
        for rel in ('a.txt', 'b.txt'):
            procs[rel] = fx.start('checkpoint', ['--kind', 'record', '--path', rel],
                                  env_extra=audit_env, path_prefix=[bin_dir])
        results = dict((rel, p.finish(PER_RUN_TIMEOUT)) for rel, p in procs.items())
        pids = dict((rel, p.pid) for rel, p in procs.items())
        calls = read_jsonl(git_log)
        run_ids = dict((rel, set()) for rel in procs)
        for call in calls:
            for rel, pid in pids.items():
                if call.get('ppid') == pid and call.get('message'):
                    run_ids[rel].update(RUN_LINE.findall(call['message']))
        owner_of_run = {}
        for rel, ids in run_ids.items():
            for run_id in ids:
                owner_of_run[run_id] = rel

        for rel, res in results.items():
            other = 'b.txt' if rel == 'a.txt' else 'a.txt'
            self.assertFalse(res.timed_out, res.describe())
            self.assertIn(res.code, (0, 1), res.describe())
            data = self.checkpoint_json(res)
            if res.code == 0:
                self.assertEqual(data.get('result'), 'committed', res.describe())
                commit = data.get('commit')
                trailer = fx.trailer(commit, 'EG-Run')
                self.assertRegex(trailer, RUN_ID)
                self.assertIn(trailer, run_ids[rel],
                              'reported commit does not carry this run\'s EG-Run\n'
                              + res.describe())
                self.assertEqual(fx.changed_paths(commit), {rel}, res.describe())
            else:
                restored = fx.index_entry(rel) == pre_entries[rel]
                self.assertTrue(restored or rel in (data.get('message') or ''),
                                '%s neither restored nor reported\n%s' % (rel, res.describe()))
            self.assertNotIn(other, [p.get('path') for p in data.get('paths') or []])

        for commit in fx.commits_between(base):
            changed = fx.changed_paths(commit) or set()
            self.assertFalse({'a.txt', 'b.txt'} <= changed,
                             'commit %s mixes both processes\' paths' % commit)
            owner = owner_of_run.get(fx.trailer(commit, 'EG-Run'))
            if owner is not None:
                other = 'b.txt' if owner == 'a.txt' else 'a.txt'
                self.assertNotIn(other, changed, 'commit %s contains the other path' % commit)

        # EG-S1-AC15-W1: no lock file may be deleted by eg.
        events = read_jsonl(audit_log)
        audited = set(e['pid'] for e in events if e['event'] == 'audit-start')
        self.assertTrue(set(pids.values()) <= audited, 'audit hook not active in eg')
        deletions = [e for e in events if e['event'] != 'audit-start']
        self.assertEqual(deletions, [], 'lock files deleted: %r' % deletions)


if __name__ == '__main__':
    unittest.main()
