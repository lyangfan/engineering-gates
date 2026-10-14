"""EG-S2 acceptance tests: configuration, decision registry, design, spec map.

Run: /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v
"""

import json
import os
import unittest

try:
    from . import support as S
except ImportError:  # discovered with the test directory as top level
    import support as S


CONFIG_ERROR_CHECKS = ("EG-S2-C01", "EG-S2-C19")


def _write_config(root, cfg):
    with open(os.path.join(str(root), S.CONFIG), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False)


class ConfigTests(S.TraceTestCase):
    """C01: eg.json shape, path rules and glob semantics."""

    # eg:ac EG-S2-AC01
    def test_ac01_config_errors_exit_2_and_name_the_field(self):
        def absolute(cfg, root):
            cfg["decisions"] = os.path.join(str(root), S.DECISIONS)

        cases = [
            ("missing tests key", "tests", lambda c, r: c.pop("tests")),
            ("unknown key", "bogus_key", lambda c, r: c.__setitem__("bogus_key", "x")),
            ("empty design", "design", lambda c, r: c.__setitem__("design", [])),
            ("absolute path", "decisions", absolute),
            (
                "dot-dot path",
                "spec_map",
                lambda c, r: c.__setitem__("spec_map", "docs/design/../design/spec-map.md"),
            ),
            (
                "dot-dot pattern",
                "specs",
                lambda c, r: c.__setitem__("specs", ["docs/../docs/specs/*.md"]),
            ),
            ("design not an array", "design", lambda c, r: c.__setitem__("design", S.DESIGN)),
            ("wrong schema", "schema", lambda c, r: c.__setitem__("schema", "eg-config/v0")),
        ]
        for label, field, mutate in cases:
            with self.subTest(label):
                root = self.build()
                cfg = S.base_config()
                mutate(cfg, root)
                _write_config(root, cfg)
                res = self.trace(root, "--mode", "tests")
                # W EG-S2-AC01-W1: a defaulted missing key would give exit 0, not 2.
                self.assertError(res)
                for check in res.checks:
                    self.assertIn(check, CONFIG_ERROR_CHECKS, res.describe())
                self.assertMentions(res, field)

    # eg:ac EG-S2-AC01
    def test_ac01_globstar_matches_top_level_and_nested_files(self):
        nested = "docs/specs/sub/EG-S2-beta.md"

        def fixture():
            fx = S.Fixture()
            fx.config["specs"] = ["docs/specs/**/*.md"]
            fx.files[nested] = fx.files.pop(S.S2)
            return fx

        # Both spec files must be found, otherwise their test markers would be
        # reported as referring to non-existent specs.
        self.assertPass(self.trace(self.build(fixture()), "--mode", "tests"))

        for rel in (S.S1, nested):
            with self.subTest(defect_in=rel):
                fx = fixture()
                prefix = "EG-S1" if rel == S.S1 else "EG-S2"
                fx.add_clause(rel, "**[%s-C09]** 没有任何引用的条款。" % prefix)
                fx.add_ac(rel, "**[%s-AC09]** 覆盖 %s-C09：描述。\n- [%s-AC09-W1] 错误实现。" % (prefix, prefix, prefix))
                self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C11")

    # eg:ac EG-S2-AC01
    def test_ac01_trailing_globstar_collects_files(self):
        # W EG-S2-AC01-W2: pathlib.Path.glob on 3.9 returns only directories for
        # a trailing "**", so zero files are collected and C24 fails the run.
        fx = S.Fixture()
        fx.config["specs"] = ["docs/specs/**"]
        self.assertPass(self.trace(self.build(fx), "--mode", "spec"))

        fx = S.Fixture()
        fx.config["tests"] = ["tests/**"]
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))

    # eg:ac EG-S2-AC01
    def test_ac01_root_defaults_to_current_directory(self):
        root = self.build()
        self.assertPass(self.run_eg(["--mode", "tests"], cwd=root))

        fx = S.Fixture()
        fx.remove_marker("EG-S2-AC03")
        root = self.build(fx)
        self.assertFail(self.run_eg(["--mode", "tests"], cwd=root), "EG-S2-C17")


class EncodingAndMatchTests(S.TraceTestCase):
    """C24: UTF-8 with optional BOM; zero-match patterns."""

    # eg:ac EG-S2-AC24
    def test_ac24_bom_is_accepted_in_every_input_file(self):
        fx = S.Fixture()
        fx.bom = True
        root = self.build(fx)
        for mode in ("design", "spec", "tests"):
            with self.subTest(mode=mode):
                self.assertPass(self.trace(root, "--mode", mode))

    # eg:ac EG-S2-AC24
    def test_ac24_bom_registry_is_valid_json(self):
        fx = S.Fixture()
        data = json.dumps(fx.registry, ensure_ascii=False).encode("utf-8")
        fx.raw[S.DECISIONS] = b"\xef\xbb\xbf" + data
        # W EG-S2-AC24-W1: reading without BOM support makes this an invalid-JSON error (exit 2).
        self.assertPass(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC24
    def test_ac24_gbk_design_is_input_error(self):
        fx = S.Fixture()
        data = S.DESIGN_TEXT.encode("gbk")
        with self.assertRaises(UnicodeDecodeError):
            data.decode("utf-8")
        fx.raw[S.DESIGN] = data
        self.assertError(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC24
    def test_ac24_zero_matches_fail(self):
        fx = S.Fixture()
        fx.config["specs"] = ["docs/specs/*.txt"]
        # W EG-S2-AC24-W2: treating zero matches as success would exit 0.
        self.assertFail(self.trace(self.build(fx), "--mode", "spec"), "EG-S2-C24")

        fx = S.Fixture()
        fx.config["tests"] = ["tests/**/*.txt"]
        self.assertFail(self.trace(self.build(fx), "--mode", "tests"), "EG-S2-C24")

    # eg:ac EG-S2-AC24
    def test_ac24_zero_matches_counted_over_all_patterns(self):
        fx = S.Fixture()
        fx.config["specs"] = ["docs/specs/*.md", "docs/nothing/*.md"]
        fx.config["tests"] = ["tests/**/*.py", "nothing/**/*.py"]
        self.assertPass(self.trace(self.build(fx), "--mode", "tests"))


class RegistryTests(S.TraceTestCase):
    """C02-C04: decision registry format and relations."""

    # eg:ac EG-S2-AC02
    def test_ac02_entry_problems_fail_with_exit_1(self):
        def duplicate(fx):
            fx.add_decision(S.decision("D-003"))

        def short_id(fx):
            fx.add_decision(S.decision("D-7", status="withdrawn"))

        def missing_date(fx):
            del fx.decision("D-003")["date"]

        def extra_note(fx):
            fx.decision("D-003")["note"] = "多余字段"

        def empty_statement(fx):
            fx.decision("D-003")["statement"] = ""

        def bad_date(fx):
            fx.decision("D-003")["date"] = "2026/10/14"

        def relation_not_array(fx):
            fx.decision("D-007")["refines"] = "D-003"

        cases = [
            # W EG-S2-AC02-W2: keeping the later duplicate silently gives no C02 failure.
            ("duplicate id", duplicate),
            ("id D-7", short_id),
            # W EG-S2-AC02-W1: missing / unknown fields must be reported.
            ("missing date", missing_date),
            ("extra note field", extra_note),
            ("empty statement", empty_statement),
            ("malformed date", bad_date),
            ("relation not an array", relation_not_array),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                fx = S.Fixture()
                mutate(fx)
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C02")

    # eg:ac EG-S2-AC02
    def test_ac02_wrong_registry_schema_is_input_error(self):
        fx = S.Fixture()
        fx.registry["schema"] = "eg-decisions/v0"
        self.assertError(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC02
    def test_ac02_four_digit_id_is_valid(self):
        fx = S.Fixture()
        fx.add_decision(S.decision("D-1000"))
        fx.edit(S.DESIGN, "- 流程决定见 D-007。\n", "- 流程决定见 D-007。\n- 大编号决定 D-1000。\n")
        fx.edit(S.SPEC_MAP, "| D-008 |", "| D-1000 | 不进 spec：夹具 |\n| D-008 |")
        root = self.build(fx)
        # W EG-S2-AC02-W3: accepting exactly three digits would report D-1000.
        self.assertPass(self.trace(root, "--mode", "design"))
        self.assertPass(self.trace(root, "--mode", "spec"))

    # eg:ac EG-S2-AC03
    def test_ac03_unknown_status_values_fail(self):
        # W EG-S2-AC03-W1: accepting any non-empty string would not report these.
        for status in ("deferred", "pending", "Active"):
            with self.subTest(status=status):
                fx = S.Fixture()
                fx.decision("D-003")["status"] = status
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C03")

    # eg:ac EG-S2-AC04
    def test_ac04_relation_violations_fail(self):
        def dangling_refines(fx):
            fx.decision("D-003")["refines"] = ["D-099"]

        def dangling_amended_by(fx):
            fx.decision("D-003")["amended_by"] = ["D-098"]

        def dangling_supersedes(fx):
            fx.decision("D-005")["supersedes"] = ["D-004", "D-097"]

        def self_reference(fx):
            fx.decision("D-003")["refines"] = ["D-003"]

        def orphan_superseded(fx):
            fx.decision("D-006")["status"] = "superseded"

        def superseded_still_active(fx):
            fx.decision("D-005")["supersedes"] = ["D-004", "D-003"]

        def amends_without_amended_by(fx):
            del fx.decision("D-001")["amended_by"]

        def amended_by_without_amends(fx):
            del fx.decision("D-002")["amends"]

        cases = [
            # W EG-S2-AC04-W2: dangling ids in non-supersedes fields must be reported.
            ("dangling refines", dangling_refines),
            ("dangling amended_by", dangling_amended_by),
            ("dangling supersedes", dangling_supersedes),
            ("self reference", self_reference),
            ("superseded without superseder", orphan_superseded),
            # W EG-S2-AC04-W3: a superseded-but-active decision is the only defect here.
            ("superseded but still active", superseded_still_active),
            ("one-way amends", amends_without_amended_by),
            ("one-way amended_by", amended_by_without_amends),
        ]
        for label, mutate in cases:
            with self.subTest(label):
                fx = S.Fixture()
                mutate(fx)
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C04")

    # eg:ac EG-S2-AC04
    def test_ac04_supersedes_cycle_fails(self):
        fx = S.Fixture()
        fx.add_decision(S.decision("D-010", status="superseded", supersedes=["D-011"]))
        fx.add_decision(S.decision("D-011", status="superseded", supersedes=["D-010"]))
        res = self.trace(self.build(fx), "--mode", "design")
        # W EG-S2-AC04-W1: only checking direct self-loops leaves this fixture
        # with no failure at all (both decisions are consistently superseded).
        self.assertFail(res, "EG-S2-C04")


class DesignTests(S.TraceTestCase):
    """C05-C06: decision references in design files."""

    # eg:ac EG-S2-AC05
    def test_ac05_all_design_files_are_scanned(self):
        # D-008 is referenced only in the second design file.
        # W EG-S2-AC05-W1: scanning only the first file reports D-008 here.
        self.assertPass(self.trace(self.build(), "--mode", "design"))

    # eg:ac EG-S2-AC05
    def test_ac05_unreferenced_active_decision_fails(self):
        fx = S.Fixture()
        fx.edit(S.DESIGN_EXTRA, "全局约束见 D-008。", "全局约束另见附表。")
        res = self.trace(self.build(fx), "--mode", "design")
        self.assertFail(res, "EG-S2-C05")
        self.assertEqual(res.count("EG-S2-C05"), 1, res.describe())

    # eg:ac EG-S2-AC06
    def test_ac06_bad_references_in_design_fail(self):
        cases = [
            ("unknown id", "另见 D-099。"),
            # W EG-S2-AC06-W1: D-004 exists but is superseded.
            ("superseded id", "旧决定 D-004。"),
            ("withdrawn id", "撤回的 D-006。"),
        ]
        for label, text in cases:
            with self.subTest(label):
                fx = S.Fixture()
                fx.files[S.DESIGN] += "\n" + text + "\n"
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C06")

    # eg:ac EG-S2-AC06
    def test_ac06_both_unknown_and_superseded_reported(self):
        fx = S.Fixture()
        fx.files[S.DESIGN] += "\n另见 D-099。\n\n旧决定 D-004。\n"
        res = self.trace(self.build(fx), "--mode", "design")
        self.assertFail(res, "EG-S2-C06")
        self.assertGreaterEqual(res.count("EG-S2-C06"), 2, res.describe())


CHECK_TABLE_WITH_UNKNOWN_COLUMN = (
    "3. 定档清单",
    "| 清单项 | EG-S1 | EG-S2 | EG-S3 | EG-S4 |\n"
    "|---|---|---|---|---|\n"
    "| 公共 API / wire | 是：CLI（EG-S1-C01） | 否 | 是：执行探针 | 否 |\n"
    "| 并发 / 恢复 | 否 | 否 | 否 | 否 |\n",
)


class SpecMapTests(S.TraceTestCase):
    """C25, C07-C09: spec map tables."""

    # eg:ac EG-S2-AC25
    def test_ac25_missing_section_or_table_fails(self):
        cases = [
            ("no checklist section", [S.SEC_LIST, S.SEC_ALLOC, S.SEC_TIER]),
            ("allocation section without table", [S.SEC_LIST, ("2. 决定分配", "（暂无）\n"), S.SEC_CHECK, S.SEC_TIER]),
            ("tier section without table", [S.SEC_LIST, S.SEC_ALLOC, S.SEC_CHECK, ("4. 档位", "（暂无）\n")]),
        ]
        for label, sections in cases:
            with self.subTest(label):
                fx = S.Fixture()
                fx.files[S.SPEC_MAP] = S.render_map(sections)
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C25")

    # eg:ac EG-S2-AC25
    def test_ac25_sections_located_by_heading_text(self):
        # The base map uses numbered headings ("3. 定档清单") and has an unrelated
        # first table; it must pass.
        self.assertPass(self.trace(self.build(), "--mode", "design"))

        fx = S.Fixture()
        fx.files[S.SPEC_MAP] = S.render_map(
            [(h.split(". ", 1)[1], b) for h, b in S.MAP_SECTIONS]
        )
        self.assertPass(self.trace(self.build(fx), "--mode", "design"))

        # W EG-S2-AC25-W1: locating tables by section order reads the wrong table here.
        fx = S.Fixture()
        fx.files[S.SPEC_MAP] = S.render_map([S.SEC_TIER, S.SEC_CHECK, S.SEC_ALLOC, S.SEC_LIST])
        self.assertPass(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC25
    def test_ac25_checklist_column_not_in_tier_table_fails(self):
        fx = S.Fixture()
        fx.files[S.SPEC_MAP] = S.render_map(
            [S.SEC_LIST, S.SEC_ALLOC, CHECK_TABLE_WITH_UNKNOWN_COLUMN, S.SEC_TIER]
        )
        res = self.trace(self.build(fx), "--mode", "design")
        self.assertFail(res)
        self.assertTrue(
            set(res.checks) & {"EG-S2-C25", "EG-S2-C09"},
            "expected a C25 (or C09) failure\n" + res.describe(),
        )

    # eg:ac EG-S2-AC07
    def test_ac07_allocation_errors_fail(self):
        cases = [
            ("active decision missing", "| D-003 | EG-S3 |\n", ""),
            ("decision in two rows", "| D-001 | EG-S1 |\n", "| D-001 | EG-S1 |\n| D-001 | EG-S2 |\n"),
            ("empty not-in-spec reason", "| D-007 | 不进 spec：流程决定 |", "| D-007 | 不进 spec： |"),
        ]
        for label, old, new in cases:
            with self.subTest(label):
                fx = S.Fixture()
                fx.edit(S.SPEC_MAP, old, new)
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C07")

    # eg:ac EG-S2-AC07
    def test_ac07_global_and_not_in_spec_rows_are_allocations(self):
        # Base map: D-007 is "不进 spec：…", D-008 is "全局约束：…；EG-S2 首先落实".
        root = self.build()
        # W EG-S2-AC07-W1: treating these rows as unallocated fails design mode.
        self.assertPass(self.trace(root, "--mode", "design"))
        # W EG-S2-AC07-W2: counting EG-S2 from the global note as an allocation makes
        # C12 demand a D-008 reference in the EG-S2 spec.
        self.assertPass(self.trace(root, "--mode", "spec"))

    # eg:ac EG-S2-AC08
    def test_ac08_tier_errors_fail(self):
        cases = [
            # W EG-S2-AC08-W1: a "是" for EG-S2 while its rule result is 标准.
            ("yes but rule result standard", S.CHECK_ROW_API,
             "| 公共 API / wire | 是：CLI（EG-S1-C01） | 是：标记语法（EG-S2-C01） | 是：执行探针 |"),
            ("all no but rule result strict", S.TIER_ROW_S2, "| EG-S2 | 严格 | 严格 |  |"),
            ("downgrade without reason", S.TIER_ROW_S3, "| EG-S3 | 严格 | 标准 |  |"),
            ("invalid confirmed tier", S.TIER_ROW_S1, "| EG-S1 | 严格 | 超严格 | 写 git |"),
            ("invalid rule result", S.TIER_ROW_S2, "| EG-S2 | 中等 | 标准 |  |"),
        ]
        for label, old, new in cases:
            with self.subTest(label):
                fx = S.Fixture()
                fx.edit(S.SPEC_MAP, old, new)
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C08")

    # eg:ac EG-S2-AC08
    def test_ac08_upgrade_without_reason_passes(self):
        fx = S.Fixture()
        fx.edit(S.SPEC_MAP, S.TIER_ROW_S2, "| EG-S2 | 标准 | 严格 |  |")
        # W EG-S2-AC08-W2: requiring a reason whenever tiers differ reports this.
        self.assertPass(self.trace(self.build(fx), "--mode", "design"))

    # eg:ac EG-S2-AC09
    def test_ac09_checklist_cell_errors_fail(self):
        cases = [
            ("existing spec, no clause id", "是：CLI（EG-S1-C01）", "是：CLI"),
            # W EG-S2-AC09-W2: EG-S1-C99 is well-formed but does not exist.
            ("existing spec, unknown clause id", "是：CLI（EG-S1-C01）", "是：CLI（EG-S1-C99）"),
            ("existing spec, other spec's clause", "是：CLI（EG-S1-C01）", "是：CLI（EG-S2-C01）"),
            ("missing spec, empty note", "是：执行探针", "是："),
            ("neither no nor yes", "是：执行探针", "可能"),
            ("yes without colon", "是：执行探针", "是"),
        ]
        for label, old, new in cases:
            with self.subTest(label):
                fx = S.Fixture()
                fx.edit(S.SPEC_MAP, S.CHECK_ROW_API, S.CHECK_ROW_API.replace(old, new))
                self.assertFail(self.trace(self.build(fx), "--mode", "design"), "EG-S2-C09")

    # eg:ac EG-S2-AC09
    def test_ac09_missing_spec_only_needs_non_empty_note(self):
        # EG-S3 has no spec file; its "是：执行探针" cell contains no clause id.
        # W EG-S2-AC09-W1: requiring a clause id here fails the base map.
        root = self.build()
        self.assertPass(self.trace(root, "--mode", "design"))
        self.assertPass(self.trace(root, "--mode", "spec"))


if __name__ == "__main__":
    unittest.main()
