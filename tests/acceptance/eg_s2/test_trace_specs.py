"""EG-S2 acceptance tests: spec clauses, acceptance blocks, test markers, code exclusion.

Run: /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v
"""

import unittest

try:
    from . import support as S
except ImportError:  # discovered with the test directory as top level
    import support as S


def _with_clause(clause_text, ac_text=None):
    """Base fixture plus an extra EG-S2 clause C05 covered by a new AC04."""
    fx = S.Fixture()
    fx.add_clause(S.S2, clause_text)
    if ac_text is None:
        ac_text = "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。"
    if ac_text:
        fx.add_ac(S.S2, ac_text)
    fx.add_marker("EG-S2-AC04")
    return fx


class ClauseNamingTests(S.TraceTestCase):
    """C10: spec file names and clause markers."""

    # eg:ac EG-S2-AC10
    def test_ac10_clause_ids_unique_per_spec_only(self):
        # EG-S1-C01 and EG-S2-C01 both exist in the base fixture.
        # W EG-S2-AC10-W1: comparing ids across specs reports them as duplicates.
        self.assertPass(self.trace(self.build(), "--mode", "spec"))

    # eg:ac EG-S2-AC10
    def test_ac10_duplicate_clause_in_one_spec_fails(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S2-C01]** 重复的条款（D-002）。")
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C10")
        self.assertHasFailureAt(res, "EG-S2-C10", S.S2)

    # eg:ac EG-S2-AC10
    def test_ac10_clause_prefix_must_equal_file_spec(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S3-C05]** 前缀与文件不符（D-002）。")
        # W EG-S2-AC10-W2: EG-S3 is in the map, so a map-membership check accepts it.
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C10")

    # eg:ac EG-S2-AC10
    def test_ac10_file_prefix_not_in_map_fails(self):
        rel = "docs/specs/EG-S9-extra.md"
        fx = S.Fixture()
        fx.files[rel] = "# 多余的 spec\n"
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C10")
        self.assertHasFailureAt(res, "EG-S2-C10", rel)

    # eg:ac EG-S2-AC10
    def test_ac10_prefix_must_be_followed_by_dash_or_dot(self):
        # EG-S10-extra.md does not belong to EG-S1; EG-S1's own file is removed so a
        # mis-assignment cannot surface as a "two files" error instead.
        fx = S.Fixture()
        fx.files[S.S1] = None
        fx.files["docs/specs/EG-S10-extra.md"] = "# 多余的 spec\n"
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C10")

        fx = S.Fixture()
        fx.files["docs/specs/EG-S2.md"] = fx.files.pop(S.S2)
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))

    # eg:ac EG-S2-AC10
    def test_ac10_two_files_for_one_spec_fail(self):
        fx = S.Fixture()
        fx.files["docs/specs/EG-S2-other.md"] = "# 另一份 EG-S2\n"
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C10")


class BlockBoundaryTests(S.TraceTestCase):
    """C26: clause and acceptance block boundaries."""

    # eg:ac EG-S2-AC26
    def test_ac26_reference_in_following_list_counts(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 条款正文没有引用，见下列各项：\n"
            "\n"
            "- 依据 D-002。\n"
            "- 另见说明。"
        )
        # W EG-S2-AC26-W1: ending the block at the blank line misses the list reference.
        self.assertPass(self.trace(self.build(fx), "--mode", "spec"))

    # eg:ac EG-S2-AC26
    def test_ac26_hash_lines_in_fence_are_not_headings(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 条款正文含示例：\n"
            "\n"
            "```text\n"
            "# 这不是标题\n"
            "## 这也不是\n"
            "```\n"
            "\n"
            "示例之后引用 D-002。"
        )
        # W EG-S2-AC26-W2: treating "# ..." inside the fence as a heading ends the
        # block early and leaves the clause unclassified.
        self.assertPass(self.trace(self.build(fx), "--mode", "spec"))

    # eg:ac EG-S2-AC26
    def test_ac26_text_after_heading_not_in_clause(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 没有引用的条款。\n"
            "\n"
            "## 2.9 附注\n"
            "\n"
            "此处提到 D-002 与 F-03。"
        )
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C11")
        self.assertEqual(res.count("EG-S2-C11"), 1, res.describe())

    # eg:ac EG-S2-AC26
    def test_ac26_next_clause_marker_ends_block(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 没有引用的条款。\n"
            "**[EG-S2-C06]** 引用 D-002 的条款。",
            "**[EG-S2-AC04]** 覆盖 EG-S2-C05、EG-S2-C06：描述。\n- [EG-S2-AC04-W1] 错误实现。",
        )
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C11")
        self.assertEqual(res.count("EG-S2-C11"), 1, res.describe())

    # eg:ac EG-S2-AC26
    def test_ac26_acceptance_block_continues_after_blank_line(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 条款（D-002）。",
            "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n\n- [EG-S2-AC04-W1] 错误实现。",
        )
        self.assertPass(self.trace(self.build(fx), "--mode", "spec"))


class ClassificationTests(S.TraceTestCase):
    """C11-C13: clause classification, active references, freeze."""

    # eg:ac EG-S2-AC11
    def test_ac11_unclassified_clause_fails(self):
        cases = [
            ("no reference at all", "**[EG-S2-C05]** 没有任何引用。"),
            # W EG-S2-AC11-W1: "D-"/"F-" followed by a non-digit is not a reference.
            ("non-numeric D-/F- text", "**[EG-S2-C05]** 参见 D-级 约定与 F-score 指标。"),
            # W EG-S2-AC11-W2: undefined AUTHOR-CHOICE spelling.
            ("undefined author-choice", "**[EG-S2-C05]** 待定。[AUTHOR-CHOICE:maybe]"),
        ]
        for label, clause in cases:
            with self.subTest(label):
                res = self.trace(self.build(_with_clause(clause)), "--mode", "spec")
                self.assertFail(res, "EG-S2-C11")
                self.assertEqual(res.count("EG-S2-C11"), 1, res.describe())

    # eg:ac EG-S2-AC11
    # eg:ac EG-S2-AC22
    def test_ac11_markers_inside_backticks_do_not_classify(self):
        fx = _with_clause("**[EG-S2-C05]** 写法为 `[AUTHOR-CHOICE:local]`，引用写作 `D-002` 或 `F-01`。")
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C11")

    # eg:ac EG-S2-AC11
    def test_ac11_substantive_marker_classifies_without_freeze(self):
        fx = _with_clause("**[EG-S2-C05]** 实质选择。[AUTHOR-CHOICE:substantive]")
        self.assertPass(self.trace(self.build(fx), "--mode", "spec"))

    # eg:ac EG-S2-AC12
    def test_ac12_only_superseded_reference_reports_c11_and_c12(self):
        fx = _with_clause("**[EG-S2-C05]** 只引用被替代的 D-004。")
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C11", "EG-S2-C12")
        self.assertEqual(res.count("EG-S2-C11"), 1, res.describe())
        self.assertEqual(res.count("EG-S2-C12"), 1, res.describe())

    # eg:ac EG-S2-AC12
    def test_ac12_mixed_reference_reports_c12_only(self):
        fx = _with_clause("**[EG-S2-C05]** 引用 D-002 与被替代的 D-004。")
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C12")
        self.assertNoCheck(res, "EG-S2-C11")

    # eg:ac EG-S2-AC12
    def test_ac12_allocated_decision_must_be_cited_in_a_clause(self):
        fx = S.Fixture()
        fx.edit(S.S2, "**[EG-S2-C01]** 第一条（D-002）。", "**[EG-S2-C01]** 第一条（F-03）。")
        fx.add_clause(S.S2, "## 2.9 说明\n\n本节提到 D-002，但不在任何条款块内。")
        # D-002 still appears in the intro line and under a heading, outside clauses.
        # W EG-S2-AC12-W1: counting whole-file references would accept this.
        res = self.trace(self.build(fx), "--mode", "spec")
        self.assertFail(res, "EG-S2-C12")

    # eg:ac EG-S2-AC12
    def test_ac12_allocation_to_spec_without_file_is_not_checked(self):
        # D-003 is allocated to EG-S3, which has no spec file.
        # W EG-S2-AC12-W2: checking EG-S3's allocation fails these runs.
        root = self.build()
        self.assertPass(self.trace(root, "--mode", "spec"))
        self.assertPass(self.trace(root, "--mode", "tests"))

    # eg:ac EG-S2-AC13
    def test_ac13_freeze_rejects_substantive_marker(self):
        fx = _with_clause("**[EG-S2-C05]** 实质选择尚未决定。[AUTHOR-CHOICE:substantive]")
        root = self.build(fx)
        self.assertPass(self.trace(root, "--mode", "spec"))
        # W EG-S2-AC13-W1: only warning under --freeze would exit 0.
        self.assertFail(self.trace(root, "--mode", "spec", "--freeze"), "EG-S2-C13")

    # eg:ac EG-S2-AC13
    def test_ac13_freeze_lists_local_choices(self):
        root = self.build()
        res = self.trace(root, "--mode", "spec", "--freeze")
        self.assertPass(res)
        got = sorted(
            (c.get("spec"), c.get("clause"), c.get("path"), c.get("line"))
            for c in res.report["local_choices"]
        )
        want = sorted([
            ("EG-S1", "EG-S1-C03", S.S1, S.line_of(S.S1_TEXT, "**[EG-S1-C03]**")),
            ("EG-S2", "EG-S2-C04", S.S2, S.line_of(S.S2_TEXT, "**[EG-S2-C04]**")),
        ])
        self.assertEqual(got, want, res.describe())

    # eg:ac EG-S2-AC13
    # eg:ac EG-S2-AC22
    def test_ac13_markers_in_backticks_ignored_by_freeze(self):
        fx = _with_clause(
            "**[EG-S2-C05]** 标记写法为 `[AUTHOR-CHOICE:substantive]` 与 `[AUTHOR-CHOICE:local]`（D-002）。"
        )
        res = self.trace(self.build(fx), "--mode", "spec", "--freeze")
        # W EG-S2-AC22-W1: counting the quoted substantive marker fails the freeze.
        self.assertPass(res)
        clauses = sorted(c.get("clause") for c in res.report["local_choices"])
        self.assertEqual(clauses, ["EG-S1-C03", "EG-S2-C04"], res.describe())


class AcceptanceTests(S.TraceTestCase):
    """C14-C16: acceptance coverage and wrong implementations."""

    # eg:ac EG-S2-AC14
    def test_ac14_coverage_of_unknown_clause_fails(self):
        fx = S.Fixture()
        fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C99：描述。\n- [EG-S2-AC04-W1] 错误实现。")
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C14")

    # eg:ac EG-S2-AC14
    def test_ac14_coverage_of_other_spec_clause_fails(self):
        fx = S.Fixture()
        fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S1-C01：跨 spec 覆盖。\n- [EG-S2-AC04-W1] 错误实现。")
        # W EG-S2-AC14-W1: EG-S1-C01 exists, but in another spec.
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C14")

    # eg:ac EG-S2-AC14
    def test_ac14_duplicate_acceptance_id_fails(self):
        fx = S.Fixture()
        fx.add_ac(S.S2, "**[EG-S2-AC01]** 覆盖 EG-S2-C01：重复的验收。\n- [EG-S2-AC01-W2] 错误实现。")
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C14")

    # eg:ac EG-S2-AC14
    # eg:ac EG-S2-AC15
    def test_ac14_mention_outside_declaration_is_not_coverage(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S2-C05]** 新条款（D-002）。")
        fx.edit(
            S.S2,
            "覆盖 EG-S2-C01、EG-S2-C02：描述一。",
            "覆盖 EG-S2-C01、EG-S2-C02：描述一，并提及 EG-S2-C05。",
        )
        res = self.trace(self.build(fx), "--mode", "spec")
        # W EG-S2-AC14-W2: counting every clause id in the block would cover C05.
        self.assertFail(res, "EG-S2-C15")
        self.assertEqual(res.count("EG-S2-C15"), 1, res.describe())

    # eg:ac EG-S2-AC15
    def test_ac15_uncovered_clause_fails(self):
        fx = S.Fixture()
        fx.add_clause(S.S2, "**[EG-S2-C05]** 没有验收覆盖的条款（D-002）。")
        res = self.trace(self.build(fx), "--mode", "spec")
        # W EG-S2-AC15-W1: the spec has acceptances, yet C05 is not covered.
        self.assertFail(res, "EG-S2-C15")
        self.assertEqual(res.count("EG-S2-C15"), 1, res.describe())

    # eg:ac EG-S2-AC16
    def test_ac16_wrong_implementation_errors_fail(self):
        def no_items(fx):
            fx.add_clause(S.S2, "**[EG-S2-C05]** 条款（D-002）。")
            fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：没有错误实现。")

        def unlabeled_item(fx):
            fx.add_clause(S.S2, "**[EG-S2-C05]** 条款（D-002）。")
            fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- 错误实现：没有编号。")

        def misplaced_item(fx):
            fx.edit(
                S.S2,
                "- [EG-S2-AC02-W2] 错误实现二。\n",
                "- [EG-S2-AC02-W2] 错误实现二。\n- [EG-S2-AC01-W2] 放错位置的错误实现。\n",
            )

        def duplicate_item(fx):
            fx.edit(
                S.S2,
                "- [EG-S2-AC03-W1] 错误实现一。\n",
                "- [EG-S2-AC03-W1] 错误实现一。\n- [EG-S2-AC03-W1] 重复编号。\n",
            )

        cases = [
            ("acceptance without wrong implementation", no_items),
            # W EG-S2-AC16-W1: an item without an id is not a wrong implementation.
            ("unlabeled item only", unlabeled_item),
            # W EG-S2-AC16-W2: assigning by id prefix would file this under AC01 silently.
            ("item with another acceptance's prefix", misplaced_item),
            ("two W1 in one acceptance", duplicate_item),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                fx = S.Fixture()
                mutate(fx)
                self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C16")


class TestMarkerTests(S.TraceTestCase):
    """C17: test markers in test files."""

    # eg:ac EG-S2-AC17
    def test_ac17_missing_marker_reported_only_in_tests_mode(self):
        fx = S.Fixture()
        fx.remove_marker("EG-S2-AC03")
        root = self.build(fx)
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")
        # W EG-S2-AC17-W1: spec mode must not look at test files.
        self.assertPass(self.trace(root, "--mode", "spec"))

    # eg:ac EG-S2-AC17
    def test_ac17_unknown_acceptance_id_in_tests_fails(self):
        fx = S.Fixture()
        fx.add_marker("EG-S2-AC99")
        root = self.build(fx)
        self.assertFail(self.trace(root, "--mode", "tests"), "EG-S2-C17")
        self.assertPass(self.trace(root, "--mode", "spec"))

    # eg:ac EG-S2-AC17
    def test_ac17_marker_in_string_is_recognised(self):
        fx = S.Fixture()
        fx.remove_marker("EG-S2-AC02")
        fx.files[S.T2] += '\nLABEL = "' + S.ac_marker("EG-S2-AC02") + '"\n'
        # W EG-S2-AC17-W2: matching only function names misses string / comment /
        # docstring markers (all markers in this fixture are of those kinds).
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))


class CodeExclusionTests(S.TraceTestCase):
    """C22: inline code and fenced code are excluded in design and spec files."""

    # eg:ac EG-S2-AC22
    def test_ac22_backticked_decision_in_design_not_counted(self):
        fx = S.Fixture()
        fx.edit(S.DESIGN_EXTRA, "全局约束见 D-008。", "全局约束见 `D-008`。")
        res = self.trace(self.build(fx), "--mode", "design")
        # W EG-S2-AC22-W1: counting the quoted id would leave D-008 "referenced".
        self.assertFail(res, "EG-S2-C05")

    # eg:ac EG-S2-AC22
    def test_ac22_fenced_decisions_in_design_ignored(self):
        fx = S.Fixture()
        fx.files[S.DESIGN] += "\n```text\n示例：D-099 与 D-004\n```\n\n行内示例 `D-006`。\n"
        # W EG-S2-AC22-W1: the quoted D-099 / D-004 / D-006 would trigger C06.
        self.assertPass(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC22
    def test_ac22_markers_in_spec_code_are_not_clauses(self):
        fx = S.Fixture()
        fx.add_clause(
            S.S2,
            "**[EG-S2-C05]** 条款写法示例如下（D-002）：\n"
            "\n"
            "```markdown\n"
            "**[EG-S2-C77]** 示例条款，没有引用。\n"
            "**[EG-S2-AC77]** 覆盖 EG-S2-C88：示例验收。\n"
            "- [EG-S2-AC01-W1] 示例错误实现。\n"
            "```\n"
            "\n"
            "`**[EG-S2-C78]**` 是行内示例。",
        )
        fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。")
        fx.add_marker("EG-S2-AC04")
        # W EG-S2-AC22-W1: treating the examples as real markers yields C10/C11/C14/C15/C16 failures.
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))

    # eg:ac EG-S2-AC22
    def test_ac22_backticked_marker_in_test_file_counts(self):
        fx = S.Fixture()
        fx.remove_marker("EG-S2-AC03")
        fx.files[S.T2] += "# 见 `" + S.ac_marker("EG-S2-AC03") + "`\n"
        # W EG-S2-AC22-W2: applying code exclusion to test files misses this marker.
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))


if __name__ == "__main__":
    unittest.main()
