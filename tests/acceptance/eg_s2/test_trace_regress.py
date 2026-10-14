"""EG-S2 regression tests for implementation review findings.

B1: IB1-01, -02, -03, -05.  C1: IC1-01, -02, -03.

Run: /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v
"""

import os
import re
import unittest

try:
    from . import support as S
except ImportError:  # discovered with the test directory as top level
    import support as S


def _with_clause(clause_text):
    """Base fixture plus an extra EG-S2 clause C05 covered by a new AC04."""
    fx = S.Fixture()
    fx.add_clause(S.S2, clause_text)
    fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
    fx.add_marker("EG-S2-AC04")
    return fx


# ---------------------------------------------------------------------------
# IB1-01: AUTHOR-CHOICE markers followed directly by CJK text or letters (C11, C13)
# ---------------------------------------------------------------------------

FOLLOWERS = [
    ("followed by CJK", "需用户决定。"),
    ("followed by a letter", "pending."),
]


class AuthorChoiceFollowedByTextTests(S.TraceTestCase):
    """C11 / C13: a marker is the exact text ``[AUTHOR-CHOICE:...]``; what follows is irrelevant."""

    # eg:ac EG-S2-AC13
    # IB1-01
    def test_ac13_freeze_rejects_substantive_marker_followed_by_text(self):
        for label, tail in FOLLOWERS:
            with self.subTest(label):
                fx = _with_clause("**[EG-S2-C05]** 依据 D-002，细节[AUTHOR-CHOICE:substantive]" + tail)
                res = self.trace(self.build(fx), "--mode", "spec", "--freeze")
                self.assertFail(res, "EG-S2-C13")
                self.assertHasFailureAt(res, "EG-S2-C13", S.S2)

    # eg:ac EG-S2-AC11
    # IB1-01
    def test_ac11_substantive_marker_followed_by_text_classifies_clause(self):
        for label, tail in FOLLOWERS:
            with self.subTest(label):
                fx = _with_clause("**[EG-S2-C05]** 实质选择[AUTHOR-CHOICE:substantive]" + tail)
                res = self.trace(self.build(fx), "--mode", "spec")
                self.assertNoCheck(res, "EG-S2-C11")
                self.assertPass(res)

    # eg:ac EG-S2-AC11
    # eg:ac EG-S2-AC13
    # IB1-01
    def test_ac13_local_marker_followed_by_text_classifies_and_is_listed(self):
        for label, tail in FOLLOWERS:
            with self.subTest(label):
                clause = "**[EG-S2-C05]** 第五条，[AUTHOR-CHOICE:local]" + tail
                fx = _with_clause(clause)
                root = self.build(fx)
                res = self.trace(root, "--mode", "spec")
                self.assertNoCheck(res, "EG-S2-C11")
                self.assertPass(res)

                res = self.trace(root, "--mode", "spec", "--freeze")
                self.assertNoCheck(res, "EG-S2-C11")
                self.assertPass(res)
                got = sorted(
                    (c.get("spec"), c.get("clause"), c.get("path"), c.get("line"))
                    for c in res.report["local_choices"]
                )
                # Clause marker and AUTHOR-CHOICE marker share one line (NOTES section 1).
                want = sorted([
                    ("EG-S1", "EG-S1-C03", S.S1, S.line_of(S.S1_TEXT, "**[EG-S1-C03]**")),
                    ("EG-S2", "EG-S2-C04", S.S2, S.line_of(fx.files[S.S2], "**[EG-S2-C04]**")),
                    ("EG-S2", "EG-S2-C05", S.S2, S.line_of(fx.files[S.S2], "**[EG-S2-C05]**")),
                ])
                self.assertEqual(got, want, res.describe())


# ---------------------------------------------------------------------------
# IB1-02: test markers whose spec is not in the map or has no file (C17, C23)
# ---------------------------------------------------------------------------


class UnknownSpecTestMarkerTests(S.TraceTestCase):
    """C17: without --spec, every test marker must name an acceptance of an existing spec file."""

    # eg:ac EG-S2-AC17
    # IB1-02
    def test_ac17_marker_with_prefix_outside_map_fails_without_spec(self):
        fx = S.Fixture()
        fx.add_marker("EG-S9-AC01")
        root = self.build(fx)
        # C23: with --spec only markers prefixed by a selected spec are checked.
        self.assertPass(self.trace(root, "--mode", "tests", "--spec", "EG-S2"))
        self.assertPass(self.trace(root, "--mode", "spec"))
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")

    # eg:ac EG-S2-AC17
    # IB1-02
    def test_ac17_marker_for_spec_without_file_fails_without_spec(self):
        # EG-S3 is in the map but has no spec file.
        fx = S.Fixture()
        fx.add_marker("EG-S3-AC01")
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "tests", "--spec", "EG-S2"))
        self.assertPass(self.trace(root, "--mode", "tests", "--spec", "EG-S1", "--spec", "EG-S2"))
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")


# ---------------------------------------------------------------------------
# IB1-03: spec IDs are whatever the tier table lists (C25)
# ---------------------------------------------------------------------------

RENAMINGS = [
    ("APP-Sn", [("EG-S", "APP-S")]),
    ("names without -Sn", [("EG-S1", "CORE"), ("EG-S2", "TRACE"), ("EG-S3", "PROBE"), ("EG-S9", "EXTRA")]),
]


def _rename(text, pairs):
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _renamed(fx, pairs):
    """Copy of ``fx`` with every spec ID replaced, in file contents and file names."""
    out = S.deepcopy(fx)
    out.files = {
        _rename(rel, pairs): (None if text is None else _rename(text, pairs))
        for rel, text in fx.files.items()
    }
    return out


def _outcome(res, pairs=None):
    """Exit code, failures as (check, path, line), and local choices, with paths renamed."""
    def path(p):
        return _rename(p, pairs) if (pairs and isinstance(p, str)) else p

    failures = sorted(
        (f.get("check"), str(path(f.get("path"))), str(f.get("line"))) for f in res.failures
    )
    local = sorted(
        (str(path(c.get("spec"))), str(path(c.get("clause"))), str(path(c.get("path"))), str(c.get("line")))
        for c in res.report["local_choices"]
    )
    return res.code, failures, local


def _dup_clause(fx):
    fx.add_clause(S.S2, "**[EG-S2-C01]** 重复的条款（D-002）。")


def _foreign_clause_prefix(fx):
    fx.add_clause(S.S2, "**[EG-S3-C05]** 前缀与文件不符（D-002）。")


def _file_prefix_not_in_map(fx):
    fx.files["docs/specs/EG-S9-extra.md"] = "# 多余的 spec\n"


def _coverage_of_unknown_clause(fx):
    fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C99：描述。\n- [EG-S2-AC04-W1] 错误实现。")
    fx.add_marker("EG-S2-AC04")


def _uncovered_clause(fx):
    fx.add_clause(S.S2, "**[EG-S2-C05]** 没有验收覆盖的条款（D-002）。")


def _misplaced_wrong_impl(fx):
    fx.edit(
        S.S2,
        "- [EG-S2-AC02-W2] 错误实现二。\n",
        "- [EG-S2-AC02-W2] 错误实现二。\n- [EG-S2-AC01-W2] 放错位置的错误实现。\n",
    )


def _unclassified_clause(fx):
    fx.add_clause(S.S2, "**[EG-S2-C05]** 没有任何引用的条款。")
    fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
    fx.add_marker("EG-S2-AC04")


def _substantive_left(fx):
    fx.add_clause(S.S2, "**[EG-S2-C05]** 实质选择尚未决定。[AUTHOR-CHOICE:substantive]")
    fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
    fx.add_marker("EG-S2-AC04")


def _missing_test_marker(fx):
    fx.remove_marker("EG-S2-AC03")


def _unknown_test_marker(fx):
    fx.add_marker("EG-S2-AC99")


def _checklist_column_not_in_tier_table(fx):
    fx.edit(S.SPEC_MAP, S.TIER_ROW_S3 + "\n", "")
    fx.edit(S.SPEC_MAP, "| D-003 | EG-S3 |\n", "| D-003 | 不进 spec：夹具 |\n")


def _unreferenced_allocation(fx):
    fx.edit(S.SPEC_MAP, "| D-002 | EG-S2（地图字段） |", "| D-002 | EG-S1、EG-S2（地图字段） |")


# (label, mode args, mutation or None, check the EG-Sn fixture must report or None for pass)
CASES = [
    ("design pass", ["--mode", "design"], None, None),
    ("spec pass", ["--mode", "spec"], None, None),
    ("tests pass", ["--mode", "tests"], None, None),
    ("freeze local choices", ["--mode", "spec", "--freeze"], None, None),
    ("spec selected", ["--mode", "spec", "--spec", "EG-S2"], None, None),
    ("C25 checklist column not in tier table", ["--mode", "design"], _checklist_column_not_in_tier_table, "EG-S2-C25"),
    ("C12 allocated decision not cited", ["--mode", "spec"], _unreferenced_allocation, "EG-S2-C12"),
    ("C10 duplicate clause", ["--mode", "spec"], _dup_clause, "EG-S2-C10"),
    ("C10 clause prefix differs from file", ["--mode", "spec"], _foreign_clause_prefix, "EG-S2-C10"),
    ("C10 file prefix not in map", ["--mode", "tests"], _file_prefix_not_in_map, "EG-S2-C10"),
    ("C11 unclassified clause", ["--mode", "spec"], _unclassified_clause, "EG-S2-C11"),
    ("C13 substantive under freeze", ["--mode", "spec", "--freeze"], _substantive_left, "EG-S2-C13"),
    ("C14 coverage of unknown clause", ["--mode", "spec"], _coverage_of_unknown_clause, "EG-S2-C14"),
    ("C15 uncovered clause", ["--mode", "spec"], _uncovered_clause, "EG-S2-C15"),
    ("C16 misplaced wrong implementation", ["--mode", "spec"], _misplaced_wrong_impl, "EG-S2-C16"),
    ("C17 missing test marker", ["--mode", "tests"], _missing_test_marker, "EG-S2-C17"),
    ("C17 unknown test marker", ["--mode", "tests"], _unknown_test_marker, "EG-S2-C17"),
]


class SpecIdFormTests(S.TraceTestCase):
    """C25: the spec ID set is the tier table's first column; no ID shape is prescribed.

    A project whose spec IDs differ from the base fixture only by name must get the
    same exit code, the same (check, path, line) failures and the same local choices.
    """

    def _compare(self, label, args, mutate, expect, pairs):
        fx = S.Fixture()
        if mutate is not None:
            mutate(fx)
        eg_res = self.trace(self.build(fx), *args)
        if expect is None:
            self.assertPass(eg_res)
        else:
            self.assertFail(eg_res, expect)

        renamed_args = [_rename(a, pairs) for a in args]
        other = self.trace(self.build(_renamed(fx, pairs)), *renamed_args)
        self.assertEqual(
            _outcome(other),
            _outcome(eg_res, pairs),
            "%s: renamed project differs from EG-Sn project\n--- EG-Sn ---\n%s\n--- renamed ---\n%s"
            % (label, eg_res.describe(), other.describe()),
        )

    # eg:ac EG-S2-AC25
    # IB1-03
    def test_ac25_design_mode_accepts_any_spec_id_form(self):
        for name, pairs in RENAMINGS:
            for label, args, mutate, expect in CASES:
                if args[1] != "design":
                    continue
                with self.subTest(name + ": " + label):
                    self._compare(label, args, mutate, expect, pairs)

    # eg:ac EG-S2-AC10
    # eg:ac EG-S2-AC14
    # eg:ac EG-S2-AC16
    # IB1-03
    def test_ac10_spec_mode_accepts_any_spec_id_form(self):
        for name, pairs in RENAMINGS:
            for label, args, mutate, expect in CASES:
                if args[1] != "spec":
                    continue
                with self.subTest(name + ": " + label):
                    self._compare(label, args, mutate, expect, pairs)

    # eg:ac EG-S2-AC17
    # IB1-03
    def test_ac17_tests_mode_accepts_any_spec_id_form(self):
        for name, pairs in RENAMINGS:
            for label, args, mutate, expect in CASES:
                if args[1] != "tests":
                    continue
                with self.subTest(name + ": " + label):
                    self._compare(label, args, mutate, expect, pairs)

    # eg:ac EG-S2-AC23
    # IB1-03
    def test_ac23_renamed_spec_id_is_a_valid_selection(self):
        for name, pairs in RENAMINGS:
            with self.subTest(name):
                root = self.build(_renamed(S.Fixture(), pairs))
                for mode in ("spec", "tests"):
                    self.assertPass(self.trace(root, "--mode", mode, "--spec", _rename("EG-S2", pairs)))


# ---------------------------------------------------------------------------
# IB1-05, IC1-02, IC1-03: C07 allocation failure location (C19)
# ---------------------------------------------------------------------------


def _read_lines(root, rel):
    with open(os.path.join(str(root), rel), encoding="utf-8-sig") as fh:
        return fh.read().split("\n")


def _entry_span(registry_lines, did):
    """1-based first and last line of the registry object whose ``id`` is ``did``."""
    key = '"id": "%s"' % did
    hits = [i for i, text in enumerate(registry_lines) if key in text]
    if len(hits) != 1:
        raise AssertionError("expected one registry line with %s, found %r" % (key, hits))
    at = hits[0]
    start = max(i for i in range(at + 1) if registry_lines[i].strip() == "{")
    end = min(i for i in range(at, len(registry_lines)) if registry_lines[i].strip().startswith("}"))
    return start + 1, end + 1


def _section_span(map_lines, title):
    """1-based heading line and last non-blank line of the spec-map section ``title`` (C25)."""
    heading = re.compile(r"^#{1,6}\s+(?:\d+\.\s*)?" + re.escape(title) + r"\s*$")
    starts = [i for i, text in enumerate(map_lines) if heading.match(text)]
    if len(starts) != 1:
        raise AssertionError("expected one %r heading in the spec map, found %r" % (title, starts))
    start = starts[0]
    end = len(map_lines)
    for i in range(start + 1, len(map_lines)):
        if re.match(r"^#{1,6}\s", map_lines[i]):
            end = i
            break
    while end > start + 1 and not map_lines[end - 1].strip():
        end -= 1
    return start + 1, end


def _decision_last(fx, did):
    """Move ``did`` to the end of the registry, past the last line of the spec map."""
    entry = fx.decision(did)
    fx.registry["decisions"].remove(entry)
    fx.registry["decisions"].append(entry)


# (label, fixture change); the base fixture puts D-003's registry line inside the
# spec map but outside its allocation section, the second variant past its end.
LOCATION_LAYOUTS = [
    ("base fixture", None),
    ("D-003 last in the registry", lambda fx: _decision_last(fx, "D-003")),
]


class AllocationLocationTests(S.TraceTestCase):
    """C19: a non-null ``line`` is the line of the problem in the file named by ``path``.

    For a C07 allocation failure about decision ``did`` the problem lives either in
    the registry entry of ``did`` or in the allocation section of the spec map, so a
    non-null ``line`` must fall inside that span of the file named by ``path``.
    """

    def _assert_c07_located(self, root, res, did):
        registry = _read_lines(root, S.DECISIONS)
        spec_map = _read_lines(root, S.SPEC_MAP)
        spans = {
            S.DECISIONS: _entry_span(registry, did),
            S.SPEC_MAP: _section_span(spec_map, "决定分配"),
        }
        # The IB1-05 defect (spec-map path, registry line) is only visible if no line
        # of the registry entry also lies in the allocation section.
        entry_lo, entry_hi = spans[S.DECISIONS]
        alloc_lo, alloc_hi = spans[S.SPEC_MAP]
        self.assertTrue(
            entry_hi < alloc_lo or entry_lo > alloc_hi,
            "fixture precondition: registry lines %r overlap allocation section %r"
            % (spans[S.DECISIONS], spans[S.SPEC_MAP]),
        )
        hits = [f for f in res.failures if f.get("check") == "EG-S2-C07"]
        for item in hits:
            path, line = item.get("path"), item.get("line")
            if line is None:
                continue
            self.assertIn(
                path,
                spans,
                "a C07 line must lie in the registry or the spec map\n" + res.describe(),
            )
            lo, hi = spans[path]
            self.assertTrue(
                lo <= line <= hi,
                "line %d of %s is outside lines %d-%d (%s)\n%s"
                % (
                    line,
                    path,
                    lo,
                    hi,
                    "registry entry of " + did if path == S.DECISIONS else "allocation section",
                    res.describe(),
                ),
            )

    # eg:ac EG-S2-AC07
    # eg:ac EG-S2-AC19
    # IB1-05, assertion revised for IC1-03
    def _check_layouts(self, old_row, new_rows):
        for label, layout in LOCATION_LAYOUTS:
            with self.subTest(label):
                fx = S.Fixture()
                if layout is not None:
                    layout(fx)
                fx.edit(S.SPEC_MAP, old_row, new_rows)
                root = self.build(fx)
                res = self.trace(root, "--mode", "design")
                self.assertFail(res, "EG-S2-C07")
                self._assert_c07_located(root, res, "D-003")

    # eg:ac EG-S2-AC07
    # eg:ac EG-S2-AC19
    # IB1-05, assertion revised for IC1-03
    def test_ac07_missing_allocation_failure_points_into_its_path(self):
        self._check_layouts("| D-003 | EG-S3 |\n", "")

    # eg:ac EG-S2-AC07
    # eg:ac EG-S2-AC19
    # IC1-02
    def test_ac07_duplicate_allocation_failure_points_into_its_path(self):
        self._check_layouts("| D-003 | EG-S3 |\n", "| D-003 | EG-S3 |\n| D-003 | EG-S2 |\n")


# ---------------------------------------------------------------------------
# IC1-01: the coverage declaration ends at the first ``：`` (C14, C15)
# ---------------------------------------------------------------------------

AC01_LINE = "**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：描述一。"
AC02_LINE = "**[EG-S2-AC02]** 覆盖 EG-S2-C03：描述二。"

# (label, original acceptance line, rewritten line); every rewrite keeps the declaration.
COLON_CASES = [
    (
        "CASE 1: per-clause notes after the declaration",
        AC01_LINE,
        "**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：EG-S2-C01：缺键时报错；EG-S2-C02：多键时报错。",
    ),
    (
        "CASE 2: clause ID directly followed by ： later in the text",
        AC02_LINE,
        "**[EG-S2-AC02]** 覆盖 EG-S2-C03：描述二，另见EG-S2-C01：说明。",
    ),
    (
        "CASE 2 after a two-ID declaration, other spec's clause ID",
        AC01_LINE,
        "**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：描述一，参见EG-S1-C01：说明。",
    ),
]


def _colon_fixture(original, rewritten):
    fx = S.Fixture()
    fx.edit(S.S2, original, rewritten)
    return fx


class CoverageDeclarationEndTests(S.TraceTestCase):
    """C14: only IDs in ``覆盖 <条款 ID>[、<条款 ID>…]：`` count, i.e. up to the first ``：``."""

    # eg:ac EG-S2-AC14
    # eg:ac EG-S2-AC15
    # IC1-01
    def test_ac14_clause_ids_after_the_declaration_do_not_break_it(self):
        for label, original, rewritten in COLON_CASES:
            with self.subTest(label):
                root = self.build(_colon_fixture(original, rewritten))
                for mode in ("spec", "tests"):
                    res = self.trace(root, "--mode", mode)
                    self.assertNoCheck(res, "EG-S2-C14", "EG-S2-C15")
                    self.assertPass(res)

    # eg:ac EG-S2-AC14
    # eg:ac EG-S2-AC15
    # IC1-01
    def test_ac14_declaration_end_holds_for_any_spec_id_form(self):
        for name, pairs in RENAMINGS:
            for label, original, rewritten in COLON_CASES:
                with self.subTest(name + ": " + label):
                    root = self.build(_renamed(_colon_fixture(original, rewritten), pairs))
                    for mode in ("spec", "tests"):
                        res = self.trace(root, "--mode", mode)
                        self.assertNoCheck(res, "EG-S2-C14", "EG-S2-C15")
                        self.assertPass(res)

    # eg:ac EG-S2-AC14
    # eg:ac EG-S2-AC15
    # IC1-01
    def test_ac14_clause_named_after_the_first_colon_is_not_covered(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S2-C05]** 第五条（D-002）。")
        fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C03：EG-S2-C05：说明。\n- [EG-S2-AC04-W1] 错误实现。")
        fx.add_marker("EG-S2-AC04")
        res = self.trace(self.build(fx), "--mode", "spec")
        # The declaration is "EG-S2-C03", which exists; EG-S2-C05 stays uncovered.
        self.assertFail(res, "EG-S2-C15")
        self.assertNoCheck(res, "EG-S2-C14")


if __name__ == "__main__":
    unittest.main()
