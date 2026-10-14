"""EG-S2 acceptance tests: modes, spec selection, report and exit codes, read-only, stdlib.

Run: /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v
"""

import os
import re
import subprocess
import sys
import unittest

try:
    from . import support as S
except ImportError:  # discovered with the test directory as top level
    import support as S


def _unclassified_clause_fixture():
    fx = S.Fixture()
    fx.add_clause(S.S2, "**[EG-S2-C05]** 没有任何引用的条款。")
    fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
    fx.add_marker("EG-S2-AC04")
    return fx


def _s1_substantive_fixture():
    fx = S.Fixture()
    fx.add_clause(S.S1, "**[EG-S1-C04]** 实质选择尚未决定。[AUTHOR-CHOICE:substantive]")
    fx.add_ac(S.S1, "**[EG-S1-AC03]** 覆盖 EG-S1-C04：描述。\n- [EG-S1-AC03-W1] 错误实现。")
    fx.add_marker("EG-S1-AC03", rel=S.T1)
    return fx


class ModeTests(S.TraceTestCase):
    """C18: modes and their check sets; usage errors."""

    # eg:ac EG-S2-AC18
    def test_ac18_spec_errors_ignored_in_design_mode(self):
        root = self.build(_unclassified_clause_fixture())
        # W EG-S2-AC18-W1: running every check in design mode would fail here.
        self.assertPass(self.trace(root, "--mode", "design"))
        self.assertFail(self.trace(root, "--mode", "spec"), "EG-S2-C11")
        res = self.trace(root, "--mode", "tests")
        self.assertFail(res, "EG-S2-C11")
        self.assertNoCheck(res, "EG-S2-C17")

    # eg:ac EG-S2-AC18
    def test_ac18_test_marker_errors_only_in_tests_mode(self):
        fx = S.Fixture()
        fx.remove_marker("EG-S2-AC03")
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "design"))
        self.assertPass(self.trace(root, "--mode", "spec"))
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")

    # eg:ac EG-S2-AC18
    def test_ac18_spec_file_naming_errors_ignored_in_design_mode(self):
        fx = S.Fixture()
        fx.files["docs/specs/EG-S9-extra.md"] = "# 多余的 spec\n"
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "design"))
        self.assertFail(self.trace(root, "--mode", "spec"), "EG-S2-C10")

    # eg:ac EG-S2-AC18
    def test_ac18_design_checks_run_in_every_mode(self):
        fx = S.Fixture()
        fx.edit(S.DESIGN_EXTRA, "全局约束见 D-008。", "全局约束另见附表。")
        root = self.build(fx)
        for mode in ("design", "spec", "tests"):
            with self.subTest(mode=mode):
                self.assertFail(self.trace(root, "--mode", mode), "EG-S2-C05")

    # eg:ac EG-S2-AC18
    def test_ac18_freeze_check_only_with_freeze(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S2-C05]** 实质选择尚未决定。[AUTHOR-CHOICE:substantive]")
        fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
        fx.add_marker("EG-S2-AC04")
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "spec"))
        self.assertPass(self.trace(root, "--mode", "tests"))
        self.assertFail(self.trace(root, "--mode", "spec", "--freeze"), "EG-S2-C13")

    # eg:ac EG-S2-AC18
    def test_ac18_usage_errors_exit_2(self):
        root = self.build()
        res = self.trace(root)
        # W EG-S2-AC18-W2: illegal combinations must not be ignored (exit 0).
        self.assertUsageError(res, checks=("EG-S2-C18",))
        self.assertIsNone(res.report["mode"], res.describe())

        cases = [
            ("tests with freeze", ["--mode", "tests", "--freeze"]),
            ("design with freeze", ["--mode", "design", "--freeze"]),
            ("design with spec", ["--mode", "design", "--spec", "EG-S2"]),
            ("unknown mode", ["--mode", "bogus"]),
        ]
        for label, args in cases:
            with self.subTest(label):
                res = self.trace(root, *args)
                self.assertUsageError(res, checks=("EG-S2-C18",))


class SpecSelectionTests(S.TraceTestCase):
    """C23: --spec selection."""

    # eg:ac EG-S2-AC23
    def test_ac23_selected_spec_ignores_other_specs_freeze(self):
        root = self.build(_s1_substantive_fixture())
        res = self.trace(root, "--mode", "spec", "--spec", "EG-S2", "--freeze")
        # W EG-S2-AC23-W1: ignoring --spec would report EG-S1's substantive marker.
        self.assertPass(res)
        clauses = sorted(c.get("clause") for c in res.report["local_choices"])
        self.assertEqual(clauses, ["EG-S2-C04"], res.describe())

        self.assertFail(self.trace(root, "--mode", "spec", "--freeze"), "EG-S2-C13")
        self.assertFail(
            self.trace(root, "--mode", "spec", "--spec", "EG-S1", "--spec", "EG-S2", "--freeze"),
            "EG-S2-C13",
        )

    # eg:ac EG-S2-AC23
    def test_ac23_unknown_or_missing_spec_is_usage_error(self):
        root = self.build()
        for mode in ("spec", "tests"):
            for spec_id in ("EG-S9", "EG-S3"):
                with self.subTest(mode=mode, spec=spec_id):
                    res = self.trace(root, "--mode", mode, "--spec", spec_id)
                    self.assertUsageError(res, checks=("EG-S2-C23",))

    # eg:ac EG-S2-AC23
    def test_ac23_selection_limits_clause_checks(self):
        fx = S.Fixture()
        fx.edit(S.S1, "**[EG-S1-C01]** 第一条（D-001）。", "**[EG-S1-C01]** 第一条（F-05）。")
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "spec", "--spec", "EG-S2"))
        self.assertFail(self.trace(root, "--mode", "spec", "--spec", "EG-S1"), "EG-S2-C12")
        self.assertFail(self.trace(root, "--mode", "spec"), "EG-S2-C12")

    # eg:ac EG-S2-AC23
    def test_ac23_selection_scope_of_file_naming_check(self):
        fx = S.Fixture()
        fx.files["docs/specs/EG-S9-extra.md"] = "# 多余的 spec\n"
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "spec", "--spec", "EG-S2"))
        self.assertFail(self.trace(root, "--mode", "spec"), "EG-S2-C10")

        fx = S.Fixture()
        fx.files["docs/specs/EG-S2-other.md"] = "# 另一份 EG-S2\n"
        root = self.build(fx)
        self.assertFail(self.trace(root, "--mode", "spec", "--spec", "EG-S2"), "EG-S2-C10")
        self.assertPass(self.trace(root, "--mode", "spec", "--spec", "EG-S1"))

    # eg:ac EG-S2-AC23
    def test_ac23_selection_scope_of_test_markers(self):
        fx = S.Fixture()
        fx.add_marker("EG-S1-AC99", rel=S.T1)
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "tests", "--spec", "EG-S2"))
        self.assertFail(self.trace(root, "--mode", "tests", "--spec", "EG-S1"), "EG-S2-C17")
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")


class ReportTests(S.TraceTestCase):
    """C19: exit codes, input errors, JSON report on stdout, summary on stderr."""

    # eg:ac EG-S2-AC19
    def test_ac19_failure_report_is_json_with_full_failure_items(self):
        fx = S.Fixture()
        fx.edit(S.DESIGN_EXTRA, "全局约束见 D-008。", "全局约束另见附表。")
        res = self.trace(self.build(fx), "--mode", "spec")
        # The runner already asserts: stdout is exactly one JSON object
        # (W EG-S2-AC19-W2) and every failure has check/path/line/message
        # (W EG-S2-AC19-W3: a missing "line" key fails check_report_shape).
        self.assertFail(res, "EG-S2-C05")
        for item in res.failures:
            self.assertIn("line", item, res.describe())
        self.assertTrue(res.stderr.strip(), "human summary expected on stderr\n" + res.describe())

    # eg:ac EG-S2-AC19
    def test_ac19_registry_syntax_error_is_input_error(self):
        fx = S.Fixture()
        fx.raw[S.DECISIONS] = b'{"schema": "eg-decisions/v1", "decisions": [\n'
        root = self.build(fx)
        for mode in ("design", "spec", "tests"):
            with self.subTest(mode=mode):
                # W EG-S2-AC19-W1: reporting unreadable input as a check failure gives 1.
                self.assertError(self.trace(root, "--mode", mode))

    # eg:ac EG-S2-AC19
    def test_ac19_input_errors_exit_2(self):
        def no_config(fx):
            fx.config = None

        def config_not_json(fx):
            fx.raw[S.CONFIG] = b"{not json"

        def registry_missing(fx):
            fx.registry = None

        def design_missing(fx):
            fx.files[S.DESIGN_EXTRA] = None

        def spec_map_missing(fx):
            fx.files[S.SPEC_MAP] = None

        def registry_top_level_array(fx):
            fx.registry = [S.decision("D-001")]

        def registry_decisions_not_array(fx):
            fx.registry["decisions"] = {"D-001": S.decision("D-001")}

        def registry_extra_top_level_key(fx):
            fx.registry["extra"] = 1

        cases = [
            ("eg.json missing", no_config),
            ("eg.json not JSON", config_not_json),
            ("registry file missing", registry_missing),
            ("design file missing", design_missing),
            ("spec map missing", spec_map_missing),
            ("registry top level is an array", registry_top_level_array),
            ("registry decisions not an array", registry_decisions_not_array),
            ("registry extra top-level key", registry_extra_top_level_key),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                fx = S.Fixture()
                mutate(fx)
                self.assertError(self.trace(self.build(fx), "--mode", "tests"))

    # eg:ac EG-S2-AC19
    def test_ac19_single_entry_problem_is_check_failure(self):
        fx = S.Fixture()
        del fx.decision("D-003")["date"]
        res = self.trace(self.build(fx), "--mode", "design")
        self.assertEqual(res.code, 1, res.describe())
        self.assertEqual(res.report["result"], "fail", res.describe())

    # eg:ac EG-S2-AC19
    def test_ac19_pass_report(self):
        res = self.trace(self.build(), "--mode", "tests")
        self.assertPass(res)


# An empty -X pycache_prefix= clears any interpreter-default prefix (macOS system
# Python 3.9 ships one outside the project), so bytecode would land in the
# project's own __pycache__ where the snapshot sees it.
BYTECODE_IN_SOURCE_TREE = ["-X", "pycache_prefix="]


class ReadOnlyTests(S.TraceTestCase):
    """C20: the command never changes the project, including __pycache__."""

    def _assert_child_would_write_bytecode_in_tree(self, env):
        probe = subprocess.run(
            [sys.executable] + BYTECODE_IN_SOURCE_TREE
            + ["-c", "import sys; print(sys.pycache_prefix, sys.dont_write_bytecode)"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=S.TIMEOUT,
        )
        self.assertEqual(
            probe.stdout.decode().strip(),
            "None False",
            "test environment: child interpreter would not write bytecode next to sources "
            "(see NOTES.md)\n" + probe.stderr.decode(errors="replace"),
        )

    # eg:ac EG-S2-AC20
    def test_ac20_runs_leave_project_unchanged(self):
        self._assert_child_would_write_bytecode_in_tree(S.clean_env(bytecode_guard=False))
        runs = [
            (["--mode", "design"], True),
            (["--mode", "spec"], True),
            (["--mode", "spec", "--freeze"], True),
            (["--mode", "tests"], True),
            (["--mode", "tests"], False),
            (["--mode", "design", "--freeze"], True),
        ]
        for label, fixture, codes in (
            ("passing project", S.Fixture(), [0, 0, 0, 0, 0, 2]),
            ("failing project", _unclassified_clause_fixture(), [0, 1, 1, 1, 1, 2]),
        ):
            with self.subTest(label):
                root = self.build(fixture)
                S.copy_scripts(root / "scripts")
                script = root / "scripts" / "eg.py"
                env = S.clean_env(bytecode_guard=False)
                before = S.snapshot(root)
                for (args, with_root), expected in zip(runs, codes):
                    if with_root:
                        res = self.run_eg(
                            args + ["--root", str(root)],
                            script=script,
                            env=env,
                            python_args=BYTECODE_IN_SOURCE_TREE,
                        )
                    else:
                        res = self.run_eg(
                            args, cwd=root, script=script, env=env, python_args=BYTECODE_IN_SOURCE_TREE
                        )
                    self.assertEqual(res.code, expected, res.describe())
                after = S.snapshot(root)
                # W EG-S2-AC20-W1: a report/cache file written into the project shows up here.
                # W EG-S2-AC20-W2: scripts/__pycache__ from imported modules shows up here.
                added = sorted(k[1] for k in after if k not in before)
                removed = sorted(k[1] for k in before if k not in after)
                changed = sorted(k[1] for k in before if k in after and before[k] != after[k])
                self.assertEqual((added, removed, changed), ([], [], []))


SCIENCE_IMPORT_PATTERNS = [
    re.compile(r"^\s*from\s+science[_-]?gates\b", re.M | re.I),
    re.compile(r"^\s*import\s+[^\n#]*\bscience[_-]?gates\b", re.M | re.I),
    re.compile(r"^\s*from\s+\S+\s+import\s+[^\n#]*\bscience[_-]?gates\b", re.M | re.I),
    re.compile(r"(?:import_module|__import__)\s*\(\s*['\"]science[_-]?gates", re.I),
    re.compile(r"sys\.path[^\n]*science[_-]?gates", re.I),
]


def _python_minor(executable):
    try:
        out = subprocess.run(
            [executable, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.decode().strip()


def _find_python39():
    for candidate in (sys.executable, "/usr/bin/python3"):
        if candidate and os.path.exists(candidate) and _python_minor(candidate) == "3.9":
            return candidate
    return None


class StdlibOnlyTests(S.TraceTestCase):
    """C21: Python 3.9 standard library only; no science-gates imports."""

    # eg:ac EG-S2-AC21
    def test_ac21_sources_do_not_import_science_gates(self):
        self.assertTrue(S.EG_PY.is_file(), "scripts/eg.py does not exist")
        offenders = []
        for path in sorted(S.SCRIPTS_DIR.rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in SCIENCE_IMPORT_PATTERNS:
                if pattern.search(text):
                    offenders.append(str(path.relative_to(S.REPO_ROOT)))
                    break
        self.assertEqual(offenders, [])

    # eg:ac EG-S2-AC21
    def test_ac21_runs_in_clean_python39_venv(self):
        base_python = _find_python39()
        if base_python is None:
            self.skipTest("no Python 3.9 interpreter found (see NOTES.md)")
        venv_dir = self.tmp / "venv"
        try:
            made = subprocess.run(
                [base_python, "-m", "venv", "--without-pip", str(venv_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self.skipTest("cannot create venv: %s (see NOTES.md)" % exc)
        if made.returncode != 0:
            self.skipTest("cannot create venv: %s (see NOTES.md)" % made.stderr.decode(errors="replace"))
        python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

        env = S.clean_env()
        env.pop("VIRTUAL_ENV", None)
        env["PYTHONNOUSERSITE"] = "1"
        probe = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.util, sys; "
                "print(sys.version_info[:2] == (3, 9), sys.prefix != sys.base_prefix, "
                "importlib.util.find_spec('yaml') is None)",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
        self.assertEqual(probe.stdout.decode().split(), ["True", "True", "True"], probe.stderr.decode())

        # W EG-S2-AC21-W1: a third-party import fails in this venv (no JSON on stdout).
        # W EG-S2-AC21-W2: 3.10+ syntax or stdlib parameters fail on this 3.9 interpreter.
        root = self.build()
        for args in (["--mode", "design"], ["--mode", "spec", "--freeze"], ["--mode", "tests"]):
            with self.subTest(args=args):
                self.assertPass(self.trace(root, *args, python=str(python), env=env))
        failing = self.build(_unclassified_clause_fixture())
        self.assertFail(self.trace(failing, "--mode", "tests", python=str(python), env=env), "EG-S2-C11")
        bad_registry = S.Fixture()
        bad_registry.raw[S.DECISIONS] = b"{"
        self.assertError(self.trace(self.build(bad_registry), "--mode", "design", python=str(python), env=env))
        self.assertUsageError(self.trace(root, "--mode", "tests", "--freeze", python=str(python), env=env))


if __name__ == "__main__":
    unittest.main()
