# EG-S2 验收测试说明

测试依据：`docs/specs/EG-S2-trace.md`（基准 commit `26f2e0c`）。本文件记录运行环境问题、spec 中无法写出确定断言之处，以及测试对含糊处采取的处理。凡下文写“不断言”的，测试都没有针对该点做断言。

## 0. 运行环境：入口命令在本机被用户站点包遮蔽

- 现象：`/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v` 在本机报 `ModuleNotFoundError: No module named 'tests.acceptance'`，一个测试都不运行。
- 原因：`~/Library/Python/3.9/lib/python/site-packages/tests/__init__.py` 是一个普通包，它遮蔽了仓库根目录下没有 `__init__.py` 的 `tests/` 命名空间包。测试作者只能在 `tests/acceptance/eg_s2/` 下写文件，无法添加 `tests/__init__.py` 或 `tests/acceptance/__init__.py`。
- 已验证可用的等价命令（结果相同）：
  - `PYTHONNOUSERSITE=1 /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v`
  - `/usr/bin/python3 -s -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v`
  - `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -v`（不带 `-t .`；测试文件对此有回退导入）
- 建议由流程维护者决定：在 `tests/`、`tests/acceptance/` 下补 `__init__.py`，或把入口命令改为上面某一种。

## 1. spec 未规定、测试按最弱可判定的方式处理的点

| 验收 | spec 原文 | 问题 | 测试的处理 |
|---|---|---|---|
| EG-S2-AC01 | “各自退出码为 2 并指出问题字段” | spec 没有说明用 `failures` 的哪个字段“指出”问题字段，而 message 文字不规定 | 断言退出码 2、`result` 为 `error`，并断言问题字段名（如 `tests`、`bogus_key`、`design`、`decisions`、`spec_map`、`specs`、`schema`）出现在 `failures` 序列化后的文本中（通常即 message）。若审查认为这超出 spec，可删去 `assertMentions` 一行 |
| EG-S2-AC01、C19 | C01：“均为配置错误（退出码 2）”；C19：“输入错误只有以下情形：`eg.json` … 不符合 C01” | `eg.json` 配置错误时 `failures[].check` 应为 `EG-S2-C01` 还是 `EG-S2-C19`，spec 未定 | 只断言 check ∈ {`EG-S2-C01`, `EG-S2-C19`} |
| EG-S2-AC02 | “各自报告对应条目且退出码为 1” | 未规定如何在报告中标识“对应条目”（message、line 还是 path） | 每个夹具只含一个缺陷，断言退出码 1 且出现 `EG-S2-C02`；不断言条目如何被标识 |
| EG-S2-AC25 | “档位表中没有的 spec ID 出现在清单列头时报错” | 未规定该失败归属 `EG-S2-C25` 还是 `EG-S2-C09` | 断言退出码 1，且失败中含 `EG-S2-C25` 或 `EG-S2-C09` 之一 |
| EG-S2-AC13 | `local_choices` 示例 `"line": 40` | 未规定 line 指条款标记所在行还是 AUTHOR-CHOICE 标记所在行 | 夹具把两者写在同一行，断言 line 等于该行 |
| EG-S2-AC19 | “path 为相对于 `--root` 的路径，使用 `/` 分隔” | 用法错误时 path 取值未规定；输入错误（如 `eg.json` 中的绝对路径）时出问题的文件可能不在 `--root` 下 | 只在退出码为 1 的报告中断言 path 为 null 或不含 `\` 的相对路径；不断言 line 的具体取值，只断言为 null 或 ≥1 的整数 |
| EG-S2-AC19 | C19：“决策登记 … 顶层不符合 C02”为输入错误；C02 只列举了“顶层不是对象、`decisions` 不是数组、`schema` 值不符” | 顶层多出第三个键是否属于“顶层不符合 C02”（C02 写的是“恰好含”） | 按 C19 的概括规定处理：顶层多键断言退出码 2 |
| EG-S2-AC18 | “`mode` 在无法解析时为 `null`” | `--mode bogus`、`--mode tests --freeze` 等能解析出值但非法的组合，`mode` 是否为 null 未定 | 只对缺少 `--mode` 断言 `mode` 为 null；所有用法错误都断言 `specs` 为 `[]`，且 check 只出现 `EG-S2-C18`（`--spec` 取值问题为 `EG-S2-C23`） |
| EG-S2-AC23、C19 | 报告字段 `"specs": ["EG-S2"]` | spec 只规定用法错误时为空数组，没有明文规定正常运行时 `specs` 的含义（是否为选中的 spec 列表） | 正常运行时只断言 `specs` 是数组 |
| EG-S2-AC19 | “可读摘要写到标准错误” | 未规定通过时是否也必须输出摘要 | 只在存在失败的运行中断言标准错误非空 |

## 2. spec 未覆盖、测试未涉及的情形

- EG-S2-C17 与 EG-S2-C23：未给 `--spec` 时，测试文件中出现前缀为地图外 spec（如 `EG-S9`）或文件不存在的 spec（如 `EG-S3`）的验收 ID。C17 说“不存在于任何已存在的 spec 文件即报错”，C23 又说“C10—C17 只作用于选中的 spec”，两条结合后结论不确定。测试只使用前缀为已存在 spec 的不存在 ID（`EG-S2-AC99`）。
- EG-S2-C24：design 模式下 `specs` 零匹配是否报错没有明文（C24 只写了 spec 与 tests 模式），不测。
- EG-S2-C10：`nn` 少于两位（如 `**[EG-S2-C1]**`）是报错还是不识别为标记，未定，不测。
- EG-S2-C07：去向中出现地图档位表以外的 spec ID、或非 active 决定出现在分配表中，未定，不测（夹具不含这两种情况）。
- EG-S2-C14：验收标记后缺少覆盖声明时归哪条 check，未定，不测。
- EG-S2-C19：spec 文件或测试文件（由模式匹配得到，而非 `eg.json` 直接列出）无法按 UTF-8 解码时，属于“`eg.json` 所列文件”的输入错误还是检查失败，未定，不测（AC24 只要求 GBK 设计稿退出码为 2）。

## 3. 关于 AC20 / AC21 的夹具说明

- EG-S2-AC20：按任务说明，把仓库 `scripts/`（排除 `__pycache__`、`*.pyc`）复制到夹具根目录，再运行复制品的 `scripts/eg.py`，此时不设 `PYTHONDONTWRITEBYTECODE`、不加 `-B`。对夹具根目录下全部目录与文件内容做运行前后比对，覆盖通过、失败、`--freeze`、缺省 `--root`（cwd 为夹具根）与用法错误几种运行。其余测试运行仓库内的 `scripts/eg.py` 时设置 `PYTHONDONTWRITEBYTECODE=1`，避免在仓库中留下 `__pycache__`。
- EG-S2-AC21：在临时目录中用 Python 3.9 创建 `--without-pip` 虚拟环境（优先 `sys.executable`，否则 `/usr/bin/python3`），先确认其中 `yaml` 不可导入，再运行命令。找不到 3.9 解释器或 venv 创建失败时 skip；本机自测中 venv 创建成功，未 skip。“源码不 import science-gates”通过扫描 `scripts/**/*.py` 中的 import 语句、`import_module` / `__import__` 调用与 `sys.path` 操作实现，并要求 `scripts/eg.py` 存在。

## 4. 测试文件中的标记

- 测试文件中的 `eg:ac EG-S2-ACnn` 字面量只用于本 spec 的真实验收。夹具里的测试标记在运行时由 `support.ac_marker()` 拼接生成，因此将来对本仓库运行 `trace --mode tests` 时，夹具中的 `EG-S2-AC99`、`EG-S1-AC99` 等不会被误认为本仓库的测试标记。

## 5. AC20 修正：字节码写入位置不受解释器内置前缀影响（对应补丁检查存活者 EG-S2-AC20-W2）

- 原因：macOS 系统 Python 3.9（`/usr/bin/python3`）自带非空的 `sys.pycache_prefix`（`~/Library/Caches/com.apple.python`），环境变量里没有 `PYTHONPYCACHEPREFIX` 时也是如此。原测试中，"导入后才关闭字节码写入"的错误实现会把字节码写到项目外的这个目录，运行前后的项目快照看不到，于是该补丁存活（见 `tests/mutants/eg_s2/SURVIVORS.md`）。`clean_env()` 只能去掉环境变量，去不掉这个内置默认值。
- 没有采用"把 `PYTHONPYCACHEPREFIX` 指向 `--root` 内"的做法：实测设置前缀后，解释器启动阶段（`eg.py` 第一行执行之前）就会把约 40 个标准库模块的 `.pyc` 写进前缀目录，正确实现也会因此失败。
- 做法：AC20 运行复制出的 `scripts/eg.py` 时，在解释器参数中加 `-X pycache_prefix=`（值为空）。CPython 3.8 起，空值的这个选项表示 `sys.pycache_prefix = None`，并且优先于环境变量和解释器内置默认值，于是项目模块的字节码只能写到源码旁的 `__pycache__`，也就是 `--root` 之内、快照覆盖的位置；标准库字节码仍写在项目外，不影响比较。`support.run_eg()` 为此增加了 `python_args` 参数，默认为空，其他测试的命令行不变。
- 为避免在其他解释器上悄悄退化成空测试，AC20 先用同样的参数和环境启动子解释器，确认 `sys.pycache_prefix` 为 `None`、`sys.dont_write_bytecode` 为 `False`，不满足时测试失败并提示是测试环境问题。
- 断言没有变：仍然只比较 `--root` 下全部目录与文件在运行前后是否一致（C20：只读，不产生包括 `__pycache__` 在内的任何文件）。

## 6. 实现审查 B1 的回归测试（`test_trace_regress.py`）

依据：`docs/specs/EG-S2-trace.md`（冻结版）；缺陷来源为 `docs/reviews/EG-S2/review-impl-B1.md` 中用户定性为实现错误的 IB1-01、IB1-02、IB1-03、IB1-05（IB1-04 为已知限制，不测）。既有测试与 `support.py` 未改动；新文件自带夹具变换函数。每个测试方法前的注释写明对应的 IB1 编号。

| IB1 | 测试 | 依据条款 | 断言 |
|---|---|---|---|
| IB1-01 | `test_ac13_freeze_rejects_substantive_marker_followed_by_text` | C13、C11 | 标记后紧跟汉字或字母，`--freeze` 下退出码 1，C13 失败项指向该 spec 文件 |
| IB1-01 | `test_ac11_substantive_marker_followed_by_text_classifies_clause` | C11 | 同上写法的 substantive 标记使条款算已归类，不带 `--freeze` 时通过 |
| IB1-01 | `test_ac13_local_marker_followed_by_text_classifies_and_is_listed` | C11、C13 | local 标记后紧跟汉字或字母：不报 C11；`--freeze` 下该条款出现在 `local_choices` 中（条款标记与 AUTHOR-CHOICE 标记同行，避开第 1 节所述 line 的未定处） |
| IB1-02 | `test_ac17_marker_with_prefix_outside_map_fails_without_spec` | C17、C23 | 测试文件含地图外前缀的标记（`EG-S9-AC01`）：未给 `--spec` 时 tests 模式报 C17；`--spec EG-S2` 时通过（C23 收窄不变）；spec 模式通过 |
| IB1-02 | `test_ac17_marker_for_spec_without_file_fails_without_spec` | C17、C23 | 同上，前缀为地图中有、文件不存在的 `EG-S3` |
| IB1-03 | `test_ac25_design_mode_accepts_any_spec_id_form` | C25、C07、C08、C09 | 见下文"同构比较" |
| IB1-03 | `test_ac10_spec_mode_accepts_any_spec_id_form` | C25、C10、C11—C16 | 同上 |
| IB1-03 | `test_ac17_tests_mode_accepts_any_spec_id_form` | C25、C10、C17 | 同上 |
| IB1-03 | `test_ac23_renamed_spec_id_is_a_valid_selection` | C25、C23 | 改名后的 spec ID（如 `APP-S2`）作为 `--spec` 取值合法，spec 与 tests 模式通过 |
| IB1-05 | `test_ac07_missing_allocation_failure_points_into_its_path` | C19、C07 | 分配表漏掉 D-003 时，C07 失败项的 `line` 要么为 null，要么是 `path` 所指文件中确实存在、且含 `D-003` 的那一行；`line` 非 null 时 `path` 不得为 null |

同构比较（IB1-03）：C25 规定"地图中的 spec ID 集合以档位表第一列为准"，spec 与决定都没有规定 spec ID 的形式，因此只在 spec ID 名称上不同的两个项目，检查结果应当相同。测试对基准夹具（及其变体）先在 `EG-S1`/`EG-S2`/`EG-S3` 命名下运行并断言预期结论，再把全部文件内容与文件名中的 spec ID 替换后运行，比较两者的退出码、失败项 `(check, path, line)` 多重集合（`path` 同样替换）以及 `local_choices`。`message` 与报告的 `specs` 字段不比较（文字不受约束；`specs` 含义见第 1 节）。替换方案两种：`EG-S` → `APP-S`（派发示例），以及 `EG-S1/S2/S3/S9` → `CORE/TRACE/PROBE/EXTRA`（不带 `-S<数字>` 形状，防止只把字母前缀放宽的修复）。覆盖的情形：三种模式的通过、`--freeze` 的 local 清单、`--spec` 选择，以及分别触发 C25、C12、C10（重复条款、前缀与文件不符、文件名前缀不在地图中）、C11、C13、C14、C15、C16、C17（缺标记、未知标记）的变体。

在基准候选实现（`e20e734`）上，10 个新测试全部失败：IB1-01 的标记不被识别（`--freeze` 退出码 0；条款被报 C11）；IB1-02 未给 `--spec` 时退出码 0；IB1-03 改名后的项目报 C25"档位表 spec ID 必须为全称"、C07"去向无法识别"等，`--spec APP-S2` 返回 2；IB1-05 的 `line` 为 25，而 spec 地图第 25 行是"清单版本：v1。"。

本节涉及的 spec 未定处：

- C19 只说 `line` 为行号、问题不对应具体行时为 null，没有明说 `line` 必须属于 `path` 所指文件；测试按"`path` 与 `line` 共同给出位置"理解，并只要求该行提到出问题的决定编号，因此 `line: null`（分配表中本无此行）与改为指向决策登记中该决定所在行两种修复都能通过。
- IB1-02 的测试只断言未给 `--spec` 时报 C17，不断言失败项的 `path`/`line`，也不区分"地图外"与"无文件"两种原因。
- IB1-03 中 spec ID 允许的字符集 spec 未定；测试只使用字母、数字与 `-`，且 ID 本身不含 `-C<数字>`、`-AC<数字>` 这类会与条款、验收标记产生歧义的片段。

## 7. 实现审查 C1 的回归测试与 IC1-03 修正（`test_trace_regress.py`）

依据：`docs/specs/EG-S2-trace.md`（冻结版）；缺陷来源为 `docs/reviews/EG-S2/review-impl-C1.md` 的 IC1-01、IC1-02、IC1-03。既有测试的断言与 `support.py` 未改动，只修改了 IC1-03 所指的那一个测试。每个测试方法前的注释写明对应的 IC1 编号。

| IC1 | 测试 | 依据条款 | 断言 |
|---|---|---|---|
| IC1-01 | `test_ac14_clause_ids_after_the_declaration_do_not_break_it` | C14、C15 | 覆盖声明之后的正文里出现"条款 ID 紧跟 `：`"时，spec 与 tests 模式都退出码 0，不报 C14/C15。三种写法：报告的 CASE 1（`覆盖 A、B：A：……；B：……`）、CASE 2（`覆盖 C03：描述二，另见EG-S2-C01：说明。`），以及两个 ID 的声明后出现另一 spec 的条款 ID 紧跟 `：` |
| IC1-01 | `test_ac14_declaration_end_holds_for_any_spec_id_form` | C14、C15、C25 | 同上三种写法，把 spec ID 换成第 6 节的两种改名方案（`APP-Sn`；`CORE/TRACE/…`）后结论相同 |
| IC1-01 | `test_ac14_clause_named_after_the_first_colon_is_not_covered` | C14、C15 | `覆盖 EG-S2-C03：EG-S2-C05：说明。` 中声明只到第一个 `：`：EG-S2-C03 存在，不报 C14；EG-S2-C05 未被覆盖，报 C15。防止修复把整行的条款 ID 都计为覆盖 |
| IC1-02 | `test_ac07_duplicate_allocation_failure_points_into_its_path` | C19、C07 | 分配表中 D-003 出现两次时，C07 失败项的位置判定与下文 IC1-03 相同 |
| IC1-03 | `test_ac07_missing_allocation_failure_points_into_its_path`（修正断言） | C19、C07 | 分配表漏掉 D-003 时，位置判定见下文 |

第 6 节表中 IB1-05 一行的"断言"列和"本节涉及的 spec 未定处"第一条，由本节取代。

### C07 失败项的位置判定（IC1-02、IC1-03）

C19 规定 `line` 为 1 起始的行号，"问题不对应具体行时为 `null`"。由此理解：`line` 非 null 时，它是问题在 `path` 所指文件中的那一行。C07 的问题是"某条 active 决定在分配表中出现的次数不是 1"，它只可能对应两处：决策登记中该决定的条目，或 spec 地图中的决定分配表。测试据此对每个 C07 失败项判定：

1. `line` 为 null：通过，不约束 `path`。
2. `line` 非 null：`path` 必须是决策登记或 spec 地图之一；
   - `path` 为决策登记：`line` 落在该决定的 JSON 对象内（从其 `{` 到 `}`，含 `"id": "D-003"` 那一行）；
   - `path` 为 spec 地图：`line` 落在标题为 `决定分配` 的章节内（从标题行到该章节最后一个非空行，即分配表末行；含表头与各数据行）。

不再要求该行文字含 `D-003`。因此派发列出的三种修法都通过：登记中该决定所在行、分配表中的位置（表头、末行、重复出现的那一行均可）、`null`。

IB1-05 原错误是 `path` 为 spec 地图、`line` 却是登记中的行号。这个行号落在地图的分配章节之外（"不对应"）或超出地图行数（"超出"），都被第 2 条挡住。为保证这一点不依赖巧合，测试先断言夹具前提：登记中该决定条目的行号范围与地图分配章节的行号范围不相交，否则报夹具问题而不是实现问题。两个测试都在两种布局下运行：基准夹具（D-003 的登记行 25 落在地图内、分配章节外，即审查报告的复现）与把 D-003 移到登记末尾（登记行 66 超出地图行数）。

审查报告建议的"`line` 不超过 `path` 所指文件的行数"没有采用：在基准夹具上，IB1-05 原错误给出的 25 不超过地图行数，会被放过。

### 在候选实现（`scripts/` = `22ea31a`）上的运行结果

- 全部 95 个测试中，原有 91 个（含修正后的 IC1-03 测试）通过；4 个新测试失败，共 12 个子测试失败：
  - IC1-01 三个测试的每个子测试都报出 C14（声明被读成 `EG-S2-C02：EG-S2-C01：缺键时报错；EG-S2-C02` 一类字符串）与 C15，退出码 1；
  - IC1-02 两种布局下都得到 `path` 为 `docs/design/spec-map.md`、`line` 为登记中的行号（25、66），落在分配章节（第 13—23 行）之外。
- 在副本中临时改动 `engine.py` 并各自运行后还原（`git status` 只剩本目录的改动）：
  - 模拟 IB1-05 原错误（漏分配分支改为 `path=map_path`，`line` 仍为登记行号）：IC1-03 测试在两种布局下都失败，line 25 与 66 均判在分配章节外；
  - 漏分配分支改为 `line=None`、改为 spec 地图加表头行、改为 spec 地图加分配表末行：IC1-03 测试均通过；
  - 漏分配分支改为登记中另一条目的行（D-003 所在行 + 8）：IC1-03 测试失败；
  - 重复分支改为 `path=decisions_path`、改为 spec 地图加第二次出现的分配表行、改为 `line=None`：IC1-02 测试均通过；
  - 覆盖声明正则的 ID 字符类排除 `：`（审查报告的最小修复）：IC1-01 三个测试通过；与重复分支改为 `path=decisions_path` 同时应用时，95 个测试全部通过。

本节涉及的 spec 未定处：

- C19 没有逐条规定每种失败的 `line` 应指向哪一行。本节"`line` 必须落在问题所在的条目或章节内"是从"不对应具体行时为 null"推出的最弱可判定要求；`path` 限定为决策登记与 spec 地图，是因为 C07 只涉及这两个文件。
- spec ID 本身含 `：` 时覆盖声明如何切分，spec 未定（审查报告建议按 D-017 处理）；IC1-01 的测试只使用不含 `：` 的 spec ID。
