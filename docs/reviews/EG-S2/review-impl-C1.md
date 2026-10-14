# EG-S2 Implementation Review C1

reviewer：Claude Opus 5.5（独立新会话，未参与 spec、测试、实现、修复与实现审查 B1）

verdict: FAIL

## 输入核对

派发文件 `docs/reviews/EG-S2/dispatch-impl-review-C1.md` 已全文读取，与 `git show 6e8976a:docs/reviews/EG-S2/dispatch-impl-review-C1.md` 逐字节一致。

| 项 | 结果 |
|---|---|
| 分支 | `eg/v2` |
| B1 受审 commit | `93ccc09` = `93ccc091779abde19bfe960e0f5ae44e97c5fe24` |
| C1 受审 commit | `66a10e8` = `66a10e853c3d4ae3b4c6c3a1cddfb704d7e748c1` |
| 本轮提交 | `git log --oneline 93ccc09..66a10e8`：`ea36012`、`1504751`、`5aeaa7d`、`d499fe4`、`54931f7`、`cc6cada`、`4bbe332`（EG-S1 与审查记录），`ef8e915`（回归测试冻结），`22ea31a`（修复候选），`c01ec78`、`cb5b2c5`、`66a10e8`（记录与补丁重写） |
| 本轮 scripts/tests 变化 | `engine.py`（+159/−）、`test_trace_regress.py`（新增）、`NOTES.md` 第 6 节、10 个补丁、`manifest.json`、`SURVIVORS.md`；另有 EG-S1 的 `scripts/egcheckpoint/` 与 `scripts/eg.py`（新增两个子命令的导入），后者只在影响 `trace` 时审（见 I6） |
| 冻结 spec | `66a10e8` 中与工作区中的 `docs/specs/EG-S2-trace.md` 的 sha256 均为 `97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62`，与派发一致 |
| 冻结检查表 | `git diff 93ccc09 66a10e8 -- docs/reviews/EG-S2/checklist-impl.md` 为空，与 B1 相同 |
| B1 报告、账本、三份修复派发 | 已读取；账本对 IB1 的定性与派发一致（IB1-01、02、03、05 为实现错误，IB1-04 为已知限制） |

身份一致，可审。

工作方式：`git worktree add --detach <mktemp -d>/wt 66a10e8` 建立受审副本；为对照修复前行为另建 `93ccc09` 的副本。全部实验在副本与系统临时目录中进行，Python 均加 `-B`；唯一例外是为 I6 在受审副本的一个临时拷贝中不带 `-B` 运行 `trace --mode tests` 一次。复现用的夹具通过副本中的 `tests/acceptance/eg_s2/support.py` 生成在 `tempfile` 目录。为验证 IC1-01 的最小修复，在受审副本中临时改过 `engine.py` 一行，验证后 `git checkout` 还原，`git status --short` 为空。项目目录中只写了本报告。两个副本已在审查结束时 `git worktree remove`。

已由协调者完成的机械检查（91 项通过、10 个回归测试在旧候选上失败、48/48 补丁被杀死、自检通过）不重复报告；本审查在受审副本中顺带重跑 91 项与自检，结果一致。

## B1 finding 关闭核对

复现脚手架同 B1 报告（在受审副本根目录执行；`fx` 为 `support.Fixture()`，输出为 `exit`、`result`、`[check, path, line]` 列表、`local_choices` 的条款列表）。

### IB1-01（AUTHOR-CHOICE 标记后紧跟文字）：已关闭

`_block_text_has` 与 `_line_has_token` 改为子串判断（`token in text`），不再看标记后的字符类别。

| 情形 | `66a10e8` 输出 |
|---|---|
| B1 CASE A：`细节[AUTHOR-CHOICE:substantive]尚待用户决定。`，`--mode spec --freeze` | `exit=1 fail [['EG-S2-C13', 'docs/specs/EG-S2-beta.md', 19]] ['EG-S1-C03', 'EG-S2-C04']` |
| 变体：标记后接拉丁字母 `TBD`、数字 `1`、下划线 `_x`、行尾、列表项中 | 均为 `exit=1`，C13 指向标记所在行 |
| B1 CASE B：`第四条，[AUTHOR-CHOICE:local]入口在导入前关闭字节码写入。`，`--freeze` | `exit=0 pass [] ['EG-S1-C03', 'EG-S2-C04']` |
| 变体：local 标记后接字母、标记位于条款正文开头 | 均为 `exit=0`，EG-S2-C04 在 `local_choices` 中 |
| 反向：`[AUTHOR-CHOICE:localx]`（未定义写法） | `exit=1`，报 C11（C11 只认两种写法） |
| 反向：local 标记写在反引号内 | `exit=1`，报 C11（C22 排除） |
| 反向：substantive 标记写在反引号内，`--freeze` | `exit=0`（C22 排除，不触发 C13） |

结论：B1 反例与同类变体全部符合 C11、C13、C22。

### IB1-02（未给 `--spec` 时的未知前缀测试标记）：已关闭

`check_test_markers` 新增 `restrict_prefix`，仅在给出 `--spec` 时按前缀过滤。

| 情形 | `66a10e8` 输出 |
|---|---|
| B1 反例：`EG-S9-AC01`（地图外）与 `EG-S3-AC01`（无文件），`--mode tests` | `exit=1`，两条 `EG-S2-C17`（`tests/sub/test_s2.py` 第 8、9 行） |
| 同一项目，`--mode tests --spec EG-S2` | `exit=0`（C23 收窄） |
| 变体：前缀完全不像 spec ID 的 `XYZ-AC01`，`--mode tests` | `exit=1`，C17 |
| 变体：`--spec EG-S2` 下出现 `EG-S1-AC99` | `exit=0`（前缀未选中，C23） |
| 变体：`--mode spec` 含 `EG-S9-AC01` | `exit=0`（spec 模式不查测试，C18） |

结论：符合 C17、C23。

### IB1-03（spec ID 写死为 `EG-S<数字>`）：已关闭（另见 IC1-01，修复本身引入了新缺陷）

去掉 `SPEC_ID_RE`；条款、验收、覆盖声明、错误实现、测试标记的正则改为通用前缀，再与文件所属 spec 比较；去向解析按档位表 ID 集合最长匹配；档位表 ID 只拒绝空、含空白或 `]` 的单元格。

| 情形 | `66a10e8` 输出 |
|---|---|
| B1 反例：全部 `EG-S` 换成 `APP-S`，design / spec `--freeze` / tests | 均 `exit=0`；`local_choices` 为 `APP-S1-C03`、`APP-S2-C04` |
| 变体：换成 `app_s`、`规格`、`X.Y-`、`EG-S0`、`P-C`、`Q-AC`、`P-C1` | 三种模式均 `exit=0`，`local_choices` 与基准同构 |
| `APP-S` 项目注入错误：条款前缀与文件不符、重复错误实现编号、删除测试标记、去向含地图外 ID、C09 说明写不存在的条款 ID、文件名前缀不在地图 | 分别报 C10（并连带 C14）、C16、C17、C07、C09、C10，与 `EG-S` 夹具同类注入的结论一致 |
| `APP-S` 项目，`--spec APP-S2` / `--spec EG-S2` | `exit=0` / `exit=2`（C23） |

结论：B1 反例与常见形式的 spec ID 均符合 C25、C10、C14、C16、C17。spec ID 本身含 `-AC<两位以上数字>` 时测试标记识别失真（非阻塞备注 1）。但修复中放宽的覆盖声明正则引入了新的 C14 误报，见 IC1-01。

### IB1-05（C07 失败项 `path` 与 `line` 指向不同文件）：B1 反例已关闭，同类变体未关闭（IC1-02，MINOR）

| 情形 | `66a10e8` 输出 |
|---|---|
| B1 反例：分配表删去 D-003，`--mode design` | `exit=1 fail [['EG-S2-C07', 'docs/design/decisions.json', 25]]`；登记第 25 行为 D-003 所在行 |
| 变体：分配表中 D-003 出现两次 | `exit=1 fail [['EG-S2-C07', 'docs/design/spec-map.md', 25]]`；夹具 spec 地图第 25 行为 `## 3. 定档清单`，25 仍是登记中的行号 |

B1 报告给出的位置是 count≠1 两个分支共用的那一行（B1 时第 1033 行），修复只改了 count==0 分支；"出现多次"分支（现第 1103—1104 行）仍以 spec 地图为 `path`、登记行号为 `line`。严重度与 IB1-05 相同（MINOR），不阻塞。

### IB1-04：已接受为已知限制，未审。

## 变化范围审查（I1—I6）

| ID | 结果 | 证据摘要 |
|---|---|---|
| I1 | FAIL | IC1-01：通用化的覆盖声明正则可越过全角冒号，验收标记行后文若有"条款 ID 紧跟 `：`"（中间无空白），覆盖声明被误读，报假的 C14 与 C15；`93ccc09` 上同一输入通过。其余修改（标记子串识别、去向解析、档位表 ID 校验、条款/验收/错误实现/测试标记通用前缀、C09 说明匹配、C17 前缀过滤）经上表实验与变体核对符合条文。 |
| I2 | PASS | 修复轮没有新增实现者取舍。`engine.py` 模块说明中关于 C17 的取舍已按 IB1-02 改写；档位表 ID 拒绝空白与 `]` 是为了标记与表格语法可以解析，B1 的最小修复也建议保留这一限制，不碰实质选择。 |
| I3 | PASS | 10 个重写补丁逐个对照 spec §3：AC02-W3、AC07-W1、AC09-W2、AC14-W1、AC17-W1、AC18-W1、AC20-W2、AC22-W2 与旧补丁逻辑相同，只是迁移到新上下文。重点核对两处：AC09-W1 对无文件的 spec 要求说明中含形如 `<SPEC>-Cnn` 的条款 ID，正是"spec 文件不存在时也要求条款 ID"的字面意思，比旧补丁（要求实际存在、必然失败）弱，不是更容易被抓住的错误；受审副本中应用后，主测试 `test_ac09_missing_spec_only_needs_non_empty_note` 因夹具中 EG-S3 的"是：执行探针"被报 C09 而失败，还原后通过。AC17-W2 改为只从 `def test_…` 函数名中按归一化验收 ID 子串识别，注释与字符串中的标记全部漏掉，忠实于"只匹配测试函数名，漏掉注释或字符串中的标记"；只能识别已知验收 ID 是"不扫描标记"的直接后果，不是另一种错误；应用后主测试 `test_ac17_marker_in_string_is_recognised` 失败，还原后通过。 |
| I4 | PASS（1 条 MINOR） | 10 个回归测试的断言都能追溯到 C11、C13、C17、C23、C25、C10、C14—C16、C19。IB1-03 的同构比较只比较退出码、`(check, path, line)` 多重集合与 `local_choices`，不比较 `message` 与 `specs`，替换后的 ID 只用字母、数字与 `-`，不越界。IB1-05 测试要求 `line` 所在行含 `D-003`，比 C19 略强（IC1-03，MINOR）。 |
| I5 | PASS（IC1-01 已在 I1 计入） | 新代码在 `_marked_spec` 返回 `None`、去向以括注开头、档位表 ID 含正则特殊字符（`X.Y-1`，已 `re.escape`）、空 ID 集合等输入下均给出合规 JSON 报告，未见未捕获异常。IC1-02 为定位行不一致。 |
| I6 | PASS | `engine.py` 的修改没有新增 import、文件写入或环境读取，没有针对测试或夹具的分支。`scripts/eg.py` 在 `sys.dont_write_bytecode = True` 之后才新增导入 `egcheckpoint`，后者只 import 标准库（`os/re/json/hashlib/subprocess/signal/tempfile/time/secrets/shlex/stat/shutil/glob/sys`），模块级没有副作用语句，不 import science-gates。在受审副本的临时拷贝中用 `/usr/bin/python3`（3.9.6）不带 `-B` 运行 `scripts/eg.py trace --mode tests`，退出码 0，运行后 `find . -name __pycache__` 无结果。 |

## Findings

### IC1-01

- check：I1
- severity：MAJOR
- scope：CHANGED
- location：`scripts/egtrace/engine.py` 第 50—52 行 `COVERAGE_RE`；使用点第 1476、1487 行 `_coverage`
- 原文（代码）：

  ```python
  COVERAGE_RE = re.compile(
      r"^\s*覆盖\s*((?:[^\s、]+-C\d{2,})(?:\s*、\s*[^\s、]+-C\d{2,})*)\s*："
  )
  ```

  原文（spec）：C14"标记后紧接覆盖声明 `覆盖 <条款 ID>[、<条款 ID>…]：`，只有该声明中的 ID 计为覆盖"；AC14"验收正文中提到但不在覆盖声明里的条款 ID 不计为覆盖"。
- 依据：覆盖声明到第一个 `：` 结束。修复前前缀为 `EG-S\d+`，不会越过 `：`；为 IB1-03 放宽为 `[^\s、]+` 后，这个字符类包含全角冒号和汉字，于是贪婪匹配会一直延伸到同一行上最后一个"条款 ID 后跟 `：`"的位置，只要中间没有空白或 `、`。声明被读成 `EG-S2-C02：EG-S2-C01：缺键时报错；EG-S2-C02` 这类字符串，`_coverage` 把它当成一个不存在的条款 ID 报 C14，真正被覆盖的条款随之报 C15。中文行文在全角冒号后通常不加空格，逐条说明所覆盖条款的写法（`覆盖 A、B：A：……；B：……`）是合乎 C14 的自然写法。
- 反例（在受审副本根目录执行，脚手架同上）：
  - CASE 1：`fx.edit(S.S2, "**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：描述一。", "**[EG-S2-AC01]** 覆盖 EG-S2-C01、EG-S2-C02：EG-S2-C01：缺键时报错；EG-S2-C02：多键时报错。"); args = ["--mode", "spec"]`
    - `66a10e8`：`exit=1 fail [['EG-S2-C14', 21, '验收 EG-S2-AC01 覆盖的条款 EG-S2-C02：EG-S2-C01：缺键时报错；EG-S2-C02 不存在于同一 spec'], ['EG-S2-C15', 13, '条款 EG-S2-C02 没有被任何验收覆盖']]`
    - `93ccc09`：`exit=0 pass []`
  - CASE 2：`fx.edit(S.S2, "**[EG-S2-AC02]** 覆盖 EG-S2-C03：描述二。", "**[EG-S2-AC02]** 覆盖 EG-S2-C03：描述二，另见EG-S2-C01：说明。"); args = ["--mode", "spec"]`
    - `66a10e8`：`exit=1`，C14（"覆盖的条款 EG-S2-C03：描述二，另见EG-S2-C01 不存在于同一 spec"）与 C15（EG-S2-C03 未被覆盖）
    - `93ccc09`：`exit=0 pass []`
  - 对照：CASE 2 中"另见"后加一个空格，或把后一个 `：` 换成 `。`，`66a10e8` 均 `exit=0`。
- 后果：合规的 spec 被判失败（退出码 1），spec 与 tests 模式及 `--freeze` 门都受影响，报告指出的条款 ID 是一段被误切的正文，使用者难以定位。这是本轮修复引入的回归，旧候选在同一输入上正确。
- 最小修复：覆盖声明中 ID 部分的字符类排除全角冒号，即 `[^\s、：]+`（两处）。在受审副本中临时这样改动后，上述反例与对照均 `exit=0`，91 项验收测试全部通过（已还原）。如认为 spec ID 本身含 `：` 也必须支持，那是 C14 语法与 C25 的交叉问题，属 spec 缺陷（按 D-017），可以像 `]` 一样在 `_spec_id_usable` 中拒绝，不由实现者另作选择。

### IC1-02

- check：I5
- severity：MINOR
- scope：PRIOR_FINDING（IB1-05 的同类变体）
- location：`scripts/egtrace/engine.py` 第 1103—1104 行
- 原文（代码）：`failures.append(problem("EG-S2-C07", message, path=map_path, line=decision.line))`（"在决定分配表中出现了 %d 次"分支）
- 依据：C19"`path` 为相对于 `--root` 的路径……`line` 为 1 起始的行号"；修复派发要求"`path` 与 `line` 必须指向同一文件中的同一位置"。`decision.line` 是登记中的行号，`path` 却是 spec 地图。B1 报告的位置是两个分支共用的一行，修复只改了 count==0 分支。
- 反例：`fx.edit(S.SPEC_MAP, "| D-003 | EG-S3 |\n", "| D-003 | EG-S3 |\n| D-003 | EG-S2 |\n"); args = ["--mode", "design"]` → `exit=1 fail [['EG-S2-C07', 'docs/design/spec-map.md', 25]]`；该夹具 spec 地图第 25 行为 `## 3. 定档清单`，25 是 D-003 在 `decisions.json` 中的行号。
- 严重度理由：退出码、`check`、`path` 与结论都正确，只是定位行指错，与 IB1-05 同级。
- 后果：按报告定位会跳到无关行。
- 最小修复：该分支改为 `path=decisions_path`，或保留 `path=map_path` 而 `line` 取第二次出现的分配表行（`alloc_rows` 中已有行号）。

### IC1-03

- check：I4
- severity：MINOR
- scope：CHANGED
- location：`tests/acceptance/eg_s2/test_trace_regress.py` 第 334—338 行 `test_ac07_missing_allocation_failure_points_into_its_path`
- 原文（测试）：`self.assertIn("D-003", lines[line - 1], ...)`
- 依据：C19 只要求 `line` 为行号、不对应具体行时为 `null`，没有要求该行提到出问题的决定。修复派发 `dispatch-impl-fix-1.md` 明确把"`path` 为 spec 地图、`line` 为分配表位置"列为可接受的修法，而分配表位置（例如表头行）不含 `D-003`，会被该测试判错。NOTES 第 6 节只列出了 `null` 与"登记中该决定所在行"两种可通过的修法。
- 反例：无需运行。按派发列出的第三种修法，`line` 指向 `| 决定 | 去向 |` 所在行时，`assertIn("D-003", …)` 必然失败。
- 严重度理由：当前实现选择指向登记，测试通过；该断言只排除了一种较弱的定位方式，没有迫使实现采用唯一的特定选择，不阻塞。
- 后果：测试与派发对允许修法的说法不一致；后续重写实现或补丁时可能误判。
- 最小修复：放宽为"`line` 不超过 `path` 所指文件的行数"，或在 NOTES 中写明本测试有意排除"指向分配表"的修法，并同步修复派发的说法。

## 非阻塞备注

1. 测试标记正则 `MARKER_RE`（第 58—60 行）的 ID 部分为非贪婪的 `[^\s]+?-AC\d{2,}`。spec ID 本身含 `-AC<两位以上数字>` 时（实验中用 `Q-AC11`、`Q-AC12`），`eg:ac Q-AC11-AC01` 被截成 `Q-AC11`，tests 模式报 10 条假的 C17。条款正则因有 `]` 收尾不受影响。这种 spec ID 不属于合理输入，且 `<SPEC>-ACnn` 语法在 spec ID 不受限时本身有歧义（NOTES 第 6 节也已注明测试不覆盖），宜在 spec 下次修订时按 D-017 说明 spec ID 不得含 `-C<数字>`、`-AC<数字>` 片段，或规定按已知 ID 最长匹配。
2. C09 说明匹配（第 1139—1143 行）用 `(?<![A-Za-z0-9])` 作左边界。一个 spec ID 是另一个以 `-` 连接的后缀时（如同时有 `S2` 与 `EG-S2`），`EG-S2-C01` 也会被当作 `S2-C01`。只在极少见的命名下出现，影响很小。
3. 修复派发与回归测试都要求"`path` 与 `line` 指向同一文件"，但账本中 IB1-05 的摘要只写了"未出现在分配表"一种情形；IC1-02 处理时宜一并更正账本措辞。
4. 本轮 `scripts/eg.py` 的变化来自 EG-S1，每次运行 `trace` 都会导入 `egcheckpoint`。经 I6 核对目前无害；此后 EG-S1 模块若引入 3.10+ 语法或第三方依赖，会直接使 `trace` 违反 C21。可考虑在 EG-S6 中把子命令改为按需导入。

## 裁定理由

B1 的 4 条待核 finding 中，IB1-01、IB1-02、IB1-03 按 B1 反例与同类变体核对均已关闭；IB1-05 的 B1 反例已关闭，同一行代码的"出现多次"分支仍有同类问题（IC1-02，MINOR，不阻塞）。

修复轮引入了 1 条新的 MAJOR：IC1-01。为关闭 IB1-03 而通用化的覆盖声明正则可以越过全角冒号，导致合乎 C14 的验收写法被报假的 C14 与 C15、退出码 1。它映射检查表 I1，有原文、依据，并在新旧两个 commit 上给出了可复现的对照反例。这是实现缺陷，不是 spec 缺陷：C14 的声明语法在 spec ID 不含 `：` 时没有歧义，最小修复只需在字符类中排除 `：`，已在副本中验证 91 项测试仍全部通过。

I2、I3、I6 通过；I4 只有 1 条 MINOR（IC1-03）。按派发规则，存在新的 MAJOR，裁定 FAIL。本轮是标准档最后一轮，按派发将判为 NON_CONVERGENT，由用户选择重置方式。IC1-01 的修复范围很小（一行正则，加一个回归测试），可供用户选择重置方式时参考。
