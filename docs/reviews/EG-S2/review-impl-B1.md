# EG-S2 Implementation Review B1

reviewer：Claude Opus 5.5（独立新会话，未参与 spec、测试或实现）

verdict: FAIL

## 输入核对

派发文件 `dispatch-impl-review-B1.md`（提交于 `93ccc09`）与更正文件 `dispatch-impl-review-B1-erratum.md`（提交于 `ea36012`）均已全文读取；按更正，受审 commit 为 `93ccc09`。

| 项 | 结果 |
|---|---|
| 受审 commit | `git rev-parse 93ccc09` = `93ccc091779abde19bfe960e0f5ae44e97c5fe24`，位于分支 `eg/v2`（`eg/v2` 顶端为 `ea36012`，其父为 `93ccc09`） |
| 派发原文所写 commit | `fcf871a` = `fcf871aa199f91d919f9b7a18095360505c943bf`；`git diff --stat fcf871a 93ccc09 -- scripts tests` 为空，`git diff --name-status fcf871a 93ccc09` 只有新增的 `checklist-impl.md` 与 `dispatch-impl-review-B1.md`，与更正文件所述一致 |
| 实现与候选一致 | `git diff --stat e20e734 93ccc09 -- scripts` 为空 |
| 冻结 spec | `docs/specs/EG-S2-trace.md` 的 `shasum -a 256` 输出为 `97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62`，与派发值一致 |
| 冻结验收测试 | `git log -- tests/acceptance/eg_s2` 最新为 `0a04a62`（tests-freeze），与派发一致 |
| 冻结检查表 | `docs/reviews/EG-S2/checklist-impl.md`，存在于 `93ccc09` |

身份一致，可审。

工作方式：`git worktree add --detach <mktemp -d>/wt 93ccc09` 建立副本，全部实验在该副本与系统临时目录中进行（夹具通过副本中的 `tests/acceptance/eg_s2/support.py` 生成在 `tempfile` 目录）。Python 均加 `-B`，唯一例外是为 I6 取得真实执行证据，在副本中有意不带 `-B` 运行了 `python3 scripts/eg.py trace --mode design|spec|tests` 与 `--mode spec --freeze` 各一次；运行后副本中 `git status --short --ignored` 为空，`find . -name __pycache__` 无结果。项目目录中只写了本报告。副本已在审查结束时 `git worktree remove`。

D-014 核对：账本记载实现阶段"无测试异议"，无需核对异议处理。

## 检查表结果

| ID | 结果 | 证据摘要 |
|---|---|---|
| I1 | FAIL | IB1-01：AUTHOR-CHOICE 标记后紧跟中文或字母时不被识别，`--freeze` 下残留 substantive 标记仍判通过（违反 C11、C13）。IB1-03：spec ID 写死为 `EG-S<数字>`，与 C25"spec ID 集合以档位表第一列为准"冲突。其余条款逐条核对未见违反，见下文"逐条核对"。 |
| I2 | FAIL | IB1-02：账本所列取舍"未给 `--spec` 时 C17 只检查前缀属于已有文件的 spec 的测试标记"与 C17、C23 原文及 D-010 冲突。IB1-03 中的 spec ID 形式限制属于未披露的取舍，且碰到 spec 地图为 EG-S2 登记的"公共 API / wire：标记语法"触碰面。账本所列其余 13 项取舍与 spec 文字一致，见下文。 |
| I3 | PASS | 48 个补丁逐个对照 spec 中的错误实现描述，全部忠实；没有补丁用"更容易被抓住的其他错误"代替所述错误。 |
| I4 | PASS | 三个测试文件与 `support.py` 中的断言均可追溯到 spec 条款；对 spec 未定处一律采用最弱断言（NOTES 第 1 节）。未发现会把另一合理实现判错的越界断言。 |
| I5 | FAIL（仅 MINOR） | IB1-04：`supersedes` 链长超过约 1000 时 RecursionError，标准输出为空；IB1-05：C07"决定未出现在分配表"的失败项 `line` 取自登记文件，`path` 却是 spec 地图。两者均不属于合理输入下的阻塞缺陷，见各条严重度理由。 |
| I6 | PASS | `scripts/eg.py` 第 10 行在 import 之前设置 `sys.dont_write_bytecode = True`；`engine.py` 只 import `glob/json/os/re/sys`，唯一 `open` 为第 308 行的 `"rb"` 读；写出只有标准输出与标准错误；无环境变量读取、无针对测试或夹具的分支。真实不带 `-B` 运行后副本无任何新增文件（见输入核对）。 |

### I1 逐条核对（摘要）

- C01、C24、C19：键集合、类型、绝对路径、`..` 分量、glob 语义（`glob.glob(os.path.join(root, p), recursive=True)`、只收普通文件、去重排序）、BOM、UTF-8、零匹配、输入错误与检查失败边界，均与条文一致；实测 `design` 项为整数、`decisions` 为整数、空 spec 地图、单元格不足的表行、CRLF 换行、空 spec 文件、未闭合围栏等输入，均给出合规 JSON 报告与正确退出码。
- C02—C04：字段集合、`id` 形式与唯一、`status` 取值、关系存在性、自引用、成环、双向替代、`amends`/`amended_by` 成对，均实现；`date` 另做了日历校验（见非阻塞备注 1）。
- C05、C06、C22：多设计稿扫描、行内与围栏代码排除，符合条文。
- C25、C07—C09：按标题文字定位、去掉编号、取章节内第一张表、列头校验、去向三种形式与括注、全局约束不计分配、规则结果与清单一致性、上调不要求理由、"是"的说明含实际存在的条款 ID，均符合条文；但 spec ID 形式见 IB1-03。
- C10、C26、C11—C16：文件名前缀、同 spec 多文件、标记前缀等于所属 spec、块边界（围栏内 `#` 行不是标题）、覆盖声明、错误实现归属与唯一性，符合条文；AUTHOR-CHOICE 识别见 IB1-01。
- C17、C23：带 `--spec` 时的收窄符合条文；不带 `--spec` 时见 IB1-02。
- C18：三种模式的检查集合与非法组合（缺 `--mode`、`--freeze` 与非 spec 模式、`--spec` 与 design）符合条文。
- C20、C21：见 I6。

### I2 账本所列取舍逐项

| 取舍 | 判断 |
|---|---|
| `..` 按路径分量判断 | 与 C01"不得含 `..`"一致，属局部 |
| 设计稿决定编号按至少三位识别；条款分类接受一位以上 | 分别与 C06（"决定编号"即登记格式）和 C11（"`D-` 加数字"）一致 |
| 未给 `--spec` 时 C17 只检查已有文件 spec 前缀的标记 | **冲突**，见 IB1-02 |
| `local_choices[].line` 取标记所在行 | spec 未定，属局部 |
| 清单列头有、档位表无的 spec ID 报 C25 | 与 C25"spec ID 集合以档位表第一列为准"一致 |
| `eg.json` 配置错误 check 用 C01 | 与 C01"配置错误（退出码 2）"一致 |
| 少于两位数字的标记不识别 | spec 未定；属局部，但建议澄清（非阻塞备注 4） |
| 分配表中不存在的决定或档位表外 spec ID 报 C07；非 active 决定的多余行不报 | 与 C07 一致，属局部 |
| 覆盖声明只认同一行紧接标记的部分，缺失报 C14 | 与 C14"标记后紧接覆盖声明"一致 |
| 匹配到的 spec 或测试文件无法按 UTF-8 解码时退出码 2 | 与 C24"所有输入文件……无法按 UTF-8 解码即为输入错误（退出码 2）"一致 |
| design 模式下 `specs` 零匹配不报 C24 | 与 C24 只列 spec、tests 模式一致 |
| 报告 `specs` 为本次选中的 spec，错误时为空数组 | 与 C19 一致 |
| `--spec` 不合法时只返回 C23 | 与 C19、C23 一致 |

账本未列出、但实现中实际做出的取舍：spec ID 限定为 `EG-S<数字>`（IB1-03）；`date` 做日历校验（非阻塞备注 1）；定档清单第一列列头必须字面为"清单项"（非阻塞备注 2）。

### I3 补丁逐项（摘要）

AC01-W1 缺键填默认值；AC01-W2 改用 `pathlib.Path.glob`；AC02-W1 删除缺字段与未知字段检查；AC02-W2 重复 `id` 以后者覆盖前者；AC02-W3 `id` 只收三位；AC03-W1 只拒绝空串；AC04-W1 删除成环检测（直接自环仍由自引用检查捕获，等价于"只查直接自环"）；AC04-W2 只查 `supersedes` 悬空；AC04-W3 删除"被替代仍为 active"；AC05-W1 只扫第一个设计稿；AC06-W1 只查存在；AC07-W1 只把 spec 去向计入出现次数；AC07-W2 从全局约束说明抽 spec ID；AC08-W1 删除规则结果与清单比对；AC08-W2 `<` 改 `!=`；AC09-W1 对无文件 spec 也要求条款 ID；AC09-W2 只看形式；AC10-W1 跨 spec 比较编号；AC10-W2 前缀在地图中即接受；AC11-W1 接受 `D-` 后跟非数字；AC11-W2 接受任意 `[AUTHOR-CHOICE:…]`；AC12-W1 全文统计（含标题与说明段）；AC12-W2 对无文件 spec 也做分配检查；AC13-W1 只写警告；AC14-W1 允许覆盖他 spec 条款；AC14-W2 块内所有条款 ID 计为覆盖；AC15-W1 有任一验收即视为全部覆盖；AC16-W1 无 ID 列表项计为错误实现；AC16-W2 按 ID 前缀归属；AC17-W1 spec 模式也查测试标记；AC17-W2 只匹配测试函数名；AC18-W1 各模式跑全部检查；AC18-W2 忽略非法组合；AC19-W1 输入错误返回 1；AC19-W2 摘要也写标准输出；AC19-W3 去掉 `line`；AC20-W1 报告写入项目内缓存文件；AC20-W2 导入后才关闭字节码写入；AC21-W1 引入 `yaml`；AC21-W2 使用 `glob` 的 `root_dir`；AC22-W1 不做代码排除；AC22-W2 对测试文件也做代码排除；AC23-W1 忽略 `--spec`；AC24-W1 不允许 BOM；AC24-W2 零匹配视为通过；AC25-W1 按章节位置取表；AC26-W1 空行结束条款块；AC26-W2 用未屏蔽的原始行判断标题。均与 spec 对应错误实现描述一一对应。

## Findings

复现脚手架（在 `93ccc09` 的副本根目录执行；`<CASE>` 段落见各 finding）：

```sh
python3 -B -s - <<'EOF'
import json, subprocess, sys, tempfile
sys.dont_write_bytecode = True
from tests.acceptance.eg_s2 import support as S
fx = S.Fixture()
# <CASE>：修改 fx，并设置 args
d = tempfile.mkdtemp(); fx.write(d)
p = subprocess.run([sys.executable, "-B", "scripts/eg.py", "trace"] + args + ["--root", d],
                   capture_output=True, text=True)
r = json.loads(p.stdout)
print("exit=%d" % p.returncode, r["result"],
      [[f["check"], f["path"], f["line"]] for f in r["failures"]],
      [c["clause"] for c in r["local_choices"]])
EOF
```

### IB1-01

- check：I1
- severity：MAJOR
- location：`scripts/egtrace/engine.py` 第 1209—1221 行 `_block_text_has`、第 1484—1493 行 `_line_has_token`；调用点第 1384—1385 行（C11 分类）、第 1501 行（`local_choices`）、第 1511 行（C13）
- 原文（代码）：

  ```python
  end = found + len(token)
  if end == len(text) or not text[end].isalnum():
  ```

  原文（spec）：C11"AUTHOR-CHOICE 标记只有两种写法，`[AUTHOR-CHOICE:local]` 与 `[AUTHOR-CHOICE:substantive]`，写在正文中（不在反引号内）"；C13"带 `--freeze` 时，选中的 spec 中不得残留 substantive 标记……输出全部 local 标记所在条款的清单"。
- 依据：spec 对标记之后的字符没有任何要求；标记以 `]` 结尾，本身已有明确边界。`str.isalnum()` 对汉字返回 True，于是标记后紧跟汉字（中文行文中不加空格是常态）或字母时，实现认为不是标记。后果覆盖 C11、C13 与 `local_choices` 三处。
- 反例：
  - CASE A：`fx.add_clause(S.S2, "**[EG-S2-C05]** 依据 D-002 的选择，细节[AUTHOR-CHOICE:substantive]尚待用户决定。"); fx.add_ac(S.S2, "**[EG-S2-AC04]** 覆盖 EG-S2-C05：描述。\n- [EG-S2-AC04-W1] 错误实现。"); args = ["--mode", "spec", "--freeze"]`
    输出：`exit=0 pass [] ['EG-S1-C03', 'EG-S2-C04']`
  - 对照（标记后加一个空格，其余相同）：`exit=1 fail [['EG-S2-C13', 'docs/specs/EG-S2-beta.md', 19]] ...`
  - CASE B：`fx.edit(S.S2, "第四条，局部选择。[AUTHOR-CHOICE:local]", "第四条，[AUTHOR-CHOICE:local]入口在导入前关闭字节码写入。"); args = ["--mode", "spec", "--freeze"]`
    输出：`exit=1 fail [['EG-S2-C11', 'docs/specs/EG-S2-beta.md', 17]] ['EG-S1-C03']`（误报 C11，且 EG-S2-C04 从 `local_choices` 中消失）
- 后果：冻结门放过残留的实质选择（D-011 要求冻结前逐条交用户决定），给出错误的 PASS；局部选择被误报为未归类、且不出现在交用户过目的清单中。
- 最小修复：去掉标记后的 `isalnum` 边界判断（标记以 `]` 结尾，子串匹配即可）；两个函数可直接用 `token in text`。

### IB1-02

- check：I2
- severity：MAJOR
- location：`scripts/egtrace/engine.py` 第 1531—1539 行 `check_test_markers`（`if prefix not in selected_set: continue`），配合第 1636—1637 行未给 `--spec` 时 `selected = sorted(existing)`；账本"实现者对未定处的取舍"第 3 项
- 原文（代码）：

  ```python
  prefix = ac_id.split("-AC", 1)[0]
  ...
  if prefix not in selected_set:
      continue
  ```

  原文（spec）：C17"测试文件中出现的验收 ID 若不存在于任何已存在的 spec 文件，即报错（D-010）"；C23"带 `--spec` 时：C10 只检查……，文件名不以任何 spec ID 开头的文件只在未给 `--spec` 时报告；C17 只检查 ID 前缀为选中 spec 的测试标记"。D-010"测试标记引用不存在的 ID 即报错"。
- 依据：C23 把"C17 只检查 ID 前缀为选中 spec 的测试标记"这一收窄明确限定在"带 `--spec` 时"之下，并在同一句中对 C10 写明不属于任何 spec 的对象"只在未给 `--spec` 时报告"。未给 `--spec` 时，"选中的 spec"恰为"全部文件已存在的 spec"，C17 的判定标准"不存在于任何已存在的 spec 文件"本身就是相对这个集合定义的，并不排除前缀不在其中的 ID。实现把带 `--spec` 时的前缀过滤也用于不带 `--spec` 的情形，使"前缀不属于已有 spec 的测试标记"在任何调用方式下都不会被报告，D-010 的这一半检查对这类 ID 永远不生效。测试作者在 NOTES 第 2 节认为这里两条结合后不确定；本审查认为 C23 的"带 `--spec` 时"限定已经消除了歧义。若协调者认为文字仍有两种读法，则按 spec 缺陷走 D-017，由用户决定，而不是由实现者自定。
- 反例：CASE：`fx.add_marker("EG-S9-AC01"); fx.add_marker("EG-S3-AC01"); args = ["--mode", "tests"]`（EG-S9 不在地图中，EG-S3 在地图中但无文件）
  输出：`exit=0 pass [] []`
  对照：`fx.add_marker("EG-S2-AC99")` 时输出 `EG-S2-C17` 失败、退出码 1。
- 后果：测试标记写错 spec 前缀、引用了地图外或尚无文件的 spec、或 spec 文件被改名后残留的旧标记，tests 模式默认调用一律判通过，给出错误结论。本仓库测试中的标记前缀只有 EG-S1、EG-S2，修复不影响自检结果。
- 最小修复：`check_test_markers` 只在给出 `--spec` 时按前缀过滤；未给 `--spec` 时对所有标记检查"是否存在于任何已存在的 spec 文件"。

### IB1-03

- check：I1（同时涉及 I2：未披露的取舍）
- severity：MAJOR
- location：`scripts/egtrace/engine.py` 第 42 行 `SPEC_ID_RE = re.compile(r"^EG-S\d+$")` 及第 918—926 行对档位表的校验；第 46—59 行 `CLAUSE_RE`、`ACCEPTANCE_RE`、`COVERAGE_RE`、`CLAUSE_ID_RE`、`WI_ID_RE`、`MARKER_RE` 中的 `EG-S\d+`；第 836 行 `parse_destination` 中的 `re.match(r"(EG-S\d+)", rest)`
- 原文（代码）：

  ```python
  SPEC_ID_RE = re.compile(r"^EG-S\d+$")
  CLAUSE_RE = re.compile(r"^\*\*\[(EG-S\d+)-C(\d{2,})\]\*\*(.*)$")
  ...
  if not SPEC_ID_RE.match(spec_id):
      ... "档位表 spec ID 必须为全称（如 EG-S2）：%s"
  ```

  原文（spec）：C25"spec ID 一律写全称（如 `EG-S2`），地图中的 spec ID 集合以档位表第一列为准"；C10、C14、C16 与 D-022 的写法是 `**[<SPEC>-Cnn]**`、`**[<SPEC>-ACnn]**`、`[<SPEC>-ACnn-Wn]`。
- 依据：spec 与决定都没有规定 spec ID 的形式；"全称"相对于 `S2` 之类的简写而言，"如 `EG-S2`"是示例。C25 明确 spec ID 集合"以档位表第一列为准"。`eg.json` 与 `--root`（D-022、D-025）的存在本身就是为了让 trace 用于任意项目根目录（D-020：engineering-gates 可单独复制安装）。实现把 spec ID 限定为 `EG-S<数字>`，这一限制不在账本所列取舍中；它限制的是 spec 地图为 EG-S2 登记为"是"的触碰面（"公共 API / wire：CLI 与标记语法"），按 D-011 不能由实现者自行决定。
- 反例：CASE：把夹具所有文本与文件名中的 `EG-S` 换成 `APP-S`：

  ```python
  for k in list(fx.files):
      fx.files[k] = fx.files[k].replace("EG-S", "APP-S")
  for old in (S.S1, S.S2):
      fx.files[old.replace("EG-S", "APP-S")] = fx.files.pop(old)
  args = ["--mode", "design"]
  ```

  输出：`exit=1 fail`，3 条 `EG-S2-C25`（"档位表 spec ID 必须为全称（如 EG-S2）：APP-S1"等）、1 条 C25 清单列不一致、4 条 `EG-S2-C07`（"去向无法识别：APP-S1"等）；tests 模式另报两份 spec 文件"文件名不以地图中的 spec ID 开头"（C10），条款与验收标记也全部不被识别。同一项目只把前缀换回 `EG-S` 即通过。
- 后果：任何不用 `EG-S<数字>` 命名 spec 的项目都无法使用 trace：design 模式必然失败，spec 与 tests 模式完全识别不到条款、验收、错误实现与测试标记。
- 最小修复：spec ID 取档位表第一列的非空单元格原样使用（可保留"不得含空白与 `]`"这类只为可解析而设的限制）；标记识别改用通用前缀，例如 `^\*\*\[([^\]\s]+?)-C(\d{2,})\]\*\*`，再按 C10/C14 比较前缀是否等于文件所属 spec；去向解析按档位表中的 ID 集合匹配。若用户确实希望把 spec ID 限定为某种形式，那是对公共写法的实质选择，须登记决定并按 D-017 修改 spec，而不是留在实现中。

### IB1-04

- check：I5
- severity：MINOR
- location：`scripts/egtrace/engine.py` 第 652—679 行 `_supersedes_cycles`（递归 `walk`）
- 原文（代码）：`elif nxt not in visited: walk(nxt, stack)`
- 依据：C19 要求标准输出只写一个 JSON 对象，退出码只取 0/1/2；未捕获异常违反之。
- 反例：CASE：

  ```python
  for i in range(1200):
      rel = {"supersedes": ["D-%04d" % (2001 + i)]} if i < 1199 else {}
      fx.add_decision(S.decision("D-%04d" % (2000 + i), status="active" if i == 0 else "superseded", **rel))
  fx.files[S.DESIGN] += "\n首条 D-2000。\n"
  fx.edit(S.SPEC_MAP, "| D-008 |", "| D-2000 | 不进 spec：夹具 |\n| D-008 |")
  args = ["--mode", "design"]
  ```

  输出：退出码 1，标准输出为空，标准错误末行 `RecursionError: maximum recursion depth exceeded`。
- 严重度理由：需要约 1000 条以上首尾相接的替代链，不属于合理输入，因此不阻塞。
- 后果：极端登记下崩溃且无 JSON 报告。
- 最小修复：改为显式栈的迭代 DFS。

### IB1-05

- check：I5
- severity：MINOR
- location：`scripts/egtrace/engine.py` 第 1033 行
- 原文（代码）：`failures.append(problem("EG-S2-C07", message, path=map_path, line=decision.line))`
- 依据：C19"`path` 为相对于 `--root` 的路径……`line` 为 1 起始的行号，问题不对应具体行时为 `null`"——`line` 应是 `path` 所指文件中的行。`decision.line` 是该决定在决策登记中的行号，却与 spec 地图的路径一起输出。
- 反例：CASE：`fx.edit(S.SPEC_MAP, "| D-003 | EG-S3 |\n", ""); args = ["--mode", "design"]`
  输出：`exit=1 fail [['EG-S2-C07', 'docs/design/spec-map.md', 25]]`；夹具 spec 地图第 25 行是标题 `## 3. 定档清单`，与 D-003 无关（25 是 D-003 在 `decisions.json` 中的行号）。
- 严重度理由：退出码、`check`、`path` 与结论都正确，只是定位行指错，不影响正确行为。
- 后果：使用者或 agent 按报告定位会跳到无关行。
- 最小修复：`line=None`（分配表中本来就没有这一行），或改为 `path=decisions_path`。

## 非阻塞备注

1. C02 `date`：spec 只要求"形如 `YYYY-MM-DD`"，实现另做日历校验（第 372—383 行），`2026-02-30` 会报 C02。比条文严格，实际影响很小；建议要么去掉，要么在下次编辑性修订中把"合法日期"写进 C02。
2. C09/C25 定档清单第一列：实现要求列头字面为"清单项"（第 934—937 行），列头写作"检查项"即报 C25 并跳过 C08、C09。spec 写的是"第一列为清单项"，可理解为列头文字，也可理解为该列内容；本仓库地图与夹具都用"清单项"，不阻塞，建议在 spec 中写明。
3. 行号：`mask_code` 与 `splitlines()` 把 U+2028、`\x0c` 等也视为换行，含这类字符的文件报告的行号会比按 `\n` 计数的行号大（实测设计稿中插入一个 U+2028 后，第 13 行的 D-099 被报告为第 14 行）。只影响定位。
4. 少于两位数字的标记（如 `**[EG-S2-C1]**`）不被识别，且其文字并入前一个块，该条款对 trace 完全不可见。spec 对此未定（NOTES 第 2 节），实现的选择属局部；建议按 D-017 编辑性修订写明是报 C10 还是忽略，倾向于报 C10。
5. 行内代码只在单行内配对；跨行的反引号对不被屏蔽。spec 写的是"反引号对之间"，未说明能否跨行，影响极小。
6. spec 地图不在 C22 的排除范围内，实现对地图中围栏代码里的 `## 档位` 也当作标题，可能取到示例表。与条文不冲突，记为已知行为。
7. design 模式报告的 `specs` 为全部文件已存在的 spec。spec 未规定 design 模式下该字段的含义，不影响判定。

## 裁定理由

存在 3 条 MAJOR（IB1-01、IB1-02、IB1-03），均有原文、依据与可复现反例，分别映射 I1、I2、I1，按派发规则裁定 FAIL。

- IB1-01 是实现缺陷：spec 对标记写法有明确规定，实现多加了一个对中文不成立的边界条件，导致冻结门在合理的中文写法下放过残留的实质选择。修复是局部的。
- IB1-02 是实现者取舍与 spec 原文和 D-010 冲突。本审查认为 C23 的"带 `--spec` 时"限定使原文确定；若协调者判断文字仍有两种读法，则转为 spec 缺陷按 D-017 交用户决定。两种处理都不应由实现者自行定论。
- IB1-03 是实现加了 spec 没有的限制：C25 把 spec ID 集合交给档位表决定，实现却写死了 `EG-S<数字>`。如果用户要限定 spec ID 形式，须作为新决定写入 spec。

I3、I4、I6 通过：补丁忠实，测试未越界，只读与依赖在真实执行点成立。IB1-04、IB1-05 为 MINOR，建议随本轮修复一并处理，但不影响裁定。修复后按 D-016 由 Closure 只审改动影响范围：上述三处代码、相应的回归实验，以及全部验收测试与补丁检查重跑结果。
