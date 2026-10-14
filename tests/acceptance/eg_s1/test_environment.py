"""EG-S1-AC16: Python 3.9 standard library only, no science-gates, probe runs recorded."""

import ast
import importlib.util
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import unittest

from . import support

INNER_RUN_FLAG = 'EG_S1_ACCEPTANCE_INNER_VENV_RUN'
PROBE_LOG = os.path.join(support.REPO_ROOT, 'docs', 'specs', 'probes',
                         'EG-S1-git-probes.log.md')
THIRD_PARTY_GIT_LIBS = ('git', 'pygit2', 'dulwich', 'sh', 'plumbum')


def _python39():
    if sys.version_info[:2] == (3, 9):
        return sys.executable
    candidate = '/usr/bin/python3'
    if os.path.exists(candidate):
        out = subprocess.run([candidate, '-c', 'import sys;print(sys.version_info[:2])'],
                             stdout=subprocess.PIPE, universal_newlines=True).stdout
        if out.strip() == '(3, 9)':
            return candidate
    return None


def _imported_modules(tree):
    """(top-level module, lineno) for absolute imports, including dynamic ones."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((alias.name.split('.')[0], node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                found.append((node.module.split('.')[0], node.lineno))
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else (
                func.id if isinstance(func, ast.Name) else None)
            if name in ('import_module', '__import__') and node.args:
                arg = node.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    found.append((arg.value.split('.')[0], node.lineno))
    return found


def _is_stdlib(name):
    if name in sys.builtin_module_names or name == '__future__':
        return True
    try:
        spec = importlib.util.find_spec(name)
    except (ImportError, ValueError):
        return False
    if spec is None:
        return False
    origin = spec.origin or ''
    if origin in ('built-in', 'frozen'):
        return True
    locations = [origin] if origin else list(spec.submodule_search_locations or [])
    roots = set(os.path.realpath(sysconfig.get_paths()[k]) for k in ('stdlib', 'platstdlib'))
    for loc in locations:
        real = os.path.realpath(loc)
        if 'site-packages' in real or 'dist-packages' in real:
            return False
        if not any(real.startswith(root + os.sep) for root in roots):
            return False
    return bool(locations)


def _local_module_names():
    names = {'scripts'}
    scripts = os.path.join(support.REPO_ROOT, 'scripts')
    for entry in os.listdir(scripts):
        p = os.path.join(scripts, entry)
        if entry.endswith('.py'):
            names.add(entry[:-3])
        elif os.path.isdir(p) and os.path.exists(os.path.join(p, '__init__.py')):
            names.add(entry)
    return names


class AC16Environment(unittest.TestCase):

    def _sources(self):
        self.assertTrue(os.path.isfile(support.EG_PY), 'entry point missing: ' + support.EG_PY)
        sources = support.implementation_sources()
        self.assertIn(os.path.join('scripts', 'eg.py'), sources)
        return sources

    def test_ac16_acceptance_suite_passes_in_clean_python39_venv(self):
        # eg:ac EG-S1-AC16
        if os.environ.get(INNER_RUN_FLAG):
            self.skipTest('already running inside the clean venv')
        self.assertTrue(os.path.isfile(support.EG_PY), 'entry point missing: ' + support.EG_PY)
        python = _python39()
        if python is None:
            self.skipTest('no Python 3.9 interpreter available to create the venv')
        base = os.path.realpath(tempfile.mkdtemp(prefix='eg-s1-venv-'))
        self.addCleanup(shutil.rmtree, base, True)
        venv = os.path.join(base, 'venv')
        env = dict((k, v) for k, v in os.environ.items()
                   if not k.startswith('PYTHON') and k != 'VIRTUAL_ENV')
        made = subprocess.run([python, '-m', 'venv', '--without-pip', venv], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        venv_python = os.path.join(venv, 'bin', 'python')
        if made.returncode != 0 or not os.path.exists(venv_python):
            self.skipTest('python -m venv failed: %s' % made.stdout.decode('utf-8', 'replace'))
        version = subprocess.run([venv_python, '-c', 'import sys;print(sys.version_info[:2])'],
                                 env=env, stdout=subprocess.PIPE,
                                 universal_newlines=True).stdout.strip()
        self.assertEqual(version, '(3, 9)')
        env[INNER_RUN_FLAG] = '1'
        env['EG_REPO_ROOT'] = support.REPO_ROOT
        tests_top = os.path.realpath(os.path.join(support.HERE, '..', '..', '..'))
        inner = subprocess.run(
            [venv_python, '-B', '-m', 'unittest', 'discover', '-s', support.HERE,
             '-t', tests_top],
            cwd=tests_top, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=1800)
        output = inner.stdout.decode('utf-8', 'replace')
        # EG-S1-AC16-W1 (3.10+ syntax/stdlib parameters) and EG-S1-AC16-W2
        # (third-party git library, absent from the clean venv) both fail the inner run.
        self.assertEqual(inner.returncode, 0, output[-6000:])

    def test_ac16_sources_compile_with_python39(self):
        # eg:ac EG-S1-AC16
        python = _python39()
        if python is None:
            self.skipTest('no Python 3.9 interpreter available')
        for rel in self._sources():
            check = subprocess.run(
                [python, '-B', '-c',
                 'import sys; compile(open(sys.argv[1], "rb").read(), sys.argv[1], "exec")',
                 os.path.join(support.REPO_ROOT, rel)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # EG-S1-AC16-W1: syntax newer than 3.9 (e.g. `match`) does not compile.
            self.assertEqual(check.returncode, 0, '%s: %s' % (rel, check.stdout.decode()))

    def test_ac16_sources_import_only_stdlib_and_local_modules(self):
        # eg:ac EG-S1-AC16
        local = _local_module_names()
        for rel in self._sources():
            src, tree = support.parse_source(rel)
            for name, lineno in _imported_modules(tree):
                where = '%s:%d imports %s' % (rel, lineno, name)
                # EG-S1-AC16-W2: GitPython (`git`) and similar libraries are rejected.
                self.assertNotIn(name, THIRD_PARTY_GIT_LIBS, where)
                self.assertTrue(name in local or _is_stdlib(name), where)

    def test_ac16_sources_do_not_import_science_gates(self):
        # eg:ac EG-S1-AC16
        for rel in self._sources():
            src, tree = support.parse_source(rel)
            for name, lineno in _imported_modules(tree):
                self.assertNotIn('science', name.lower().replace('-', '_'),
                                 '%s:%d imports %s' % (rel, lineno, name))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr in ('insert', 'append', 'extend', 'addsitedir'):
                    for arg in ast.walk(node):
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            self.assertNotIn('science', arg.value.lower(),
                                             '%s:%d adds a science-gates path' % (
                                                 rel, node.lineno))

    def _probe_log(self):
        self.assertTrue(os.path.isfile(PROBE_LOG), 'probe log missing: ' + PROBE_LOG)
        with open(PROBE_LOG, encoding='utf-8') as f:
            return f.read()

    def test_ac16_probe_log_records_run_before_implementation(self):
        # eg:ac EG-S1-AC16
        self.assertIn('实现开始前', self._probe_log(),
                      'no probe run recorded before implementation started (C16, D-012)')

    def test_ac16_probe_log_records_run_before_implementation_review(self):
        # eg:ac EG-S1-AC16
        self.assertIn('审实现前', self._probe_log(),
                      'no probe run recorded before the implementation review (C16, D-012)')


if __name__ == '__main__':
    unittest.main()
