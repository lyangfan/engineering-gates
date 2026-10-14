"""Fixture project builder and subprocess runner for the EG-S2 acceptance tests.

The tool under test is only exercised through its public interface:
``[sys.executable, <repo>/scripts/eg.py, "trace", ...]``. Fixture projects are
built inside ``tempfile`` directories; nothing is written into the repository.

Test-marker strings inside fixture files are assembled at runtime (``ac_marker``)
so that this source file itself never contains a literal test marker for a
fixture-only acceptance ID.
"""

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _repo_root():
    env = os.environ.get("EG_REPO_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[3]


REPO_ROOT = _repo_root()
SCRIPTS_DIR = REPO_ROOT / "scripts"
EG_PY = SCRIPTS_DIR / "eg.py"
TIMEOUT = 120

REPORT_KEYS = ("schema", "mode", "specs", "freeze", "result", "failures", "local_choices")
FAILURE_KEYS = ("check", "path", "line", "message")
LOCAL_KEYS = ("spec", "clause", "path", "line")
RESULT_FOR_CODE = {0: "pass", 1: "fail", 2: "error"}
CHECK_RE = re.compile(r"^EG-S2-C\d{2,}$")


def ac_marker(ac_id):
    return "eg:" + "ac " + ac_id


# ---------------------------------------------------------------------------
# Fixture project
# ---------------------------------------------------------------------------

CONFIG = "eg.json"
DECISIONS = "docs/design/decisions.json"
DESIGN = "docs/design/design.md"
DESIGN_EXTRA = "docs/design/design-extra.md"
SPEC_MAP = "docs/design/spec-map.md"
S1 = "docs/specs/EG-S1-alpha.md"
S2 = "docs/specs/EG-S2-beta.md"
T1 = "tests/test_s1.py"
T2 = "tests/sub/test_s2.py"


def base_config():
    return {
        "schema": "eg-config/v1",
        "decisions": DECISIONS,
        "design": [DESIGN, DESIGN_EXTRA],
        "spec_map": SPEC_MAP,
        "specs": ["docs/specs/*.md"],
        "tests": ["tests/**/*.py"],
    }


def decision(did, status="active", **relations):
    entry = {
        "id": did,
        "statement": "夹具决定",
        "status": status,
        "source": "dialogue.md#fixture",
        "date": "2026-10-14",
    }
    entry.update(relations)
    return entry


def base_decisions():
    return [
        decision("D-001", amended_by=["D-002"]),
        decision("D-002", amends=["D-001"]),
        decision("D-003"),
        decision("D-004", status="superseded"),
        decision("D-005", supersedes=["D-004"]),
        decision("D-006", status="withdrawn"),
        decision("D-007", refines=["D-003"]),
        decision("D-008"),
    ]


DESIGN_TEXT = """# 夹具设计稿

## 1. 总览

本设计依据 D-001，并由 D-002 修订。

## 2. 细节

- 现实核验由 D-003 规定。
- 替代关系见 D-005。
- 流程决定见 D-007。
"""

DESIGN_EXTRA_TEXT = """# 设计稿附录

全局约束见 D-008。
"""

MAP_HEAD = "# 夹具 spec 地图\n\n> 夹具。\n"

SEC_LIST = (
    "1. spec 列表",
    "| ID | 目标 |\n"
    "|---|---|\n"
    "| EG-S1 | 甲 |\n"
    "| EG-S2 | 乙 |\n"
    "| EG-S3 | 丙 |\n",
)
SEC_ALLOC = (
    "2. 决定分配",
    "| 决定 | 去向 |\n"
    "|---|---|\n"
    "| D-001 | EG-S1 |\n"
    "| D-002 | EG-S2（地图字段） |\n"
    "| D-003 | EG-S3 |\n"
    "| D-005 | EG-S1、EG-S2（替代） |\n"
    "| D-007 | 不进 spec：流程决定 |\n"
    "| D-008 | 全局约束：适用于所有 spec；EG-S2 首先落实 |\n",
)
SEC_CHECK = (
    "3. 定档清单",
    "清单版本：v1。\n"
    "\n"
    "| 清单项 | EG-S1 | EG-S2 | EG-S3 |\n"
    "|---|---|---|---|\n"
    "| 公共 API / wire | 是：CLI（EG-S1-C01） | 否 | 是：执行探针 |\n"
    "| 并发 / 恢复 | 否 | 否 | 否 |\n",
)
SEC_TIER = (
    "4. 档位",
    "| spec | 规则结果 | 确认档位 | 理由 |\n"
    "|---|---|---|---|\n"
    "| EG-S1 | 严格 | 严格 | 写 git |\n"
    "| EG-S2 | 标准 | 标准 |  |\n"
    "| EG-S3 | 严格 | 标准 | 下调：夹具 |\n",
)
MAP_SECTIONS = [SEC_LIST, SEC_ALLOC, SEC_CHECK, SEC_TIER]

CHECK_ROW_API = "| 公共 API / wire | 是：CLI（EG-S1-C01） | 否 | 是：执行探针 |"
TIER_ROW_S1 = "| EG-S1 | 严格 | 严格 | 写 git |"
TIER_ROW_S2 = "| EG-S2 | 标准 | 标准 |  |"
TIER_ROW_S3 = "| EG-S3 | 严格 | 标准 | 下调：夹具 |"


def render_map(sections, head=MAP_HEAD):
    parts = [head]
    for heading, body in sections:
        parts.append("\n## %s\n\n%s" % (heading, body))
    return "".join(parts)


S1_TEXT = """# EG-S1 夹具 spec

> 夹具。

## 2. 条款

**[EG-S1-C01]** 第一条（D-001）。

**[EG-S1-C02]** 第二条（D-005）。

**[EG-S1-C03]** 第三条，局部选择。[AUTHOR-CHOICE:local]

## 3. 验收

**[EG-S1-AC01]** 覆盖 EG-S1-C01、EG-S1-C02：描述一。
- [EG-S1-AC01-W1] 错误实现一。

**[EG-S1-AC02]** 覆盖 EG-S1-C03：描述二。
- [EG-S1-AC02-W1] 错误实现一。
"""

S2_TEXT = """# EG-S2 夹具 spec

> 分配决定：D-002、D-005。

## 1. 目标

用于验收测试的夹具。

## 2. 条款

**[EG-S2-C01]** 第一条（D-002）。

**[EG-S2-C02]** 第二条（D-005，F-01）。

**[EG-S2-C03]** 第三条，只有事实引用（F-02）。

**[EG-S2-C04]** 第四条，局部选择。[AUTHOR-CHOICE:local]

## 3. 验收

**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：描述一。
- [EG-S2-AC01-W1] 错误实现一。

**[EG-S2-AC02]** 覆盖 EG-S2-C03：描述二。
- [EG-S2-AC02-W1] 错误实现一。
- [EG-S2-AC02-W2] 错误实现二。

**[EG-S2-AC03]** 覆盖 EG-S2-C04：描述三。
- [EG-S2-AC03-W1] 错误实现一。
"""

T1_TEXT = (
    '"""夹具测试：EG-S1。"""\n'
    "\n"
    "# " + ac_marker("EG-S1-AC01") + "\n"
    "def test_one():\n"
    "    pass\n"
    "\n"
    "\n"
    "def test_two():\n"
    '    """' + ac_marker("EG-S1-AC02") + '"""\n'
)

T2_TEXT = (
    "# " + ac_marker("EG-S2-AC01") + "\n"
    "# " + ac_marker("EG-S2-AC02") + "\n"
    "# " + ac_marker("EG-S2-AC03") + "\n"
    "\n"
    "\n"
    "def test_s2():\n"
    "    pass\n"
)

ACCEPTANCE_HEADING = "## 3. 验收\n"


class Fixture(object):
    """In-memory description of a fixture project; ``write`` materialises it."""

    def __init__(self):
        self.config = base_config()
        self.registry = {"schema": "eg-decisions/v1", "decisions": base_decisions()}
        self.files = {
            DESIGN: DESIGN_TEXT,
            DESIGN_EXTRA: DESIGN_EXTRA_TEXT,
            SPEC_MAP: render_map(MAP_SECTIONS),
            S1: S1_TEXT,
            S2: S2_TEXT,
            T1: T1_TEXT,
            T2: T2_TEXT,
        }
        # rel path -> bytes; written verbatim and take precedence over everything else.
        self.raw = {}
        self.bom = False

    # --- registry helpers -------------------------------------------------
    def decision(self, did):
        for entry in self.registry["decisions"]:
            if entry.get("id") == did:
                return entry
        raise KeyError(did)

    def add_decision(self, entry):
        self.registry["decisions"].append(entry)

    # --- text helpers -----------------------------------------------------
    def edit(self, rel, old, new, count=1):
        text = self.files[rel]
        found = text.count(old)
        if found != count:
            raise AssertionError(
                "fixture edit: expected %d occurrence(s) of %r in %s, found %d"
                % (count, old, rel, found)
            )
        self.files[rel] = text.replace(old, new)

    def add_clause(self, rel, text):
        """Insert a clause paragraph just before the acceptance heading."""
        self.edit(rel, ACCEPTANCE_HEADING, text.rstrip("\n") + "\n\n" + ACCEPTANCE_HEADING)

    def add_ac(self, rel, text):
        body = self.files[rel]
        if not body.endswith("\n"):
            body += "\n"
        self.files[rel] = body + "\n" + text.rstrip("\n") + "\n"

    def add_marker(self, ac_id, rel=T2):
        self.files[rel] = self.files[rel] + "# " + ac_marker(ac_id) + "\n"

    def remove_marker(self, ac_id, rel=T2):
        self.edit(rel, "# " + ac_marker(ac_id) + "\n", "")

    # --- materialise --------------------------------------------------------
    def _encode(self, text):
        data = text.encode("utf-8")
        if self.bom:
            data = b"\xef\xbb\xbf" + data
        return data

    def write(self, root):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        payload = {}
        if self.config is not None:
            payload[CONFIG] = self._encode(json.dumps(self.config, ensure_ascii=False, indent=2) + "\n")
        if self.registry is not None:
            decisions_rel = DECISIONS
            if isinstance(self.config, dict) and isinstance(self.config.get("decisions"), str):
                if not os.path.isabs(self.config["decisions"]) and ".." not in self.config["decisions"]:
                    decisions_rel = self.config["decisions"]
            payload[decisions_rel] = self._encode(
                json.dumps(self.registry, ensure_ascii=False, indent=2) + "\n"
            )
        for rel, text in self.files.items():
            if text is None:
                continue
            payload[rel] = self._encode(text)
        payload.update(self.raw)
        for rel, data in payload.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(path), "wb") as fh:
                fh.write(data)
        return root


def line_of(text, needle):
    """1-based line number of the unique line containing ``needle``."""
    hits = [i + 1 for i, line in enumerate(text.splitlines()) if needle in line]
    if len(hits) != 1:
        raise AssertionError("expected one line containing %r, found %r" % (needle, hits))
    return hits[0]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class Result(object):
    def __init__(self, args, code, stdout, stderr):
        self.args = args
        self.code = code
        self.stdout = stdout
        self.stderr = stderr
        self.report = None
        self.parse_error = None
        try:
            self.report = json.loads(stdout)
        except ValueError as exc:
            self.parse_error = str(exc)

    @property
    def failures(self):
        if isinstance(self.report, dict) and isinstance(self.report.get("failures"), list):
            return self.report["failures"]
        return []

    @property
    def checks(self):
        return [f.get("check") for f in self.failures if isinstance(f, dict)]

    def count(self, check):
        return self.checks.count(check)

    def describe(self):
        return "args=%r\nexit=%r\n--- stdout ---\n%s\n--- stderr ---\n%s" % (
            self.args,
            self.code,
            self.stdout[-4000:],
            self.stderr[-4000:],
        )


def clean_env(bytecode_guard=True):
    env = dict(os.environ)
    for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX", "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"):
        env.pop(key, None)
    if bytecode_guard:
        env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def snapshot(root):
    """Inventory of every directory and file (with content) under ``root``."""
    state = {}
    for dirpath, dirnames, filenames in os.walk(str(root)):
        rel_dir = os.path.relpath(dirpath, str(root))
        state[("dir", rel_dir)] = None
        for name in filenames:
            path = os.path.join(dirpath, name)
            with open(path, "rb") as fh:
                state[("file", os.path.relpath(path, str(root)))] = fh.read()
    return state


class TraceTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eg_s2_acc_"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.empty_cwd = self.tmp / "cwd"
        self.empty_cwd.mkdir()
        self._counter = 0

    # --- building -----------------------------------------------------------
    def build(self, fixture=None):
        if fixture is None:
            fixture = Fixture()
        self._counter += 1
        root = self.tmp / ("proj%d" % self._counter)
        fixture.write(root)
        return root

    # --- running ------------------------------------------------------------
    def run_eg(self, args, cwd=None, python=None, script=None, env=None):
        cmd = [python or sys.executable, str(script or EG_PY), "trace"] + list(args)
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or self.empty_cwd),
            env=env if env is not None else clean_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT,
        )
        res = Result(
            list(args),
            proc.returncode,
            proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"),
        )
        self.check_report_shape(res)
        return res

    def trace(self, root, *args, **kwargs):
        """Run ``eg.py trace <args> --root <root>`` from an unrelated cwd."""
        return self.run_eg(list(args) + ["--root", str(root)], **kwargs)

    # --- report validation (C19) --------------------------------------------
    def check_report_shape(self, res):
        self.assertIsNone(res.parse_error, "stdout is not a single JSON object\n" + res.describe())
        rep = res.report
        self.assertIsInstance(rep, dict, res.describe())
        for key in REPORT_KEYS:
            self.assertIn(key, rep, "report lacks %r\n%s" % (key, res.describe()))
        self.assertEqual(rep["schema"], "eg-trace-report/v1", res.describe())
        self.assertIn(res.code, RESULT_FOR_CODE, res.describe())
        self.assertEqual(rep["result"], RESULT_FOR_CODE[res.code], res.describe())
        self.assertIsInstance(rep["specs"], list, res.describe())
        self.assertIsInstance(rep["failures"], list, res.describe())
        self.assertIsInstance(rep["local_choices"], list, res.describe())
        if res.code == 0:
            self.assertEqual(rep["failures"], [], res.describe())
        else:
            self.assertTrue(rep["failures"], "non-zero exit needs failures\n" + res.describe())
        for item in rep["failures"]:
            self.assertIsInstance(item, dict, res.describe())
            for key in FAILURE_KEYS:
                self.assertIn(key, item, "failure lacks %r\n%s" % (key, res.describe()))
            self.assertIsInstance(item["check"], str, res.describe())
            self.assertRegex(item["check"], CHECK_RE, res.describe())
            self.assertIsInstance(item["message"], str, res.describe())
            line = item["line"]
            if line is not None:
                self.assertTrue(
                    isinstance(line, int) and not isinstance(line, bool) and line >= 1,
                    "line must be null or a 1-based int\n" + res.describe(),
                )
            path = item["path"]
            if res.code == 1 and path is not None:
                self.assertIsInstance(path, str, res.describe())
                self.assertNotIn("\\", path, res.describe())
                self.assertFalse(os.path.isabs(path), "path must be relative to --root\n" + res.describe())
        for item in rep["local_choices"]:
            self.assertIsInstance(item, dict, res.describe())
            for key in LOCAL_KEYS:
                self.assertIn(key, item, res.describe())
        if "--freeze" not in res.args:
            self.assertEqual(rep["local_choices"], [], res.describe())

    def _check_mode(self, res):
        args = res.args
        if "--mode" in args:
            self.assertEqual(res.report["mode"], args[args.index("--mode") + 1], res.describe())
        self.assertIs(res.report["freeze"], "--freeze" in args, res.describe())

    def assertPass(self, res):
        self.assertEqual(res.code, 0, res.describe())
        self.assertEqual(res.report["result"], "pass", res.describe())
        self.assertEqual(res.failures, [], res.describe())
        self._check_mode(res)

    def assertFail(self, res, *checks):
        self.assertEqual(res.code, 1, res.describe())
        self.assertEqual(res.report["result"], "fail", res.describe())
        self._check_mode(res)
        for check in checks:
            self.assertIn(check, res.checks, "expected a %s failure\n%s" % (check, res.describe()))

    def assertNoCheck(self, res, *checks):
        for check in checks:
            self.assertNotIn(check, res.checks, "unexpected %s failure\n%s" % (check, res.describe()))

    def assertError(self, res):
        self.assertEqual(res.code, 2, res.describe())
        self.assertEqual(res.report["result"], "error", res.describe())
        self.assertTrue(res.failures, res.describe())

    def assertUsageError(self, res, checks=("EG-S2-C18", "EG-S2-C23")):
        self.assertError(res)
        self.assertEqual(res.report["specs"], [], res.describe())
        for check in res.checks:
            self.assertIn(check, checks, res.describe())

    def assertMentions(self, res, word):
        blob = json.dumps(res.failures, ensure_ascii=False)
        self.assertIn(word, blob, "failures should point at %r\n%s" % (word, res.describe()))

    def assertHasFailureAt(self, res, check, path):
        hits = [f for f in res.failures if f.get("check") == check and f.get("path") == path]
        self.assertTrue(hits, "expected %s failure with path %r\n%s" % (check, path, res.describe()))


def copy_scripts(dest):
    shutil.copytree(
        str(SCRIPTS_DIR),
        str(dest),
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )


def deepcopy(obj):
    return copy.deepcopy(obj)
