# EG-S2 静态追溯检查

> 状态：草稿 v0.4（阶段 4），按 B1 审查修订；格式包 F1—F8 已由 D-024 决定，待 C1 审查，未冻结。
> 档位：标准（规则结果为严格，按 spec-map 档位表下调）。依赖：无。
> 分配决定：D-006、D-008（地图字段）、D-010、D-011、D-022、D-023、D-024；全局约束 D-020、D-021。
> 本 spec 自身使用它所定义的写法；本文中描述语法的示例一律写在反引号或代码块内（见 EG-S2-C22）。

## 1. 目标与非目标

**目标**：一条只读命令，对项目做静态追溯检查，列出决策登记、设计稿、spec 地图、spec 条款、验收与测试标记之间的全部断链。

**非目标**：

- 不运行测试、不应用错误实现补丁（EG-S4）；
- 不运行探针，不检查 F 编号是否存在于事实登记（EG-S3 负责，已记入 spec 地图）；
- 不判断引用是否忠实于决定内容（D-006，交审查者）；
- 不判断 AUTHOR-CHOICE 的局部 / 实质分类是否正确（D-011，交审查者）；
- 本 spec 只创建 `scripts/eg.py` 中分发到 `trace` 子命令所需的最小部分；入口的整体约定与其他子命令归 EG-S6。

## 2. 条款

### 2.1 输入与配置

**[EG-S2-C01]** 命令读取 `--root` 所指目录（缺省为当前目录）下的 `eg.json`（D-022）。格式包 F4：`eg.json` 是一个 JSON 对象，恰好包含以下键，缺键、多键或类型不符均为配置错误（退出码 2）。（D-024）

```json
{
  "schema": "eg-config/v1",
  "decisions": "docs/design/decisions.json",
  "design": ["docs/design/design-v2.md"],
  "spec_map": "docs/design/spec-map.md",
  "specs": ["docs/specs/*.md"],
  "tests": ["scripts/tests/**/*.py"]
}
```

`schema` 的值必须为 `eg-config/v1`；`decisions`、`spec_map` 为文件路径字符串；`design` 为非空路径数组；`specs`、`tests` 为非空匹配模式数组。路径与模式都相对于 `eg.json` 所在目录，不得为绝对路径，不得含 `..`。匹配采用 `glob.glob(os.path.join(root, pattern), recursive=True)` 的语义：`**` 匹配零个或多个目录层级，只收集普通文件，结果去重后按路径排序（F-04）。

**[EG-S2-C24]** 所有输入文件按 UTF-8 读取，允许开头带 BOM；无法按 UTF-8 解码即为输入错误（退出码 2）。spec 与 tests 模式下 `specs` 的全部模式合计匹配零个文件，或 tests 模式下 `tests` 的全部模式合计匹配零个文件，按本条款报检查失败（退出码 1）。格式包 F8。（D-024）

### 2.2 决策登记

**[EG-S2-C02]** 格式包 F1：登记顶层是 JSON 对象，恰好含 `schema`（值必须为 `eg-decisions/v1`）与 `decisions`（数组）（D-021）。每条决定的必需字段为 `id`、`statement`、`status`、`source`、`date`，可选字段只有 `supersedes`、`amends`、`refines`、`amended_by`，出现其他字段即报错。`id` 形如 `D-` 加至少三位数字（如 `D-007`、`D-1000`），全局唯一；`statement` 与 `source` 为非空字符串；`date` 形如 `YYYY-MM-DD`；四个可选字段均为决定编号数组。顶层不是对象、`decisions` 不是数组、`schema` 值不符，按 C19 属于输入错误（退出码 2）；单条决定的问题属于检查失败（退出码 1）。（D-024）

**[EG-S2-C03]** `status` 只能取 `active`、`superseded`、`withdrawn`；"某事后置"本身是一条 active 决定（D-022）。

**[EG-S2-C04]** 格式包 F1：四个关系字段引用的编号必须存在，且不得引用自身；`supersedes` 关系不得成环；`status` 为 `superseded` 的决定必须被至少一条决定的 `supersedes` 引用，反之被 `supersedes` 引用的决定其 `status` 必须为 `superseded`；`amends` 与 `amended_by` 必须成对出现（A 的 `amends` 含 B，当且仅当 B 的 `amended_by` 含 A）（D-006）。（D-024）

### 2.3 设计稿

**[EG-S2-C05]** 每条 active 决定在 `design` 所列文件中至少出现一次（D-006）。

**[EG-S2-C06]** `design` 所列文件中出现的每个决定编号必须存在且为 active；出现 superseded 或 withdrawn 的编号即报错（D-006）。

### 2.4 spec 地图

**[EG-S2-C25]** 格式包 F6：spec 地图中有三张表，各自位于标题文字（去掉开头的编号如 `2. `）恰好为 `决定分配`、`定档清单`、`档位` 的章节下，取该章节内第一张 Markdown 表格。缺少任一章节或表格即按本条款报检查失败。spec ID 一律写全称（如 `EG-S2`），地图中的 spec ID 集合以档位表第一列为准。（D-024）

**[EG-S2-C07]** 格式包 F6：决定分配表的列为 `决定 | 去向`。去向单元格取三种形式之一：一个或多个 spec ID（以 `、` 分隔，每个 ID 后可跟括注）；`不进 spec：<理由>`，理由不得为空；`全局约束：<说明>`，说明中出现的 spec ID 不计为分配。每条 active 决定必须恰好出现在一行中（D-007）。（D-024）

**[EG-S2-C08]** 定档清单的规则结果必须与档位表一致：该 spec 的清单列中有任一"是"时，规则结果必须为严格；全为"否"时，规则结果不得为严格。确认档位低于规则结果时，理由不得为空；确认档位高于或等于规则结果时不要求理由。档位只能取轻量、标准、严格（D-008）。

**[EG-S2-C09]** 格式包 F6：定档清单表第一列为清单项，其余列头为 spec ID，单元格为 `否` 或 `是：<说明>`，说明不得为空。该 spec 文件已存在时，说明中必须包含至少一个在该 spec 中实际存在的条款 ID（D-008）。（D-024）

### 2.5 spec 条款

**[EG-S2-C10]** 格式包 F5：spec 文件名必须以地图中的某个 spec ID 开头，后接 `-` 或 `.`（如 `EG-S2-trace.md` 属于 `EG-S2`）；同一 spec ID 只能对应一个文件。文件内的条款标记写作 `**[<SPEC>-Cnn]**`（D-022），`<SPEC>` 必须等于该文件所属的 spec ID，`nn` 为至少两位数字；条款 ID 在该 spec 内唯一。（D-024）

**[EG-S2-C26]** 格式包 F7：条款块从行首的条款标记开始，到下一个行首条款或验收标记、或下一个 Markdown 标题之前结束；验收块的边界规则相同。块内任何位置（含其中的列表项与代码块之外的段落）的引用与标记都计入该块。（D-024）

**[EG-S2-C11]** 每个条款块至少包含一个决定引用（`D-` 加数字）、一个事实引用（`F-` 加数字），或一个 AUTHOR-CHOICE 标记（D-011）。格式包 F2：AUTHOR-CHOICE 标记只有两种写法，`[AUTHOR-CHOICE:local]` 与 `[AUTHOR-CHOICE:substantive]`，写在正文中（不在反引号内）。（D-024）

**[EG-S2-C12]** 条款中引用的决定必须为 active；只引用了非 active 决定的条款同时按 C11 与本条款各报一次。对 spec 文件已存在的每份选中 spec，地图分配给它的每条决定至少被它的一个条款引用；文件尚不存在的 spec 不做此项检查（D-010）。

**[EG-S2-C13]** 带 `--freeze` 时，选中的 spec 中不得残留 substantive 标记（必须已由用户决定并改为决定引用）；输出全部 local 标记所在条款的清单，供用户过目（D-011）。

### 2.6 验收与测试标记

**[EG-S2-C14]** 格式包 F7：验收标记写作 `**[<SPEC>-ACnn]**`（D-022），前缀规则同 C10，验收 ID 在该 spec 内唯一。标记后紧接覆盖声明 `覆盖 <条款 ID>[、<条款 ID>…]：`，只有该声明中的 ID 计为覆盖；被覆盖的条款 ID 必须存在于同一 spec。（D-024）

**[EG-S2-C15]** 每个条款至少被一条验收覆盖（D-010）。

**[EG-S2-C16]** 格式包 F7：每条验收块内至少有一个以 `- [<验收 ID>-Wn]` 开头的列表项作为错误实现（D-022）；错误实现 ID 的前缀必须等于所在验收块的 ID，`n` 在该验收内唯一（D-010、D-013）。（D-024）

**[EG-S2-C17]** tests 模式下，选中 spec 的每条验收至少有一个测试文件含其标记 `eg:ac <验收 ID>`，标记可出现在测试文件任意位置，包括注释、字符串与代码中（D-022）。测试文件中出现的验收 ID 若不存在于任何已存在的 spec 文件，即报错（D-010）。

### 2.7 代码排除

**[EG-S2-C22]** 格式包 F3：在 `design` 所列文件与 spec 文件中，行内代码（反引号对之间）与围栏代码块（三个反引号之间）内的文字不参与以下识别：条款、验收、错误实现标记；决定与事实引用；AUTHOR-CHOICE 标记。本规则不适用于测试文件（C17 的"任意位置"）。（D-024）

### 2.8 运行方式与输出

**[EG-S2-C18]** 入口为 `python3 scripts/eg.py trace --mode design|spec|tests [--spec <ID>]… [--freeze] [--root <目录>]`（D-022、D-023）。design 运行 C01—C09、C22、C24、C25；spec 另加 C10—C12、C14—C16、C26，带 `--freeze` 时另加 C13；tests 在 spec 的基础上另加 C17。缺少 `--mode`、`--freeze` 与 spec 以外的模式同用、`--spec` 与 design 模式同用，均为用法错误（退出码 2）。

**[EG-S2-C23]** `--spec <ID>` 可重复（D-023）。spec 与 tests 模式下，C10—C17 只作用于选中的 spec；未给 `--spec` 时选中全部文件已存在的 spec。给出的 ID 不在地图中、或其 spec 文件不存在，为用法错误（退出码 2）。

**[EG-S2-C19]** 格式包 F8：退出码 0 表示全部通过，1 表示存在检查失败，2 表示用法错误或输入错误（D-022）。输入错误只有以下情形：`eg.json` 缺失、不是合法 JSON 或不符合 C01；`eg.json` 所列文件不存在或无法按 UTF-8 解码；决策登记不是合法 JSON 或顶层不符合 C02。其余结构问题都按对应条款报检查失败。标准输出只写一个 JSON 对象，可读摘要写到标准错误。JSON 对象的字段如下。（D-024）

```json
{
  "schema": "eg-trace-report/v1",
  "mode": "spec",
  "specs": ["EG-S2"],
  "freeze": false,
  "result": "pass | fail | error",
  "failures": [
    {"check": "EG-S2-C05", "path": "docs/design/design-v2.md", "line": 12, "message": "..."}
  ],
  "local_choices": [
    {"spec": "EG-S2", "clause": "EG-S2-C20", "path": "docs/specs/EG-S2-trace.md", "line": 40}
  ]
}
```

`check` 为本 spec 的条款 ID；`line` 为 1 起始的行号，问题不对应具体行时为 `null`；`result` 为 `error` 时退出码为 2，`failures` 中给出原因。

**[EG-S2-C20]** 命令只读：不创建、修改或删除项目中的任何文件，报告只写到标准输出与标准错误（D-022）。`scripts/eg.py` 在导入其他模块之前设置 `sys.dont_write_bytecode = True`，使拆分模块的实现也不产生 `__pycache__`。[AUTHOR-CHOICE:local]

**[EG-S2-C21]** 实现只依赖 Python 3.9 及以上的标准库，不 import science-gates 的任何代码（D-020、D-021，F-01、F-03）。

## 3. 验收

**[EG-S2-AC01]** 覆盖 EG-S2-C01：`eg.json` 缺少 `tests` 键、多出一个未知键、`design` 为空数组、路径为绝对路径或含 `..`，各自退出码为 2 并指出问题字段；`docs/specs/**/*.md` 能匹配到 `docs/specs/` 下及其子目录中的文件。
- [EG-S2-AC01-W1] 缺键时静默使用默认路径并返回 0。
- [EG-S2-AC01-W2] 使用 `pathlib.Path.glob`，在 Python 3.9 上 `**` 只返回目录，导致零个文件被收集。

**[EG-S2-AC24]** 覆盖 EG-S2-C24：带 BOM 的 UTF-8 文件可正常读取；GBK 编码的设计稿导致退出码 2；`specs` 模式匹配零个文件时 spec 模式返回 1。
- [EG-S2-AC24-W1] 用不允许 BOM 的方式读取，带 BOM 的登记被判为非法 JSON。
- [EG-S2-AC24-W2] 零匹配时视为通过。

**[EG-S2-AC02]** 覆盖 EG-S2-C02：重复 `id`、`id` 为 `D-7`、缺 `date`、多出 `note` 字段，各自报告对应条目且退出码为 1；`schema` 值为 `eg-decisions/v0` 时退出码为 2；`D-1000` 合法。
- [EG-S2-AC02-W1] 只检查 `id` 唯一，不检查缺字段与未知字段。
- [EG-S2-AC02-W2] 重复 `id` 只保留后一条而不报错。
- [EG-S2-AC02-W3] `id` 只接受恰好三位数字，`D-1000` 被误报。

**[EG-S2-AC03]** 覆盖 EG-S2-C03：`status` 为 `deferred` 或任何其他值时报错。
- [EG-S2-AC03-W1] 接受任意非空字符串。

**[EG-S2-AC04]** 覆盖 EG-S2-C04：悬空引用、自引用、`supersedes` 成环（A→B→A）、无人替代的 superseded 决定、被替代却仍为 active 的决定、只有单向的 `amends`，各自报错。
- [EG-S2-AC04-W1] 只检查直接自环，漏掉 A→B→A。
- [EG-S2-AC04-W2] 不检查 `amended_by` 等非 `supersedes` 字段的悬空引用。
- [EG-S2-AC04-W3] 只检查 superseded 决定有人替代，不检查被替代的决定是否仍为 active。

**[EG-S2-AC05]** 覆盖 EG-S2-C05：`design` 列两个文件，删掉某条 active 决定在第二个文件中的唯一引用后，报告该决定未被引用。
- [EG-S2-AC05-W1] 只扫描 `design` 中的第一个文件。

**[EG-S2-AC06]** 覆盖 EG-S2-C06：设计稿引用一个不存在的编号和一个 superseded 编号，两者都报错。
- [EG-S2-AC06-W1] 只检查编号存在，不检查状态。

**[EG-S2-AC25]** 覆盖 EG-S2-C25：缺少定档清单章节时报 C25；标题写作 `3. 定档清单` 时能正确定位；档位表中没有的 spec ID 出现在清单列头时报错。
- [EG-S2-AC25-W1] 按章节顺序而不是标题文字定位表格，章节调换顺序后读错表。

**[EG-S2-AC07]** 覆盖 EG-S2-C07：分配表漏掉一条 active 决定、同一决定出现在两行、`不进 spec：` 后理由为空，各自报错；`全局约束：……；EG-S2 首先落实` 不计为分配给 EG-S2。
- [EG-S2-AC07-W1] 把"全局约束"或"不进 spec"当作未分配而误报。
- [EG-S2-AC07-W2] 从"全局约束"的说明中抽出 spec ID 并计为分配。

**[EG-S2-AC08]** 覆盖 EG-S2-C08：清单有"是"而规则结果为标准时报错；确认档位低于规则结果且理由为空时报错；规则结果为标准、确认为严格且理由为空时通过；档位取值非法时报错。
- [EG-S2-AC08-W1] 只检查确认档位，不比对规则结果与清单。
- [EG-S2-AC08-W2] 确认档位与规则结果不同即要求理由，误报合法的上调。

**[EG-S2-AC09]** 覆盖 EG-S2-C09：spec 文件存在、但"是"的说明中没有该 spec 实际存在的条款 ID（含写了 `EG-S2-C99` 这类不存在的 ID）时报错；spec 文件不存在时只要求说明非空；单元格既不是 `否` 也不以 `是：` 开头时报错。
- [EG-S2-AC09-W1] spec 文件不存在时也要求条款 ID，导致阶段 3 必然失败。
- [EG-S2-AC09-W2] 只检查说明中的 ID 形如条款 ID，不检查它在 spec 中存在。

**[EG-S2-AC10]** 覆盖 EG-S2-C10：同一 spec 内两个相同条款 ID 报错；`EG-S2-trace.md` 中出现前缀为 `EG-S3` 的条款标记报错；文件名前缀不在地图中报错；两个文件对应同一 spec ID 报错。
- [EG-S2-AC10-W1] 跨 spec 比较 ID 唯一性，把不同 spec 的 `C01` 误报为重复。
- [EG-S2-AC10-W2] 只要条款前缀在地图中就接受，不要求等于文件所属 spec。

**[EG-S2-AC26]** 覆盖 EG-S2-C26：条款段落后紧跟列表、决定引用只在列表项中时，该条款仍算已归类；标题之后的文字不计入前一个条款。
- [EG-S2-AC26-W1] 以空行作为条款块结束，漏掉列表项中的引用。

**[EG-S2-AC11]** 覆盖 EG-S2-C11：既无决定引用、也无事实引用和 AUTHOR-CHOICE 标记的条款被报出。
- [EG-S2-AC11-W1] 把条款文字中 "D-" 后跟非数字的字样当作合法引用。
- [EG-S2-AC11-W2] 接受 `[AUTHOR-CHOICE:maybe]` 之类的未定义写法。

**[EG-S2-AC12]** 覆盖 EG-S2-C12：条款只引用 superseded 决定时，C11 与 C12 各报一条；地图分配给已存在 spec 的某条决定无条款引用时报错；分配给文件尚不存在的 spec 的决定不报错。
- [EG-S2-AC12-W1] 统计全文引用（含标题与说明段），而不是只统计条款块内的引用。
- [EG-S2-AC12-W2] 对文件尚不存在的 spec 也执行分配检查。

**[EG-S2-AC13]** 覆盖 EG-S2-C13：`--freeze` 下残留 substantive 标记时退出码为 1；local 标记所在条款出现在 `local_choices` 中；反引号内描述语法的标记文字不计入。
- [EG-S2-AC13-W1] `--freeze` 下只给警告，退出码仍为 0。

**[EG-S2-AC14]** 覆盖 EG-S2-C14：验收覆盖一个不存在的条款 ID 时报错；两条验收 ID 相同时报错；验收正文中提到但不在覆盖声明里的条款 ID 不计为覆盖。
- [EG-S2-AC14-W1] 允许验收覆盖其他 spec 的条款而不报错。
- [EG-S2-AC14-W2] 把验收块中出现的所有条款 ID 都计为覆盖。

**[EG-S2-AC15]** 覆盖 EG-S2-C15：某条款没有任何验收覆盖时报错。
- [EG-S2-AC15-W1] 只要 spec 中存在任一验收就视为全部覆盖。

**[EG-S2-AC16]** 覆盖 EG-S2-C16：某条验收没有错误实现时报错；错误实现 ID 前缀与所在验收不一致时报错；同一验收下两个 `-W1` 时报错。
- [EG-S2-AC16-W1] 接受不带 ID 的错误实现文字。
- [EG-S2-AC16-W2] 按 ID 前缀而不是所在验收块确定归属，放过放错位置的错误实现。

**[EG-S2-AC17]** 覆盖 EG-S2-C17：删除某验收唯一的测试标记后，tests 模式报告缺失；测试中出现不存在于任何 spec 的验收 ID 时报错；spec 模式不检查测试；标记写在字符串中也能识别。
- [EG-S2-AC17-W1] spec 模式也检查测试标记，导致阶段 4 必然失败。
- [EG-S2-AC17-W2] 只匹配测试函数名，漏掉注释或字符串中的标记。

**[EG-S2-AC22]** 覆盖 EG-S2-C22：设计稿中写在反引号里的决定编号不计入 C05；代码块中的条款标记不计为条款；spec 正文反引号中的 substantive 标记文字不触发 C13；测试文件中反引号内的测试标记仍被识别。
- [EG-S2-AC22-W1] 不排除代码，把描述语法的示例当作真实标记。
- [EG-S2-AC22-W2] 把排除规则也用于测试文件，漏掉写在反引号中的测试标记。

**[EG-S2-AC18]** 覆盖 EG-S2-C18：三种模式各自只运行其检查集合；design 模式下 spec 文件中的条款错误不导致失败；缺少 `--mode`、`--mode tests --freeze`、`--mode design --spec EG-S2` 均返回 2。
- [EG-S2-AC18-W1] 所有模式都运行全部检查。
- [EG-S2-AC18-W2] 忽略非法的参数组合并返回 0。

**[EG-S2-AC23]** 覆盖 EG-S2-C23：存在 EG-S1、EG-S2 两份草稿且 EG-S1 残留 substantive 标记时，`--mode spec --spec EG-S2 --freeze` 通过；`--spec EG-S9` 返回 2。
- [EG-S2-AC23-W1] 忽略 `--spec`，仍检查全部 spec。

**[EG-S2-AC19]** 覆盖 EG-S2-C19：存在失败时退出码为 1，标准输出可被 `json.loads` 解析且 `failures` 每项含 `check`、`path`、`line`、`message`；登记 JSON 语法错误时退出码为 2 且 `result` 为 `error`；单条决定缺字段时退出码为 1；可读摘要只出现在标准错误。
- [EG-S2-AC19-W1] 输入不可读时按检查失败返回 1。
- [EG-S2-AC19-W2] 把可读摘要也写到标准输出，导致 JSON 无法解析。
- [EG-S2-AC19-W3] 失败项缺少行号字段。

**[EG-S2-AC20]** 覆盖 EG-S2-C20：运行前后对 `--root` 下全部文件（含 `__pycache__`）做清单与内容比对，没有任何变化。
- [EG-S2-AC20-W1] 把报告写入项目目录下的缓存文件。
- [EG-S2-AC20-W2] 没有在导入前关闭字节码写入，拆分模块后产生 `__pycache__`。

**[EG-S2-AC21]** 覆盖 EG-S2-C21：在 Python 3.9 的干净虚拟环境（不装任何第三方包）中，命令可运行；源码中不出现 science-gates 的 import。
- [EG-S2-AC21-W1] 隐式依赖开发机上额外安装的第三方包。
- [EG-S2-AC21-W2] 使用 Python 3.10 及以上才有的语法或标准库参数（如 `match` 语句、`glob` 的 `root_dir`），只在 3.13 上验证过。

## 4. 现实核验

事实登记的正式格式由 EG-S3 定义；本 spec 先以临时格式记录（2026-10-14，本机 macOS）。

| ID | 陈述 | 探针 | 结果 |
|---|---|---|---|
| F-01 | macOS 系统 Python 为 3.9.6；Anaconda Python 为 3.13.5 | `/usr/bin/python3 --version`；`python3 --version` | 通过 |
| F-02 | Python 3.9 标准库没有 `tomllib` | `/usr/bin/python3 -c "import tomllib"` 报 ModuleNotFoundError | 通过 |
| F-03 | PyYAML 不属于标准库；本机两个 Python 均另行安装了 6.0.3；干净 CI 环境是否带 PyYAML 未核验 | `python3 -c "import yaml"` | 本机通过；CI 未核验 |
| F-04 | `glob.glob(os.path.join(root, pattern), recursive=True)` 在 3.9 与 3.13 上对 `**` 返回相同的文件集合；`pathlib.Path.glob("**")` 在 3.9 上只返回目录 | 两个解释器各自列出 `docs/**/*.md` 并比较 | 通过（2026-10-14：两者均得 7 个相同文件；pathlib 在 3.9 不返回文件、3.13 返回） |

## 5. 实质选择

已决定：起草时的 P1 → D-021，P2—P6 → D-022；B1-11 → D-023；格式包 F1—F8 → D-024（来自 B1 审查的 B1-01、B1-02、B1-05、B1-09）：

| 包项 | 内容 | 所在条款 |
|---|---|---|
| F1 | 登记 schema：顶层与 schema 值、必需与可选字段、`id` 格式、关系约束（含双向替代、amends 成对） | C02、C04 |
| F2 | AUTHOR-CHOICE 标记只有 local 与 substantive 两种写法 | C11 |
| F3 | 设计稿与 spec 中行内代码和代码块不参与识别；测试文件除外 | C22 |
| F4 | `eg.json` 的键、类型、路径基准、匹配语义 | C01 |
| F5 | spec 文件名以 spec ID 开头；文件内标记前缀必须等于所属 spec ID | C10 |
| F6 | spec 地图三张表按标题定位、列与单元格写法、spec ID 用全称 | C07、C09、C25 |
| F7 | 条款与验收块的边界、覆盖声明语法、错误实现归属与唯一性 | C14、C16、C26 |
| F8 | 退出码 1 与 2 的边界、BOM 与零匹配处理、JSON 报告字段、摘要写到标准错误 | C19、C24 |

局部选择：C20（入口在导入前关闭字节码写入）。
