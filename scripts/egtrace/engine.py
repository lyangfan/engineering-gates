"""Read-only static trace checker.

Ambiguities resolved against the spec text (see the final report for the list):

- ``..`` in a configured path is a path segment, not an arbitrary substring.
- Decision references in design files use the registry id shape (``D-`` plus
  at least three digits). Clause classification accepts ``D-`` plus one or
  more digits, and a reference that is not an active decision does not
  satisfy EG-S2-C11.
- Without ``--spec``, every test marker is checked: an acceptance id that
  does not exist in any existing spec file is EG-S2-C17. With ``--spec``,
  only markers whose id prefix is a selected spec are checked (EG-S2-C23).
- ``local_choices[].line`` is the line of the ``[AUTHOR-CHOICE:local]`` marker.
- A checklist spec id that is absent from the tier table is EG-S2-C25.
- A line-start clause or acceptance marker with fewer than two digits is not
  a marker.
"""

import glob
import json
import os
import re
import sys


REPORT_SCHEMA = "eg-trace-report/v1"
CONFIG_SCHEMA = "eg-config/v1"
DECISIONS_SCHEMA = "eg-decisions/v1"

CONFIG_KEYS = ("schema", "decisions", "design", "spec_map", "specs", "tests")
DECISION_REQUIRED = ("id", "statement", "status", "source", "date")
DECISION_OPTIONAL = ("supersedes", "amends", "refines", "amended_by")
DECISION_FIELDS = DECISION_REQUIRED + DECISION_OPTIONAL
RELATION_FIELDS = DECISION_OPTIONAL
STATUSES = ("active", "superseded", "withdrawn")
TIERS = ("轻量", "标准", "严格")
TIER_RANK = {"轻量": 0, "标准": 1, "严格": 2}
TIER_HEADERS = ("spec", "规则结果", "确认档位", "理由")
ALLOC_HEADERS = ("决定", "去向")

ID_RE = re.compile(r"^D-\d{3,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OPEN_FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,})([^`]*)\s*$")
CLOSE_FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,})\s*$")
HEADING_RE = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)\s*$")
# Spec ids come from the tier table. Markers use a generic prefix; ``]`` and
# whitespace are excluded only so the marker and table grammars stay parseable.
CLAUSE_RE = re.compile(r"^\*\*\[([^\]\s]+?)-C(\d{2,})\]\*\*(.*)$")
ACCEPTANCE_RE = re.compile(r"^\*\*\[([^\]\s]+?)-AC(\d{2,})\]\*\*(.*)$")
# C14 ends the coverage declaration at the first fullwidth colon. The id
# class must not include that colon, or a later "clause id：" on the same
# line is swallowed into the declaration.
COVERAGE_RE = re.compile(
    r"^\s*覆盖\s*((?:[^\s、：]+-C\d{2,})(?:\s*、\s*[^\s、：]+-C\d{2,})*)\s*："
)
DESIGN_ID_RE = re.compile(r"(?<![A-Za-z0-9])(D-\d{3,})(?![A-Za-z0-9])")
DEC_REF_RE = re.compile(r"(?<![A-Za-z0-9])(D-\d+)(?![A-Za-z0-9])")
FACT_REF_RE = re.compile(r"(?<![A-Za-z0-9])(F-\d+)(?![A-Za-z0-9])")
WI_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\[([^\]]+)\]")
WI_ID_RE = re.compile(r"^(.+-AC\d{2,})-W(\d+)$")
MARKER_RE = re.compile(
    r"(?<![A-Za-z0-9_])eg:ac[ \t]+([^\s]+?-AC\d{2,})(?![A-Za-z0-9])"
)
CLAUSE_SUFFIX_RE = re.compile(r"^(.+)-C\d{2,}$")
ACCEPTANCE_SUFFIX_RE = re.compile(r"^(.+)-AC\d{2,}$")
LOCAL_MARK = "[AUTHOR-CHOICE:local]"
SUBST_MARK = "[AUTHOR-CHOICE:substantive]"
YES_PREFIX = "是："
NOT_IN_SPEC = "不进 spec："
GLOBAL_RULE = "全局约束："
NUMBERED_HEADING_RE = re.compile(r"^\d+(?:\.\d+)*\.\s+")


class InputError(Exception):
    def __init__(self, failures):
        Exception.__init__(self, failures[0]["message"] if failures else "input error")
        self.failures = failures


class Decision(object):
    def __init__(self, did, status, relations, line):
        self.id = did
        self.status = status
        self.line = line
        self.supersedes = relations.get("supersedes", [])
        self.amends = relations.get("amends", [])
        self.refines = relations.get("refines", [])
        self.amended_by = relations.get("amended_by", [])


class Block(object):
    def __init__(self, kind, spec_prefix, full_id, start_line, rest, prefix_ok):
        self.kind = kind
        self.spec_prefix = spec_prefix
        self.full_id = full_id
        self.start_line = start_line
        self.rest = rest
        self.prefix_ok = prefix_ok
        self.lines = []


class ParsedFile(object):
    def __init__(self, path, blocks, masked_lines):
        self.path = path
        self.blocks = blocks
        self.masked_lines = masked_lines

    def clauses(self):
        return [b for b in self.blocks if b.kind == "clause" and b.prefix_ok]

    def acceptances(self):
        return [b for b in self.blocks if b.kind == "acceptance" and b.prefix_ok]


def problem(check, message, path=None, line=None):
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        line = None
    if isinstance(path, str):
        path = path.replace("\\", "/")
    return {"check": check, "path": path, "line": line, "message": message}


def emit(mode, specs, freeze, failures, local_choices, code):
    if code == 0:
        result = "pass"
    elif code == 1:
        result = "fail"
    else:
        result = "error"
    if not freeze or code == 2:
        local_choices = []
    report = {
        "schema": REPORT_SCHEMA,
        "mode": mode,
        "specs": list(specs),
        "freeze": bool(freeze),
        "result": result,
        "failures": failures,
        "local_choices": local_choices,
    }
    raw = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()
    _write_summary(report)
    return code


def _write_summary(report):
    lines = ["追溯检查：%s（%d 项）" % (report["result"], len(report["failures"]))]
    for item in report["failures"]:
        loc = item.get("path") or "-"
        if item.get("line"):
            loc = "%s:%s" % (loc, item["line"])
        lines.append("%s %s %s" % (item["check"], loc, item["message"]))
    for choice in report["local_choices"]:
        lines.append(
            "local %s %s:%s"
            % (choice["clause"], choice["path"], choice["line"])
        )
    sys.stderr.buffer.write(("\n".join(lines) + "\n").encode("utf-8"))
    sys.stderr.buffer.flush()


def usage_error(message, mode=None, freeze=False):
    return emit(
        mode,
        [],
        freeze,
        [problem("EG-S2-C18", message)],
        [],
        2,
    )


def _take_value(argv, index, key):
    if index + 1 >= len(argv) or argv[index + 1].startswith("--"):
        return None, index, "参数 %s 缺少取值" % key
    return argv[index + 1], index + 2, None


def parse_trace_args(argv):
    """Return ``(args, error_message)``. ``args`` is None when parsing fails."""
    mode = None
    freeze = False
    specs = []
    root = None
    i = 0
    while i < len(argv):
        token = argv[i]
        key = token
        inline = None
        if token.startswith("--") and "=" in token[2:]:
            key, inline = token.split("=", 1)
        if key in ("--mode", "--spec", "--root"):
            if inline is None:
                value, i, err = _take_value(argv, i, key)
                if err:
                    return None, err
            else:
                if inline == "":
                    return None, "参数 %s 缺少取值" % key
                value = inline
                i += 1
            if key == "--mode":
                mode = value
            elif key == "--spec":
                specs.append(value)
            else:
                root = value
            continue
        if key == "--freeze":
            if inline is not None:
                return None, "参数 --freeze 不接受取值"
            freeze = True
            i += 1
            continue
        return None, "无法识别的参数 %s" % token
    return {"mode": mode, "freeze": freeze, "specs": specs, "root": root}, None


def combination_error(args):
    mode = args["mode"]
    if mode not in ("design", "spec", "tests"):
        if mode is None:
            return "缺少 --mode"
        return "--mode 的值 %s 无法识别" % mode
    if args["freeze"] and mode != "spec":
        return "--freeze 只能与 --mode spec 同用"
    if args["specs"] and mode == "design":
        return "--spec 不能与 --mode design 同用"
    return None


def report_mode(args):
    mode = args["mode"] if args else None
    if mode in ("design", "spec", "tests"):
        return mode
    return None


def _has_dotdot(path):
    return ".." in re.split(r"[\\/]", path)


def _config_problem(message):
    return problem("EG-S2-C01", message, path="eg.json")


def _check_rel_path(field, value, kind):
    """Return an error message, or None when the path or pattern is acceptable."""
    if not isinstance(value, str) or value.strip() == "":
        return "eg.json 字段 %s 必须为非空字符串" % field
    if os.path.isabs(value):
        return "eg.json 字段 %s 不得为绝对路径" % field
    if _has_dotdot(value):
        if kind == "pattern":
            return "eg.json 字段 %s 的模式不得含 .." % field
        return "eg.json 字段 %s 不得含 .." % field
    return None


def load_config(root):
    path = os.path.join(root, "eg.json")
    if not os.path.isfile(path):
        raise InputError([_config_problem("eg.json 缺失")])
    try:
        text = _read_text(path)
    except UnicodeError:
        raise InputError(
            [problem("EG-S2-C24", "eg.json 无法按 UTF-8 解码", path="eg.json")]
        )
    try:
        data = json.loads(text)
    except ValueError:
        raise InputError([_config_problem("eg.json 不是合法 JSON")])
    if not isinstance(data, dict):
        raise InputError([_config_problem("eg.json 必须为 JSON 对象")])
    failures = []
    keys = set(data.keys())
    required = set(CONFIG_KEYS)
    for key in sorted(required - keys):
        failures.append(_config_problem("eg.json 缺少字段 %s" % key))
    for key in sorted(keys - required):
        failures.append(_config_problem("eg.json 含有未知字段 %s" % key))
    if failures:
        raise InputError(failures)
    schema = data.get("schema")
    if schema != CONFIG_SCHEMA:
        failures.append(
            _config_problem("eg.json 字段 schema 的值必须为 %s" % CONFIG_SCHEMA)
        )
    decisions = data.get("decisions")
    spec_map = data.get("spec_map")
    for field, value in (("decisions", decisions), ("spec_map", spec_map)):
        message = _check_rel_path(field, value, "path")
        if message:
            failures.append(_config_problem(message))
    for field in ("design", "specs", "tests"):
        value = data.get(field)
        if not isinstance(value, list) or not value:
            failures.append(_config_problem("eg.json 字段 %s 必须为非空数组" % field))
            continue
        kind = "path" if field == "design" else "pattern"
        for item in value:
            message = _check_rel_path(field, item, kind)
            if message:
                failures.append(_config_problem(message))
    if failures:
        raise InputError(failures)
    return data


def _read_text(path):
    with open(path, "rb") as handle:
        data = handle.read()
    return data.decode("utf-8-sig")


def _read_listed(root, rel, check, label):
    rel_path = rel.replace("\\", "/")
    full = os.path.join(root, rel)
    if not os.path.isfile(full):
        raise InputError(
            [problem(check, "%s不存在：%s" % (label, rel_path), path=rel_path)]
        )
    try:
        return _read_text(full), rel_path
    except UnicodeError:
        raise InputError(
            [problem("EG-S2-C24", "%s无法按 UTF-8 解码：%s" % (label, rel_path), path=rel_path)]
        )
    except OSError as exc:
        raise InputError(
            [problem("EG-S2-C19", "%s无法读取：%s" % (label, exc), path=rel_path)]
        )


def expand_patterns(root, patterns):
    """Match ``glob.glob(os.path.join(root, pattern), recursive=True)``."""
    found = []
    seen = set()
    root_norm = os.path.normpath(root)
    for pattern in patterns:
        matches = glob.glob(os.path.join(root, pattern), recursive=True)
        for match in matches:
            if not os.path.isfile(match):
                continue
            rel = os.path.relpath(os.path.normpath(match), root_norm)
            rel = rel.replace(os.sep, "/")
            if rel.startswith("../") or rel == "..":
                continue
            if rel not in seen:
                seen.add(rel)
                found.append(rel)
    found.sort()
    return found


def _line_of_nth(text, needle, nth):
    start = 0
    index = -1
    for _ in range(nth):
        index = text.find(needle, start)
        if index < 0:
            return None
        start = index + len(needle)
    return text.count("\n", 0, index) + 1


def _id_line(text, did, nth):
    for needle in ('"id": "%s"' % did, '"id":"%s"' % did):
        line = _line_of_nth(text, needle, nth)
        if line:
            return line
    return None


def _valid_date(value):
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    year, month, day = (int(part) for part in value.split("-"))
    if month < 1 or month > 12 or day < 1:
        return False
    lengths = [31, 29 if _leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return day <= lengths[month - 1]


def _leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def load_registry(text, path):
    """Return ``(by_id, order, entry_failures)`` or raise InputError."""
    try:
        data = json.loads(text)
    except ValueError:
        raise InputError(
            [problem("EG-S2-C02", "决策登记不是合法 JSON", path=path)]
        )
    if not isinstance(data, dict):
        raise InputError(
            [problem("EG-S2-C02", "决策登记顶层必须为对象", path=path)]
        )
    keys = set(data.keys())
    if keys != {"schema", "decisions"}:
        extra = sorted(keys - {"schema", "decisions"})
        missing = sorted({"schema", "decisions"} - keys)
        detail = []
        if missing:
            detail.append("缺少 %s" % "、".join(missing))
        if extra:
            detail.append("多余字段 %s" % "、".join(extra))
        raise InputError(
            [
                problem(
                    "EG-S2-C02",
                    "决策登记顶层只能包含 schema 与 decisions（%s）" % "；".join(detail),
                    path=path,
                )
            ]
        )
    if data.get("schema") != DECISIONS_SCHEMA:
        raise InputError(
            [
                problem(
                    "EG-S2-C02",
                    "决策登记 schema 必须为 %s" % DECISIONS_SCHEMA,
                    path=path,
                )
            ]
        )
    entries = data.get("decisions")
    if not isinstance(entries, list):
        raise InputError(
            [problem("EG-S2-C02", "决策登记的 decisions 必须为数组", path=path)]
        )
    by_id = {}
    order = []
    failures = []
    seen = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            failures.append(
                problem(
                    "EG-S2-C02",
                    "决策登记第 %d 条不是对象" % (index + 1),
                    path=path,
                )
            )
            continue
        did = entry.get("id")
        id_ok = isinstance(did, str) and ID_RE.match(did) is not None
        nth = None
        line = None
        if isinstance(did, str):
            seen[did] = seen.get(did, 0) + 1
            nth = seen[did]
            line = _id_line(text, did, nth)
        if not isinstance(did, str) or not id_ok:
            shown = did if isinstance(did, str) else ("第 %d 条" % (index + 1))
            failures.append(
                problem(
                    "EG-S2-C02",
                    "决定编号不合法：%s（须为 D- 加至少三位数字）" % shown,
                    path=path,
                    line=line,
                )
            )
        if isinstance(did, str) and id_ok and did in by_id:
            failures.append(
                problem(
                    "EG-S2-C02",
                    "决定编号重复：%s" % did,
                    path=path,
                    line=line,
                )
            )
            _entry_shape(entry, did, path, line, failures, keep=False)
            continue
        relations = _entry_shape(entry, did if id_ok else None, path, line, failures, keep=True)
        if not id_ok:
            continue
        status = entry.get("status")
        if isinstance(status, str) and status not in STATUSES:
            failures.append(
                problem(
                    "EG-S2-C03",
                    "决定 %s 的 status 不合法：%s" % (did, status),
                    path=path,
                    line=line,
                )
            )
        decision = Decision(did, status if isinstance(status, str) else None, relations, line)
        by_id[did] = decision
        order.append(decision)
    return by_id, order, failures


def _entry_shape(entry, did, path, line, failures, keep):
    label = did or "该决定"
    relations = {}
    keys = set(entry.keys())
    for key in DECISION_REQUIRED:
        if key not in entry:
            failures.append(
                problem("EG-S2-C02", "决定 %s 缺少字段 %s" % (label, key), path=path, line=line)
            )
    for key in sorted(keys - set(DECISION_FIELDS)):
        failures.append(
            problem("EG-S2-C02", "决定 %s 含有未知字段 %s" % (label, key), path=path, line=line)
        )
    for key in ("statement", "source"):
        value = entry.get(key)
        if key not in entry:
            continue
        if not isinstance(value, str) or value == "":
            failures.append(
                problem(
                    "EG-S2-C02",
                    "决定 %s 的 %s 必须为非空字符串" % (label, key),
                    path=path,
                    line=line,
                )
            )
    if "date" in entry and not _valid_date(entry.get("date")):
        failures.append(
            problem(
                "EG-S2-C02",
                "决定 %s 的 date 必须形如 YYYY-MM-DD" % label,
                path=path,
                line=line,
            )
        )
    if "status" in entry and not isinstance(entry.get("status"), str):
        failures.append(
            problem(
                "EG-S2-C02",
                "决定 %s 的 status 必须为字符串" % label,
                path=path,
                line=line,
            )
        )
    for key in RELATION_FIELDS:
        if key not in entry:
            relations[key] = []
            continue
        value = entry.get(key)
        if not isinstance(value, list):
            failures.append(
                problem(
                    "EG-S2-C02",
                    "决定 %s 的 %s 必须为数组" % (label, key),
                    path=path,
                    line=line,
                )
            )
            relations[key] = []
            continue
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                failures.append(
                    problem(
                        "EG-S2-C02",
                        "决定 %s 的 %s 含有非字符串元素" % (label, key),
                        path=path,
                        line=line,
                    )
                )
                continue
            cleaned.append(item)
        relations[key] = cleaned
    if not keep:
        return {}
    return relations


def check_relations(by_id, order, path, failures):
    for decision in order:
        for field in RELATION_FIELDS:
            for target in getattr(decision, field):
                if target == decision.id:
                    failures.append(
                        problem(
                            "EG-S2-C04",
                            "决定 %s 的 %s 引用了自身" % (decision.id, field),
                            path=path,
                            line=decision.line,
                        )
                    )
                elif target not in by_id:
                    failures.append(
                        problem(
                            "EG-S2-C04",
                            "决定 %s 的 %s 引用了不存在的编号 %s" % (decision.id, field, target),
                            path=path,
                            line=decision.line,
                        )
                    )
    targets = {}
    graph = {}
    for decision in order:
        for target in decision.supersedes:
            if target == decision.id or target not in by_id:
                continue
            targets.setdefault(target, []).append(decision.id)
            graph.setdefault(decision.id, []).append(target)
    for decision in order:
        if decision.status == "superseded" and decision.id not in targets:
            failures.append(
                problem(
                    "EG-S2-C04",
                    "决定 %s 的 status 为 superseded，但没有任何决定的 supersedes 引用它" % decision.id,
                    path=path,
                    line=decision.line,
                )
            )
        if decision.id in targets and decision.status != "superseded":
            failures.append(
                problem(
                    "EG-S2-C04",
                    "决定 %s 被 supersedes 引用，但其 status 不是 superseded"
                    % decision.id,
                    path=path,
                    line=decision.line,
                )
            )
    for decision in order:
        for target in decision.amends:
            if target == decision.id or target not in by_id:
                continue
            if decision.id not in by_id[target].amended_by:
                failures.append(
                    problem(
                        "EG-S2-C04",
                        "决定 %s 的 amends 含 %s，但对方的 amended_by 没有成对引用"
                        % (decision.id, target),
                        path=path,
                        line=decision.line,
                    )
                )
        for target in decision.amended_by:
            if target == decision.id or target not in by_id:
                continue
            if decision.id not in by_id[target].amends:
                failures.append(
                    problem(
                        "EG-S2-C04",
                        "决定 %s 的 amended_by 含 %s，但对方的 amends 没有成对引用"
                        % (decision.id, target),
                        path=path,
                        line=decision.line,
                    )
                )
    _supersedes_cycles(graph, by_id, path, failures)


def _supersedes_cycles(graph, by_id, path, failures):
    visiting = set()
    visited = set()

    def walk(node, stack):
        visiting.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            if nxt in visiting:
                start = stack.index(nxt)
                cycle = stack[start:] + [nxt]
                failures.append(
                    problem(
                        "EG-S2-C04",
                        "supersedes 成环：%s" % " → ".join(cycle),
                        path=path,
                        line=by_id[node].line if node in by_id else None,
                    )
                )
            elif nxt not in visited:
                walk(nxt, stack)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in list(graph.keys()):
        if node not in visited:
            walk(node, [])


def mask_inline(core):
    chars = list(core)
    index = 0
    length = len(chars)
    while index < length:
        if chars[index] != "`":
            index += 1
            continue
        end = index
        while end < length and chars[end] == "`":
            end += 1
        tick = end - index
        cursor = end
        closed = False
        while cursor < length:
            if chars[cursor] != "`":
                cursor += 1
                continue
            run = cursor
            while run < length and chars[run] == "`":
                run += 1
            if run - cursor == tick:
                for pos in range(end, cursor):
                    chars[pos] = " "
                index = run
                closed = True
                break
            cursor = run
        if not closed:
            index = end
    return "".join(chars)


def _split_ending(line):
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[:-1], line[-1]
    return line, ""


def mask_code(text):
    """Blank fenced and inline code without changing line breaks or length."""
    masked = []
    in_fence = False
    open_tick = 0
    for line in text.splitlines(keepends=True):
        core, ending = _split_ending(line)
        if not in_fence:
            opened = OPEN_FENCE_RE.match(core)
            if opened:
                in_fence = True
                open_tick = len(opened.group(1))
                masked.append(line)
                continue
            masked.append(mask_inline(core) + ending)
            continue
        closed = CLOSE_FENCE_RE.match(core)
        if closed and len(closed.group(1)) >= open_tick:
            in_fence = False
            masked.append(line)
        else:
            masked.append((" " * len(core)) + ending)
    return "".join(masked)


def normalize_heading(title):
    title = title.strip()
    title = re.sub(r"\s+#+\s*$", "", title).strip()
    title = NUMBERED_HEADING_RE.sub("", title).strip()
    return title


def split_sections(text):
    lines = text.splitlines()
    headings = []
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match:
            continue
        headings.append((index, len(match.group(1)), normalize_heading(match.group(2))))
    sections = {}
    for pos, (index, level, title) in enumerate(headings):
        end = len(lines)
        for later, later_level, _title in headings[pos + 1 :]:
            if later_level <= level:
                end = later
                break
        if title not in sections:
            body = [(number + 1, lines[number]) for number in range(index + 1, end)]
            sections[title] = {"line": index + 1, "body": body}
    return sections


def _pipe_row(line):
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2


def _split_cells(line):
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def _delimiter_row(line):
    if not _pipe_row(line):
        return False
    cells = _split_cells(line)
    if not cells:
        return False
    return all(re.match(r"^:?-+:?$", cell) for cell in cells)


def extract_table(body):
    """Return ``(header_line, headers, rows)`` or None. Rows are ``(line, cells)``."""
    index = 0
    while index < len(body):
        line_no, text = body[index]
        if (
            _pipe_row(text)
            and index + 1 < len(body)
            and _delimiter_row(body[index + 1][1])
        ):
            headers = _split_cells(text)
            rows = []
            cursor = index + 2
            while cursor < len(body) and _pipe_row(body[cursor][1]):
                rows.append((body[cursor][0], _split_cells(body[cursor][1])))
                cursor += 1
            return line_no, headers, rows
        index += 1
    return None


def _spec_id_usable(spec_id):
    """True when a tier-table cell can be used as a spec id.

    The id is the cell text. Whitespace and ``]`` are rejected because clause
    markers and Markdown cells cannot carry them; this is not a spelling rule.
    """
    if spec_id == "":
        return False
    if "]" in spec_id:
        return False
    for ch in spec_id:
        if ch.isspace():
            return False
    return True


def _marked_spec(full_id, suffix_re):
    """Return the spec id of ``<spec>-Cdd`` or ``<spec>-ACdd``."""
    match = suffix_re.match(full_id)
    if match:
        return match.group(1)
    return None


def _dest_boundary(text, index):
    if index >= len(text):
        return True
    ch = text[index]
    return ch.isspace() or ch in "、（("


def _match_known_spec(rest, ordered):
    for sid in ordered:
        if rest.startswith(sid) and _dest_boundary(rest, len(sid)):
            return sid
    return None


def _raw_spec_token(rest):
    index = 0
    while index < len(rest) and not _dest_boundary(rest, index):
        index += 1
    if index == 0:
        return None
    return rest[:index]


def parse_destination(cell, spec_ids):
    """Return ``(kind, ids, error)``. ``kind`` is specs, not_in_spec, or global.

    Spec ids are matched from the tier table (longest first). A token that is
    not in that set is still returned so the caller can report it as unknown.
    """
    text = cell.strip()
    if text.startswith(NOT_IN_SPEC):
        reason = text[len(NOT_IN_SPEC) :].strip()
        if reason == "":
            return "not_in_spec", [], "不进 spec 的理由为空"
        return "not_in_spec", [], None
    if text.startswith(GLOBAL_RULE):
        return "global", [], None
    ids = []
    rest = text
    if rest == "":
        return "specs", [], "去向为空"
    ordered = sorted(spec_ids, key=len, reverse=True)
    while rest:
        rest = rest.lstrip()
        if rest == "":
            break
        matched = _match_known_spec(rest, ordered)
        if matched is None:
            raw = _raw_spec_token(rest)
            if raw is None:
                return "specs", [], "去向无法识别：%s" % text
            ids.append(raw)
            rest = rest[len(raw) :]
        else:
            ids.append(matched)
            rest = rest[len(matched) :]
        rest = rest.lstrip()
        if rest.startswith("（"):
            end = rest.find("）")
            if end < 0:
                return "specs", [], "去向的括注未闭合：%s" % text
            rest = rest[end + 1 :].lstrip()
        elif rest.startswith("("):
            end = rest.find(")")
            if end < 0:
                return "specs", [], "去向的括注未闭合：%s" % text
            rest = rest[end + 1 :].lstrip()
        if rest.startswith("、"):
            rest = rest[1:].strip()
            if rest == "":
                return "specs", [], "去向在分隔符后缺少 spec ID：%s" % text
            continue
        if rest == "":
            break
        return "specs", [], "去向无法识别：%s" % text
    if not ids:
        return "specs", [], "去向为空"
    return "specs", ids, None


def parse_map(text):
    sections = split_sections(text)
    model = {
        "sections": sections,
        "spec_ids": [],
        "tier_rows": [],
        "alloc_rows": [],
        "check_headers": [],
        "check_rows": [],
        "structural": [],
    }
    for title in ("决定分配", "定档清单", "档位"):
        if title not in sections:
            model["structural"].append(
                problem("EG-S2-C25", "spec 地图缺少章节：%s" % title, path=None)
            )
    alloc = sections.get("决定分配")
    checklist = sections.get("定档清单")
    tier = sections.get("档位")
    alloc_table = extract_table(alloc["body"]) if alloc else None
    check_table = extract_table(checklist["body"]) if checklist else None
    tier_table = extract_table(tier["body"]) if tier else None
    if alloc and alloc_table is None:
        model["structural"].append(
            problem("EG-S2-C25", "决定分配章节缺少表格", path=None, line=alloc["line"])
        )
    if checklist and check_table is None:
        model["structural"].append(
            problem("EG-S2-C25", "定档清单章节缺少表格", path=None, line=checklist["line"])
        )
    if tier and tier_table is None:
        model["structural"].append(
            problem("EG-S2-C25", "档位章节缺少表格", path=None, line=tier["line"])
        )
    if tier_table is not None:
        _line, headers, rows = tier_table
        if tuple(headers) != TIER_HEADERS:
            model["structural"].append(
                problem(
                    "EG-S2-C25",
                    "档位表的列必须为 spec、规则结果、确认档位、理由",
                    path=None,
                    line=_line,
                )
            )
        else:
            seen = set()
            for line, cells in rows:
                spec_id = cells[0] if cells else ""
                if spec_id in seen:
                    model["structural"].append(
                        problem("EG-S2-C25", "档位表 spec ID 重复：%s" % spec_id, path=None, line=line)
                    )
                seen.add(spec_id)
                if not _spec_id_usable(spec_id):
                    model["structural"].append(
                        problem(
                            "EG-S2-C25",
                            "档位表 spec ID 不能为空或包含空白或 ]：%s" % spec_id,
                            path=None,
                            line=line,
                        )
                    )
                else:
                    model["spec_ids"].append(spec_id)
                model["tier_rows"].append((line, cells))
    if check_table is not None:
        _line, headers, rows = check_table
        model["check_headers"] = headers
        model["check_rows"] = rows
        if not headers or headers[0] != "清单项":
            model["structural"].append(
                problem("EG-S2-C25", "定档清单表第一列必须为清单项", path=None, line=_line)
            )
    if alloc_table is not None:
        _line, headers, rows = alloc_table
        if tuple(headers) != ALLOC_HEADERS:
            model["structural"].append(
                problem("EG-S2-C07", "决定分配表的列必须为决定、去向", path=None, line=_line)
            )
        else:
            model["alloc_rows"] = rows
    return model


def _cell(cells, index):
    if index < len(cells):
        return cells[index]
    return ""


def evaluate_map(model, by_id, clause_ids, map_path, decisions_path, failures):
    for item in model["structural"]:
        item = dict(item)
        item["path"] = map_path
        failures.append(item)
    spec_set = set(model["spec_ids"])
    header_ids = []
    headers_ok = bool(model["check_headers"]) and model["check_headers"][0] == "清单项"
    if headers_ok:
        header_ids = model["check_headers"][1:]
        if set(header_ids) != spec_set:
            missing = sorted(spec_set - set(header_ids))
            extra = sorted(set(header_ids) - spec_set)
            detail = []
            if extra:
                detail.append("清单多出 %s" % "、".join(extra))
            if missing:
                detail.append("清单缺少 %s" % "、".join(missing))
            failures.append(
                problem(
                    "EG-S2-C25",
                    "定档清单的 spec 列与档位表不一致（%s）" % "；".join(detail),
                    path=map_path,
                )
            )
    allocations = {sid: set() for sid in model["spec_ids"]}
    counts = {}
    alloc_lines = {}
    if model["alloc_rows"]:
        for line, cells in model["alloc_rows"]:
            did = _cell(cells, 0)
            dest = _cell(cells, 1)
            if not ID_RE.match(did):
                failures.append(
                    problem(
                        "EG-S2-C07",
                        "决定分配表的决定编号不合法：%s" % did,
                        path=map_path,
                        line=line,
                    )
                )
                continue
            counts[did] = counts.get(did, 0) + 1
            alloc_lines.setdefault(did, []).append(line)
            _kind, ids, error = parse_destination(dest, model["spec_ids"])
            if error:
                failures.append(
                    problem("EG-S2-C07", "决定 %s 的去向：%s" % (did, error), path=map_path, line=line)
                )
                continue
            if did not in by_id:
                failures.append(
                    problem(
                        "EG-S2-C07",
                        "决定分配表引用了不存在的决定 %s" % did,
                        path=map_path,
                        line=line,
                    )
                )
            for sid in ids:
                if sid not in spec_set:
                    failures.append(
                        problem(
                            "EG-S2-C07",
                            "决定 %s 的去向含有地图中不存在的 spec %s" % (did, sid),
                            path=map_path,
                            line=line,
                        )
                    )
                    continue
                allocations.setdefault(sid, set()).add(did)
    for decision in by_id.values():
        if decision.status != "active":
            continue
        count = counts.get(decision.id, 0)
        if count != 1:
            if count == 0:
                message = "active 决定 %s 没有出现在决定分配表中" % decision.id
                failures.append(
                    problem(
                        "EG-S2-C07",
                        message,
                        path=decisions_path,
                        line=decision.line,
                    )
                )
            else:
                message = "active 决定 %s 在决定分配表中出现了 %d 次" % (decision.id, count)
                lines = alloc_lines.get(decision.id, [])
                # The extra row is in the allocation table, so line stays in map_path.
                dup_line = lines[1] if len(lines) > 1 else None
                failures.append(problem("EG-S2-C07", message, path=map_path, line=dup_line))
    if headers_ok and model["tier_rows"]:
        columns = {}
        for offset, sid in enumerate(header_ids):
            columns[sid] = offset + 1
        tier_by_spec = {}
        for line, cells in model["tier_rows"]:
            sid = _cell(cells, 0)
            if sid not in spec_set:
                continue
            tier_by_spec[sid] = (line, _cell(cells, 1), _cell(cells, 2), _cell(cells, 3))
        for sid, (line, rule, confirmed, reason) in tier_by_spec.items():
            rule_ok = rule in TIER_RANK
            confirmed_ok = confirmed in TIER_RANK
            if not rule_ok:
                failures.append(
                    problem(
                        "EG-S2-C08",
                        "spec %s 的规则结果不是合法档位：%s" % (sid, rule),
                        path=map_path,
                        line=line,
                    )
                )
            if not confirmed_ok:
                failures.append(
                    problem(
                        "EG-S2-C08",
                        "spec %s 的确认档位不是合法档位：%s" % (sid, confirmed),
                        path=map_path,
                        line=line,
                    )
                )
            column = columns.get(sid)
            yes = False
            all_no = column is not None and bool(model["check_rows"])
            clause_note_re = None
            if sid in clause_ids:
                clause_note_re = re.compile(
                    r"(?<![A-Za-z0-9])" + re.escape(sid) + r"-C\d{2,}(?![A-Za-z0-9])"
                )
            if column is None:
                all_no = False
            else:
                for row_line, cells in model["check_rows"]:
                    cell = _cell(cells, column)
                    if cell == "否":
                        continue
                    all_no = False
                    if cell.startswith(YES_PREFIX):
                        note = cell[len(YES_PREFIX) :].strip()
                        if note == "":
                            failures.append(
                                problem(
                                    "EG-S2-C09",
                                    "spec %s 的“是”缺少说明" % sid,
                                    path=map_path,
                                    line=row_line,
                                )
                            )
                        else:
                            yes = True
                            if clause_note_re is not None:
                                found = [
                                    match.group(0) for match in clause_note_re.finditer(note)
                                ]
                                if not any(item in clause_ids[sid] for item in found):
                                    failures.append(
                                        problem(
                                            "EG-S2-C09",
                                            "spec %s 的说明中没有该 spec 实际存在的条款 ID：%s"
                                            % (sid, note),
                                            path=map_path,
                                            line=row_line,
                                        )
                                    )
                    else:
                        failures.append(
                            problem(
                                "EG-S2-C09",
                                "spec %s 的清单单元格必须为“否”或以“是：”开头：%s" % (sid, cell),
                                path=map_path,
                                line=row_line,
                            )
                        )
            if rule_ok and yes and rule != "严格":
                failures.append(
                    problem(
                        "EG-S2-C08",
                        "spec %s 的清单含有“是”，规则结果必须为严格" % sid,
                        path=map_path,
                        line=line,
                    )
                )
            if rule_ok and all_no and not yes and rule == "严格":
                failures.append(
                    problem(
                        "EG-S2-C08",
                        "spec %s 的清单全为“否”，规则结果不得为严格" % sid,
                        path=map_path,
                        line=line,
                    )
                )
            if rule_ok and confirmed_ok and TIER_RANK[confirmed] < TIER_RANK[rule]:
                if reason.strip() == "":
                    failures.append(
                        problem(
                            "EG-S2-C08",
                            "spec %s 的确认档位低于规则结果，理由不得为空" % sid,
                            path=map_path,
                            line=line,
                        )
                    )
    return allocations


def _assign_spec(filename, spec_ids):
    best = None
    for sid in spec_ids:
        if filename.startswith(sid + "-") or filename.startswith(sid + "."):
            if best is None or len(sid) > len(best):
                best = sid
    return best


def parse_spec_file(text, path, owner):
    masked = mask_code(text)
    masked_lines = masked.splitlines()
    blocks = []
    current = None
    for index, line in enumerate(masked_lines):
        line_no = index + 1
        if HEADING_RE.match(line):
            current = None
            continue
        clause = CLAUSE_RE.match(line)
        acceptance = ACCEPTANCE_RE.match(line)
        match = clause or acceptance
        if match:
            kind = "clause" if clause else "acceptance"
            prefix = match.group(1)
            full_id = "%s-%s%s" % (prefix, "C" if clause else "AC", match.group(2))
            current = Block(
                kind,
                prefix,
                full_id,
                line_no,
                match.group(3),
                prefix == owner,
            )
            current.lines.append((line_no, line))
            blocks.append(current)
            continue
        if current is not None:
            current.lines.append((line_no, line))
    return ParsedFile(path, blocks, masked_lines)


def build_docs(spec_files, texts, spec_ids):
    docs = {sid: [] for sid in spec_ids}
    unknown = []
    for rel in spec_files:
        base = rel.split("/")[-1]
        owner = _assign_spec(base, spec_ids)
        if owner is None:
            unknown.append(rel)
            continue
        docs.setdefault(owner, []).append(parse_spec_file(texts[rel], rel, owner))
    clause_ids = {}
    for sid, files in docs.items():
        found = set()
        for parsed in files:
            for block in parsed.clauses():
                found.add(block.full_id)
        if files:
            clause_ids[sid] = found
    return docs, unknown, clause_ids


def _block_text_has(block, token):
    lines = []
    for line_no, text in block.lines:
        if token in text:
            lines.append(line_no)
    return lines


def _refs(block, pattern):
    found = []
    seen = set()
    for _line, text in block.lines:
        for match in pattern.finditer(text):
            value = match.group(1)
            if value not in seen:
                seen.add(value)
                found.append(value)
    return found


def _cites(block, did):
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(did) + r"(?![A-Za-z0-9])")
    for _line, text in block.lines:
        if pattern.search(text):
            return True
    return False


def check_design(design_texts, active_ids, by_id, decisions_path, failures):
    found = set()
    for rel, text in design_texts:
        masked = mask_code(text)
        for index, line in enumerate(masked.splitlines()):
            for match in DESIGN_ID_RE.finditer(line):
                did = match.group(1)
                found.add(did)
                if did not in active_ids:
                    if did in by_id:
                        detail = "决定 %s 的 status 为 %s，不是 active" % (did, by_id[did].status)
                    else:
                        detail = "决定编号 %s 不存在" % did
                    failures.append(
                        problem("EG-S2-C06", detail, path=rel, line=index + 1)
                    )
    for did in sorted(active_ids - found):
        line = by_id[did].line if did in by_id else None
        failures.append(
            problem(
                "EG-S2-C05",
                "active 决定 %s 未在设计稿中出现" % did,
                path=decisions_path,
                line=line,
            )
        )


def check_spec_bodies(docs, unknown, selected, report_unknown, active_ids, allocations, freeze, failures, local_choices):
    if report_unknown:
        for rel in unknown:
            failures.append(
                problem(
                    "EG-S2-C10",
                    "spec 文件名不以地图中的 spec ID 加 “-” 或 “.” 开头",
                    path=rel,
                )
            )
    for sid in selected:
        files = docs.get(sid, [])
        if len(files) > 1:
            shown = "、".join(parsed.path for parsed in files)
            failures.append(
                problem(
                    "EG-S2-C10",
                    "spec %s 对应多个文件：%s" % (sid, shown),
                    path=files[1].path,
                )
            )
        seen_clauses = {}
        seen_acceptances = {}
        real_clauses = []
        real_acceptances = []
        for parsed in files:
            for block in parsed.blocks:
                if block.kind == "clause" and not block.prefix_ok:
                    failures.append(
                        problem(
                            "EG-S2-C10",
                            "条款 %s 的前缀与文件所属 spec %s 不一致" % (block.full_id, sid),
                            path=parsed.path,
                            line=block.start_line,
                        )
                    )
                if block.kind == "acceptance" and not block.prefix_ok:
                    failures.append(
                        problem(
                            "EG-S2-C14",
                            "验收 %s 的前缀与文件所属 spec %s 不一致" % (block.full_id, sid),
                            path=parsed.path,
                            line=block.start_line,
                        )
                    )
            for block in parsed.clauses():
                real_clauses.append((parsed.path, block))
                if block.full_id in seen_clauses:
                    failures.append(
                        problem(
                            "EG-S2-C10",
                            "条款 ID 重复：%s" % block.full_id,
                            path=parsed.path,
                            line=block.start_line,
                        )
                    )
                else:
                    seen_clauses[block.full_id] = (parsed.path, block)
                _classify_clause(block, parsed.path, active_ids, failures)
            for block in parsed.acceptances():
                real_acceptances.append((parsed.path, block))
                if block.full_id in seen_acceptances:
                    failures.append(
                        problem(
                            "EG-S2-C14",
                            "验收 ID 重复：%s" % block.full_id,
                            path=parsed.path,
                            line=block.start_line,
                        )
                    )
                else:
                    seen_acceptances[block.full_id] = (parsed.path, block)
        clause_id_set = set(seen_clauses.keys())
        covered = set()
        for path, block in real_acceptances:
            declared = _coverage(block, sid, clause_id_set, path, failures)
            covered.update(declared)
            _wrong_implementations(block, path, failures)
        for path, block in real_clauses:
            if block.full_id not in covered:
                failures.append(
                    problem(
                        "EG-S2-C15",
                        "条款 %s 没有被任何验收覆盖" % block.full_id,
                        path=path,
                        line=block.start_line,
                    )
                )
        cited = set()
        for path, block in real_clauses:
            for did in allocations.get(sid, ()):
                if _cites(block, did):
                    cited.add(did)
        for did in sorted(allocations.get(sid, ())):
            if did not in active_ids or did in cited:
                continue
            path = files[0].path if files else None
            failures.append(
                problem(
                    "EG-S2-C12",
                    "分配给 %s 的 active 决定 %s 没有被任何条款引用" % (sid, did),
                    path=path,
                )
            )
        if freeze:
            for parsed in files:
                _freeze_markers(parsed, sid, failures, local_choices)


def _classify_clause(block, path, active_ids, failures):
    decisions = _refs(block, DEC_REF_RE)
    facts = _refs(block, FACT_REF_RE)
    local = _block_text_has(block, LOCAL_MARK)
    substantive = _block_text_has(block, SUBST_MARK)
    active = [did for did in decisions if did in active_ids]
    inactive = [did for did in decisions if did not in active_ids]
    if not active and not facts and not local and not substantive:
        failures.append(
            problem(
                "EG-S2-C11",
                "条款 %s 没有 active 决定引用、事实引用或 AUTHOR-CHOICE 标记" % block.full_id,
                path=path,
                line=block.start_line,
            )
        )
    if inactive:
        rendered = "、".join(inactive)
        failures.append(
            problem(
                "EG-S2-C12",
                "条款 %s 引用了非 active 决定 %s" % (block.full_id, rendered),
                path=path,
                line=block.start_line,
            )
        )


def _coverage(block, owner, clause_ids, path, failures):
    match = COVERAGE_RE.match(block.rest or "")
    if not match:
        failures.append(
            problem(
                "EG-S2-C14",
                "验收 %s 缺少紧接的覆盖声明" % block.full_id,
                path=path,
                line=block.start_line,
            )
        )
        return set()
    declared = [part.strip() for part in match.group(1).split("、")]
    ok = set()
    for clause_id in declared:
        prefix = _marked_spec(clause_id, CLAUSE_SUFFIX_RE)
        if prefix != owner or clause_id not in clause_ids:
            failures.append(
                problem(
                    "EG-S2-C14",
                    "验收 %s 覆盖的条款 %s 不存在于同一 spec" % (block.full_id, clause_id),
                    path=path,
                    line=block.start_line,
                )
            )
            continue
        ok.add(clause_id)
    return ok


def _wrong_implementations(block, path, failures):
    seen = {}
    valid = 0
    for line_no, text in block.lines:
        match = WI_LINE_RE.match(text)
        if not match:
            continue
        token = match.group(1)
        parsed = WI_ID_RE.match(token)
        if not parsed:
            continue
        prefix, number = parsed.group(1), parsed.group(2)
        if prefix != block.full_id:
            failures.append(
                problem(
                    "EG-S2-C16",
                    "错误实现 %s 的前缀与所在验收 %s 不一致" % (token, block.full_id),
                    path=path,
                    line=line_no,
                )
            )
            continue
        valid += 1
        if number in seen:
            failures.append(
                problem(
                    "EG-S2-C16",
                    "验收 %s 中错误实现编号 W%s 重复" % (block.full_id, number),
                    path=path,
                    line=line_no,
                )
            )
        else:
            seen[number] = line_no
    if valid == 0:
        failures.append(
            problem(
                "EG-S2-C16",
                "验收 %s 没有错误实现" % block.full_id,
                path=path,
                line=block.start_line,
            )
        )


def _line_has_token(text, token):
    return token in text


def _freeze_markers(parsed, sid, failures, local_choices):
    clause_at = {}
    for block in parsed.clauses():
        for line_no, _text in block.lines:
            clause_at[line_no] = block
        for line_no in _block_text_has(block, LOCAL_MARK):
            local_choices.append(
                {
                    "spec": sid,
                    "clause": block.full_id,
                    "path": parsed.path,
                    "line": line_no,
                }
            )
    for index, text in enumerate(parsed.masked_lines):
        if not _line_has_token(text, SUBST_MARK):
            continue
        line_no = index + 1
        block = clause_at.get(line_no)
        if block is None:
            message = "残留 [AUTHOR-CHOICE:substantive]"
        else:
            message = "条款 %s 残留 [AUTHOR-CHOICE:substantive]" % block.full_id
        failures.append(
            problem("EG-S2-C13", message, path=parsed.path, line=line_no)
        )


def check_test_markers(test_texts, docs, selected, failures, restrict_prefix):
    all_acceptances = {}
    for sid, files in docs.items():
        for parsed in files:
            for block in parsed.acceptances():
                all_acceptances[block.full_id] = (parsed.path, block.start_line, sid)
    found = set()
    selected_set = set(selected)
    for rel, text in test_texts:
        for match in MARKER_RE.finditer(text):
            ac_id = match.group(1)
            prefix = _marked_spec(ac_id, ACCEPTANCE_SUFFIX_RE)
            line = text.count("\n", 0, match.start()) + 1
            if restrict_prefix and prefix not in selected_set:
                continue
            found.add(ac_id)
            if ac_id not in all_acceptances:
                failures.append(
                    problem(
                        "EG-S2-C17",
                        "测试标记 eg:ac %s 不存在于任何已存在的 spec 文件" % ac_id,
                        path=rel,
                        line=line,
                    )
                )
    for sid in selected:
        files = docs.get(sid, [])
        for parsed in files:
            for block in parsed.acceptances():
                if block.full_id in found:
                    continue
                failures.append(
                    problem(
                        "EG-S2-C17",
                        "验收 %s 没有测试标记 eg:ac %s" % (block.full_id, block.full_id),
                        path=parsed.path,
                        line=block.start_line,
                    )
                )


def _dedupe(items):
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _active_ids(by_id):
    return {did for did, decision in by_id.items() if decision.status == "active"}


def run_trace(argv):
    args, parse_message = parse_trace_args(argv)
    if parse_message:
        mode = report_mode(args) if args else None
        freeze = bool(args and args["freeze"])
        return usage_error(parse_message, mode=mode, freeze=freeze)
    combo = combination_error(args)
    if combo:
        return usage_error(combo, mode=report_mode(args), freeze=args["freeze"])
    mode = args["mode"]
    root = os.path.abspath(args["root"] or os.getcwd())
    try:
        project = _load_project(root, mode)
    except InputError as exc:
        return emit(mode, [], args["freeze"], exc.failures, [], 2)
    if args["specs"]:
        selection = _validate_selection(project, args["specs"])
        if selection is not None:
            return emit(
                mode,
                [],
                args["freeze"],
                [problem("EG-S2-C23", selection)],
                [],
                2,
            )
        selected = _dedupe(args["specs"])
        report_unknown = False
    else:
        selected = sorted(
            sid for sid in project["spec_ids"] if project["docs_ready_files"].get(sid)
        )
        report_unknown = True
    failures = []
    if mode in ("spec", "tests") and not project["spec_files"]:
        failures.append(
            problem("EG-S2-C24", "specs 的全部模式合计没有匹配到文件", path="eg.json")
        )
    if mode == "tests" and not project["test_files"]:
        failures.append(
            problem("EG-S2-C24", "tests 的全部模式合计没有匹配到文件", path="eg.json")
        )
    failures.extend(project["entry_failures"])
    check_relations(project["by_id"], project["order"], project["decisions_path"], failures)
    check_design(
        project["design_texts"],
        _active_ids(project["by_id"]),
        project["by_id"],
        project["decisions_path"],
        failures,
    )
    docs, unknown, clause_ids = build_docs(
        project["spec_files"], project["spec_texts"], project["spec_ids"]
    )
    # A spec id counts as having a file only after filename assignment.
    existing = {sid for sid, files in docs.items() if files}
    if not args["specs"]:
        selected = sorted(existing)
    allocations = evaluate_map(
        project["map_model"],
        project["by_id"],
        clause_ids,
        project["map_path"],
        project["decisions_path"],
        failures,
    )
    local_choices = []
    if mode in ("spec", "tests"):
        check_spec_bodies(
            docs,
            unknown,
            selected,
            report_unknown,
            _active_ids(project["by_id"]),
            allocations,
            args["freeze"],
            failures,
            local_choices,
        )
    if mode == "tests":
        check_test_markers(
            project["test_texts"], docs, selected, failures, bool(args["specs"])
        )
    report_specs = selected
    if failures:
        return emit(mode, report_specs, args["freeze"], failures, local_choices, 1)
    return emit(mode, report_specs, args["freeze"], [], local_choices, 0)


def _validate_selection(project, spec_ids):
    known = set(project["spec_ids"])
    files = project["docs_ready_files"]
    for sid in spec_ids:
        if sid not in known:
            return "给出的 spec ID %s 不在地图档位表中" % sid
        if not files.get(sid):
            return "spec %s 的文件不存在" % sid
    return None


def _load_project(root, mode):
    config = load_config(root)
    decisions_text, decisions_path = _read_listed(
        root, config["decisions"], "EG-S2-C19", "决策登记文件"
    )
    design_texts = []
    seen_design = set()
    for rel in config["design"]:
        text, rel_path = _read_listed(root, rel, "EG-S2-C19", "设计稿文件")
        if rel_path in seen_design:
            continue
        seen_design.add(rel_path)
        design_texts.append((rel_path, text))
    map_text, map_path = _read_listed(root, config["spec_map"], "EG-S2-C19", "spec 地图文件")
    by_id, order, entry_failures = load_registry(decisions_text, decisions_path)
    spec_files = expand_patterns(root, config["specs"])
    spec_texts = {}
    for rel in spec_files:
        text, rel_path = _read_listed(root, rel, "EG-S2-C19", "spec 文件")
        spec_texts[rel_path] = text
    test_files = []
    test_texts = []
    if mode == "tests":
        test_files = expand_patterns(root, config["tests"])
        for rel in test_files:
            text, rel_path = _read_listed(root, rel, "EG-S2-C19", "测试文件")
            test_texts.append((rel_path, text))
    map_model = parse_map(map_text)
    for item in map_model["structural"]:
        item["path"] = map_path
    docs_ready = {sid: [] for sid in map_model["spec_ids"]}
    for rel in spec_files:
        owner = _assign_spec(rel.split("/")[-1], map_model["spec_ids"])
        if owner is not None:
            docs_ready.setdefault(owner, []).append(rel)
    return {
        "by_id": by_id,
        "order": order,
        "entry_failures": entry_failures,
        "decisions_path": decisions_path,
        "design_texts": design_texts,
        "map_model": map_model,
        "map_path": map_path,
        "spec_ids": map_model["spec_ids"],
        "spec_files": spec_files,
        "spec_texts": spec_texts,
        "test_files": test_files,
        "test_texts": test_texts,
        "docs_ready_files": docs_ready,
    }
