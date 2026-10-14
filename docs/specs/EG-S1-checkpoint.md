# EG-S1 身份与检查点

> 状态：草稿 v0.4（阶段 4），按 C1 审查修订；C1 后的决定已登记为 D-030，待 C2 审查（最后一轮），未冻结。
> 档位：严格。依赖：无。
> 分配决定：D-015、D-018（身份字段）、D-026、D-027、D-028、D-030；全局约束 D-020、D-021。
> 写法遵循 D-022、D-024；本文中描述语法的示例写在反引号或代码块内。

## 1. 目标与非目标

**目标**：两条命令。`checkpoint` 在流程工作分支上只提交明确列出的文件，并输出可核验的身份；`identity` 给出某个文件在某个 commit 中的身份，并核对工作区中的文件是否与之一致。LLM 不需要计算或抄写任何 hash（D-015）。

**非目标**：

- 不 push、不 merge、不建远端、不改写已有提交（D-015）；
- 不创建或切换分支，不建 worktree（D-026 K1）；
- 不为不在 git 中的外部大文件产生身份，这部分已明确后置（D-029）；
- 冻结记录、审查派发材料中如何引用身份，归 EG-S5；状态文件中的身份字段由 EG-S6 的协议规定写入时机，本 spec 只提供产生身份的命令（D-018）；
- 不修复中断后遗留的暂存状态与锁文件，只检测、报告并拒绝继续（见 C11）。

## 2. 条款

### 2.1 入口与输出

**[EG-S1-C01]** 入口为 `python3 scripts/eg.py checkpoint` 与 `python3 scripts/eg.py identity`，与 EG-S2 的 `trace` 共用 `scripts/eg.py`（D-022、D-026）。两个子命令都只在标准输出写一个 JSON 对象，可读摘要写到标准错误（D-026 K5、K6）。`scripts/eg.py` 共用 EG-S2-C20 已规定的入口行为（导入其他模块前关闭字节码写入）。[AUTHOR-CHOICE:local]

**[EG-S1-C02]** 退出码：0 表示提交成功或身份一致；1 表示被拒绝（`refused`：路径与仓库状态不满足前置条件）、执行出错（`error`：git 执行失败、超时、锁冲突）或身份不一致；2 表示命令本身写错：未知参数、缺少必需参数、参数取值非法、`--at` 无法解析、不在 git 仓库中、找不到 `git` 可执行文件（D-027 X1、D-028 Y6）。checkpoint 的前置检查按以下顺序进行，遇到第一个不满足的即停止：参数（C03 中的参数部分、C10）→ 路径（C03）→ 分支（C04）→ 身份（C05）→ 暂存内容（C06）→ 有无改动（C07）（D-028 Y6）。

### 2.2 checkpoint 的前置条件

**[EG-S1-C03]** 命令以 `git rev-parse --show-toplevel` 得到的仓库根目录为基准，从仓库内任何子目录运行结果相同。`--path` 至少给出一个，可重复；缺少 `--path` 为参数错误（退出码 2）。每个路径必须同时满足：相对于仓库根目录；采用规范的 `/` 分隔形式，不含 `.` 或 `..` 段、不以 `/` 结尾、不含连续的 `/`；不位于 `.git` 下；工作区中存在且是普通文件（不是目录或符号链接）；同一路径不重复出现。任一路径不满足即 `refused`、退出码 1，消息指出该路径与违反的规则（D-027 X5、D-028 Y6）。

**[EG-S1-C04]** 当前分支名必须以 `eg/` 开头；分离 HEAD 或其他分支一律 `refused`，退出码 1，不做任何 git 写操作（D-026 K1）。分支尚无任何提交时同样 `refused`，消息说明须先有一个初始提交；这种情况只在 `git init` 后直接使用 eg 分支时出现。[AUTHOR-CHOICE:local]

**[EG-S1-C05]** 提交者身份取自 `git config user.name` 与 `git config user.email`，命令自行检查二者均非空，不依赖 git 报错（git 在未配置时会自动推断身份并提交，F-15）。任一为空，或环境中设置了 `GIT_AUTHOR_NAME`、`GIT_AUTHOR_EMAIL`、`GIT_COMMITTER_NAME`、`GIT_COMMITTER_EMAIL` 中的任一变量（它们会覆盖配置，F-18），即 `refused`、退出码 1，消息指出缺少的配置项或存在的变量名。`git config` 中配置了 `author.name`、`author.email`、`committer.name`、`committer.email` 任一项（它们同样会覆盖 `user.*`，F-20）时同样 `refused`，消息指出该配置项。不以 `-c` 或环境变量补造身份（D-026 K4、D-028 Y5、D-030 Z2）。

**[EG-S1-C06]** 每个列出的路径，其暂存区内容必须与 HEAD 中的内容相同（或该路径在 HEAD 与暂存区中都不存在）；否则 `refused`、退出码 1。这样命令执行 `add` 时不会覆盖用户另行暂存的版本，失败时也能确定暂存区应恢复成什么（D-027 X4）。

**[EG-S1-C07]** 一个列出的路径"有改动"，指它在 HEAD 中不存在，或其工作区内容或可执行位与 HEAD 中的不同，即 `git add` 之后它的暂存条目会与 HEAD 不同（D-026 K7）。列出的路径全部无改动时 `refused`、退出码 1，不产生空提交（D-026 K7）。只有部分路径无改动时照常提交有改动的路径，无改动的路径在输出中标为 `unchanged` 并给出其在 HEAD 中的身份（D-027 X3）。

### 2.3 checkpoint 的提交

**[EG-S1-C08]** 提交步骤固定为：记录当前 HEAD；`git add -- <有改动的路径>`；`git commit --only -F <提交信息文件> -- <有改动的路径>`。不使用 `git add -A`、`git add .`、`git commit -a`，也不使用 `--no-verify`（D-026 K2、K3，F-12、F-12b、F-16）。

**[EG-S1-C09]** 命令结束时（无论成功、被拒绝还是出错），未列出的路径在工作区与暂存区中的状态必须与命令执行前完全相同（D-026 K2，F-12b）。

**[EG-S1-C10]** `--kind` 必须为 `spec-freeze`、`tests-freeze`、`candidate`、`review`、`record` 之一；`--spec` 可选，给出时必须非空且只含字母、数字、`.`、`_`、`-`（缺省记为 `-`）；`--message` 可选，给出时必须是不含换行或回车的非空单行文字（缺省为 `checkpoint`）。不满足即参数错误，退出码 2（D-026 K5、D-028 Y6）。提交信息格式如下，最后三行为固定的 trailer；`<运行标识>` 由命令在每次运行时随机生成，为 32 位小写十六进制（D-030 Z1，F-21）：

```text
eg(<kind>): <spec ID 或 -> <摘要>

EG-Kind: <kind>
EG-Spec: <spec ID 或 ->
EG-Run: <运行标识>
```

**[EG-S1-C11]** 钩子拒绝提交、git 返回非零、超时（C14）或锁冲突重试用尽（C15）时：不产生提交；若 C08 的 `add` 已执行，对本次全部有改动的路径执行一次 `git reset -q -- <路径>…`，使其暂存区恢复到执行前的状态；恢复遇到锁冲突时按 C15 有界重试，恢复的重试使用独立的一份等待预算。恢复成功时，输出 `result: error`（钩子拒绝时为 `refused`），退出码 1。恢复仍失败时输出 `result: error`、退出码 1，`message` 列出仍处于已暂存状态的路径，并给出恢复命令 `git reset -q -- <路径>`；不触碰其他路径，不删除任何锁文件。命令被强行终止而来不及恢复时，下一次对相同路径执行 checkpoint 会因 C06 被拒绝，消息中同样给出恢复命令（D-026 K3、D-028 Y2，F-14、F-17）。

**[EG-S1-C12]** 提交成功的判定与提交号的取得：`git commit` 返回 0 后，在 C08 记录的 HEAD（不含）到当前 HEAD（含）之间，找出 `EG-Run` trailer 等于本次运行标识的提交；必须恰好找到一个，且它只有一个父提交，相对该父提交改动的路径集合恰好等于本次有改动的路径。满足时该提交即为本次提交号，不要求它是当前 HEAD，也不要求它的父提交等于 C08 记录的 HEAD（其间可能有其他进程的提交）。不满足时视为执行出错（`result: error`、退出码 1），已产生的提交不改写，`message` 给出找到的提交号（如有）（D-030 Z1）。`sha256` 为提交中该文件字节的 SHA-256，`blob` 为 git 对象 ID，均从提交中读回计算，不取自工作区；状态文件等处的身份字段只取自本命令与 C13 的输出（D-015、D-018、D-026 K5、D-028 Y2，F-13）。成功时的输出：

```json
{
  "schema": "eg-checkpoint/v1",
  "result": "committed",
  "commit": "<40 位十六进制>",
  "branch": "eg/v2",
  "kind": "spec-freeze",
  "spec": "EG-S1",
  "paths": [
    {"path": "docs/specs/EG-S1-checkpoint.md", "status": "committed", "blob": "<git 对象 ID>", "sha256": "<64 位十六进制>"},
    {"path": "docs/reviews/EG-S1/checklist.md", "status": "unchanged", "blob": "<HEAD 中的对象 ID>", "sha256": "<HEAD 中字节的 SHA-256>"}
  ],
  "message": ""
}
```

### 2.4 identity

**[EG-S1-C13]** `identity --path <路径> [--at <版本>]`：`--at` 缺省为 `HEAD`，可为任何 git 能解析为 commit 的写法，无法解析为参数错误（退出码 2）。路径的形式规则同 C03，但工作区中不要求存在；存在时必须是普通文件。命令输出该路径在该 commit 中的 `blob` 与 `sha256`、工作区文件的 `working_sha256`（文件不存在时为 `null`），以及二者是否一致（`matches`）。`matches` 为 true 时退出码 0；路径在该 commit 中不存在、或工作区文件缺失、或二者不一致时退出码 1。路径不满足形式规则、或工作区中存在但不是普通文件时，`result` 为 `error`、退出码 1，`commit`、`blob`、`sha256`、`working_sha256` 为 `null`，`matches` 为 false，`message` 指出违反的规则（D-026 K6、D-028 Y6，F-13）。

```json
{
  "schema": "eg-identity/v1",
  "result": "match | mismatch | missing | error",
  "path": "docs/specs/EG-S2-trace.md",
  "commit": "<40 位十六进制，--at 无法解析时为 null>",
  "blob": "<git 对象 ID，该 commit 中不存在时为 null>",
  "sha256": "<提交中字节的 SHA-256，该 commit 中不存在时为 null>",
  "working_sha256": "<工作区文件的 SHA-256，文件不存在时为 null>",
  "matches": true,
  "message": ""
}
```

`result` 取值：`match`（一致）、`mismatch`（二者都存在但不一致，或工作区文件缺失）、`missing`（该 commit 中不存在该路径）、`error`（命令写错、路径不满足规则或 git 执行出错）。

### 2.5 非成功输出

**[EG-S1-C17]** checkpoint 在退出码为 1 或 2 时同样输出 `eg-checkpoint/v1` 对象：`result` 为 `refused` 或 `error`（退出码 2 时为 `error`）；`commit` 为 `null`（C12 中提交已产生但校验不通过时为该提交号）；`branch` 在无法确定时为 `null`；`kind`、`spec` 为命令行给出的值，未给出或非法时为 `null`；`paths` 列出命令行给出的每个路径，`status` 取 `not_committed`，`blob` 与 `sha256` 为 `null`；`message` 非空，说明原因（D-028 Y6）。identity 的非成功输出见 C13（D-028 Y6）。

### 2.6 执行与故障

**[EG-S1-C14]** 通过 `PATH` 查找 `git` 可执行文件，每次调用都以参数列表方式执行（不经过 shell），并在独立的进程组中启动。单次调用超时为 300 秒；环境变量 `EG_GIT_TIMEOUT_SECONDS` 为 1 到 300 之间的整数时以它为准，只能用于缩短超时；其他取值为参数错误（退出码 2）。超时后先向整个进程组发 SIGTERM，等待 10 秒仍未退出再发 SIGKILL；之后按 C11 处理，残留的锁文件不删除（D-027 X2、D-028 Y3，F-19）。

**[EG-S1-C15]** git 因另一进程持有仓库锁而失败时（标准错误中出现 `index.lock` 且含 `File exists`），对该次 git 调用做有界重试：最多 5 次，各次之间的等待合计不超过 2 秒；C11 中的恢复另有一份同样的预算；其他错误不重试。重试用尽即按 C11 以 `result: error` 结束。任何情况下都不删除锁文件（D-028 Y1，F-17）。

**[EG-S1-C16]** 实现只依赖 Python 3.9 及以上的标准库与 git 命令行（D-020、D-021）。按 D-012，在实现开始前与审实现前各重跑一次 `docs/specs/probes/EG-S1-git-probes.sh`；运行环境的 git 版本不是 2.50.1 时，在运行记录中单列（D-012，F-11—F-21）。

## 3. 验收

**[EG-S1-AC01]** 覆盖 EG-S1-C01：两个子命令的标准输出各为一个可被 `json.loads` 解析的对象，摘要只出现在标准错误；运行后仓库中不出现 `__pycache__`。
- [EG-S1-AC01-W1] 把摘要也写到标准输出。

**[EG-S1-AC02]** 覆盖 EG-S1-C02：缺少 `--kind`、`--kind other` 时退出码 2；在非 git 目录运行时 2；`PATH` 中没有 git 时 2；在 `main` 分支上运行时 1 且 `result` 为 `refused`；同时给出绝对路径并位于 `main` 分支时，消息指出路径问题（路径检查先于分支检查）；成功提交时 0。
- [EG-S1-AC02-W1] 在非 eg 分支上以退出码 2 拒绝。
- [EG-S1-AC02-W2] 不在 git 仓库中时以退出码 1 结束。
- [EG-S1-AC02-W3] 先检查分支再检查路径，消息指出分支问题。

**[EG-S1-AC03]** 覆盖 EG-S1-C03：拼错的不存在路径、绝对路径、含 `..` 或 `./` 的路径、以 `/` 结尾的路径、`.git/config`、目录、符号链接、重复给出的同一路径，各自 `refused`、退出码 1 且仓库无任何变化；缺少 `--path` 时退出码 2；从仓库的子目录运行与从根目录运行结果相同。
- [EG-S1-AC03-W1] 接受目录并把其中所有文件一起提交。
- [EG-S1-AC03-W2] 跟随符号链接提交其指向的文件。
- [EG-S1-AC03-W3] 把路径解释为相对于当前目录，在子目录中运行时提交了错误的文件或报路径不存在。

**[EG-S1-AC04]** 覆盖 EG-S1-C04：在 `main`、`feature/x`、分离 HEAD 上运行均 `refused`，HEAD 与暂存区不变；在尚无提交的 `eg/x` 分支上 `refused`；在 `eg/v2` 上可以提交。
- [EG-S1-AC04-W1] 只拒绝 `main`，放行其他非 eg 分支。
- [EG-S1-AC04-W2] 分离 HEAD 时照常提交。

**[EG-S1-AC05]** 覆盖 EG-S1-C05：在 `GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_SYSTEM=/dev/null` 且仓库未配置身份的环境中，对已跟踪文件运行，`refused` 且不产生提交，消息指出缺少的配置项；身份已配置但设置了 `GIT_AUTHOR_NAME` 时 `refused`，消息指出该变量名；仓库配置了 `author.name` 时 `refused`，消息指出该配置项。
- [EG-S1-AC05-W1] 缺身份时用固定的占位身份提交。
- [EG-S1-AC05-W2] 不检查配置，依赖 git 报错；git 以自动推断的身份提交成功（F-15）。
- [EG-S1-AC05-W3] 不检查身份环境变量，以环境变量中的身份提交（F-18）。
- [EG-S1-AC05-W4] 只检查 `user.*`，以 `author.name` 配置的身份提交（F-20）。

**[EG-S1-AC06]** 覆盖 EG-S1-C06：列出的路径已有与 HEAD 不同的暂存内容时 `refused`，用户暂存的那个版本保持不变。
- [EG-S1-AC06-W1] 直接 `add` 覆盖用户暂存的版本后提交工作区版本。

**[EG-S1-AC07]** 覆盖 EG-S1-C07：两个列出的路径都无改动时退出码 1 且不产生提交；一个有改动、一个无改动时只提交有改动的那个，另一个为 `unchanged` 并带 HEAD 中的身份；只改了可执行位的文件算有改动并被提交。
- [EG-S1-AC07-W1] 全部无改动时产生空提交（`--allow-empty`）。
- [EG-S1-AC07-W2] 只要有一个路径无改动就整体拒绝。
- [EG-S1-AC07-W3] 只比较文件字节，把只改了可执行位的文件判为无改动。

**[EG-S1-AC08]** 覆盖 EG-S1-C08：用一个记录调用参数的 git 包装脚本运行，调用序列中只有 `add -- <路径>` 与 `commit --only -F … -- <路径>` 两个写操作，不出现 `-A`、`.`、`-a`、`--no-verify`；新建的未跟踪文件能被正确提交。
- [EG-S1-AC08-W1] 不先 `add`，对未跟踪文件直接 `commit -- <路径>`，第一次提交新文件即失败（F-16）。
- [EG-S1-AC08-W2] 使用 `git add -A`。

**[EG-S1-AC09]** 覆盖 EG-S1-C09：执行前另有一个已暂存的无关改动和一个未暂存的无关改动；分别在提交成功、因分支被拒绝、因钩子失败三种情况下运行，两个无关改动的暂存与工作区状态都与执行前逐字节相同，成功时的新提交只含列出的路径。
- [EG-S1-AC09-W1] 用不带 `--only` 的 `git commit`，把已暂存的无关改动一起提交。
- [EG-S1-AC09-W2] 失败后执行不带路径的 `git reset`，清空整个暂存区，丢失用户暂存的无关改动。

**[EG-S1-AC10]** 覆盖 EG-S1-C10：提交信息首行为 `eg(spec-freeze): EG-S1 freeze v0.4`，trailer 可被 `git log --format='%(trailers:key=EG-Kind,valueonly)'` 读出为 `spec-freeze`；`EG-Run` 为 32 位小写十六进制，两次运行的值不同；`--message` 含换行时退出码 2 且不产生提交；`--spec` 含空格时退出码 2。
- [EG-S1-AC10-W1] 省略 trailer，只写首行。
- [EG-S1-AC10-W4] 使用固定的或可预测的运行标识（如时间戳），两次运行相同。
- [EG-S1-AC10-W2] 接受任意 `--kind` 值。
- [EG-S1-AC10-W3] 接受含换行的 `--message`，使其中伪造的 `EG-Kind:` 行成为 trailer。

**[EG-S1-AC11]** 覆盖 EG-S1-C11：安装一个总是失败的 pre-commit 钩子后运行，退出码 1、`result` 为 `refused`，HEAD 不变，列出路径的暂存区恢复为执行前状态；在 `add` 之后、`commit` 之前人为终止进程（故障注入），再次运行时被 C06 拒绝且消息含 `git reset -q -- <路径>`；在 `add` 之后创建 `index.lock` 并在整个重试窗口内保持（故障注入），输出 `result: error`，`message` 列出仍已暂存的路径与恢复命令，锁文件仍在。
- [EG-S1-AC11-W1] 钩子失败后重试并加 `--no-verify`。
- [EG-S1-AC11-W2] 钩子失败后不恢复暂存区，列出的路径停留在已暂存状态且消息中没有说明。
- [EG-S1-AC11-W3] 恢复遇到锁时删除锁文件再恢复。

**[EG-S1-AC12]** 覆盖 EG-S1-C12：输出中每个 `committed` 路径的 `sha256` 等于 `git show <commit>:<路径>` 字节的 SHA-256；在提交后、读回前修改工作区文件（故障注入），输出仍是提交中字节的身份；用一个在本次提交之后立即再提交另一文件的 post-commit 钩子（模拟并发，故障注入；钩子须以环境变量等方式防止自身提交再次触发自己，否则会无限递归）运行，输出 `result: committed`，`commit` 为本次提交而不是当前 HEAD；本次提交的改动路径与列出的路径不一致时（用一个修改暂存区的 pre-commit 钩子注入），输出 `result: error` 并给出找到的提交号。
- [EG-S1-AC12-W1] 从工作区文件计算 `sha256`。
- [EG-S1-AC12-W2] 直接读取提交后的 HEAD 作为本次提交号，在 post-commit 钩子场景下报告了另一个提交。
- [EG-S1-AC12-W3] 要求父提交等于执行前的 HEAD，在 post-commit 钩子之外有并发提交时把正确的提交判为失败。

**[EG-S1-AC13]** 覆盖 EG-S1-C13：对未修改的已提交文件 `result: match`、退出码 0；修改工作区后 `mismatch`、退出码 1；工作区中已删除的文件对旧 commit 查询，输出提交中的 `blob` 与 `sha256`、`working_sha256: null`、退出码 1；该 commit 中不存在的路径为 `missing`、`blob` 与 `sha256` 为 `null`、退出码 1；`--at` 无法解析时退出码 2 且 `commit` 为 `null`；路径为目录或含 `..` 时 `result: error`、退出码 1。
- [EG-S1-AC13-W1] 只比较文件大小或修改时间。
- [EG-S1-AC13-W2] 忽略 `--at`，总是读 HEAD。
- [EG-S1-AC13-W3] 工作区文件已删除时按路径规则拒绝，不输出提交中的身份。

**[EG-S1-AC17]** 覆盖 EG-S1-C17：分别触发分支拒绝、钩子失败、参数错误三种情况，标准输出都是 `eg-checkpoint/v1` 对象，`paths` 中每项为 `not_committed` 且 `blob`、`sha256` 为 `null`，`message` 非空。
- [EG-S1-AC17-W1] 失败时标准输出为空或只有文字。
- [EG-S1-AC17-W2] 失败时 `paths` 中仍填入工作区文件的 `sha256`。

**[EG-S1-AC14]** 覆盖 EG-S1-C14：设置 `EG_GIT_TIMEOUT_SECONDS=1`，用一个睡眠 6 秒、会自己再启动子进程的 pre-commit 钩子运行：退出码 1，不产生提交，不残留 `index.lock`，列出路径的暂存区已恢复，钩子及其子进程在命令结束时都已不存在；`EG_GIT_TIMEOUT_SECONDS=abc` 或 `301` 时退出码 2；源码中调用 git 时不经过 shell；路径中含空格或引号的文件能被正确提交。
- [EG-S1-AC14-W1] 不设超时，命令随钩子一直挂起。
- [EG-S1-AC14-W2] 用 `subprocess.run(timeout=…)` 的缺省行为只对 git 发 SIGKILL，残留 `index.lock`，暂存区无法恢复（F-19）。
- [EG-S1-AC14-W3] 以 `shell=True` 拼接命令字符串。

**[EG-S1-AC15]** 覆盖 EG-S1-C15：预先创建 `index.lock` 并保持，运行后退出码 1、`result: error`，锁文件仍在且内容不变，未产生提交，总耗时不超过 6 秒（提交与恢复各 2 秒的等待预算，另留 2 秒供各次 git 调用）；在第 2 次重试前移除锁，命令成功提交；两个 checkpoint 进程并发提交不同路径，重复 20 次，每次都满足以下不变量：退出码只为 0 或 1；退出码为 0 的进程报告的提交带本次运行的 `EG-Run`，且只含它自己的路径；任何新提交都不包含另一进程的路径；退出码为 1 的进程，其路径要么已恢复，要么列在 `message` 中；没有锁文件被删除。
- [EG-S1-AC15-W1] 发现锁文件时删除它再继续。
- [EG-S1-AC15-W2] 遇到锁时无限重试直到成功。
- [EG-S1-AC15-W3] 遇到锁立即失败，不重试；第 2 次重试前移除锁的场景失败。

**[EG-S1-AC16]** 覆盖 EG-S1-C16：在 Python 3.9 的干净虚拟环境中运行全部验收；源码中不出现 science-gates 的 import；实现开始前与审实现前各有一份探针运行记录。
- [EG-S1-AC16-W1] 使用 Python 3.10 及以上才有的语法或标准库参数。
- [EG-S1-AC16-W2] 依赖第三方 git 库（如 GitPython）。

## 4. 影响登记与迁移（严格档）

| 受影响对象 | 影响 | 处理 |
|---|---|---|
| EG-S2 | 共用 `scripts/eg.py`；EG-S2 只建 `trace` 所需的最小分发部分（EG-S2 §1 非目标） | 后实现的一方只增加子命令分支，不改已有子命令的行为；冲突时以 EG-S6 的入口约定为准 |
| EG-S3 | 依赖 EG-S1：事实登记与探针运行记录用 `--kind record` 入库，探针结果引用 commit | EG-S3 引用本 spec 的 C10、C12 |
| EG-S4 | 测试冻结使用 `--kind tests-freeze`（D-014 要求记录 commit） | EG-S4 引用本 spec 的 C10、C12 |
| EG-S5 | 冻结记录、审查派发引用 checkpoint 与 identity 的输出，含失败输出 | EG-S5 定义冻结记录格式，引用本 spec 的 C12、C13、C17 |
| EG-S6 | 状态文件中的身份字段由脚本写入（D-018）；统一入口约定 | EG-S6 规定写入时机，调用本 spec 的命令 |
| 0.1.0 | `subject-<round>` 字节副本与自定义 digest 机制被 git 身份取代 | 迁移说明归 EG-S6 |
| 现有工件 | `docs/reviews/EG-S2/freeze.json` 的身份为 sha256（D-015 落地前）；其字节已随 `f5f112a` 入库并核对一致 | 不改写；EG-S5 落地后可补一份引用 commit 的冻结记录 |

## 5. 现实核验

探针：`docs/specs/probes/EG-S1-git-probes.sh`；运行记录：`docs/specs/probes/EG-S1-git-probes.log.md`。钉住版本：git 2.50.1 (Apple Git-155)，macOS，2026-10-14。

| ID | 陈述 | 结果 |
|---|---|---|
| F-11 | `git worktree add -b` 不改变主工作区的分支与文件 | 稳定通过（本 spec 未使用 worktree，仅作 K1 的决策依据） |
| F-12 | 先 `add` 再 `commit --only -- <路径>` 只提交指定路径 | 稳定通过 |
| F-12b | 上述提交后，其他已暂存改动仍留在暂存区 | 稳定通过 |
| F-13 | `git show <commit>:<路径>` 的字节与提交时的文件一致 | 稳定通过 |
| F-14 | pre-commit 钩子可中止提交 | 稳定通过 |
| F-14b | `--no-verify` 跳过钩子 | 曾出现 1 次失败，原因未查明；本 spec 不使用 |
| F-15 | 未配置 user.name/email 时，git 会以自动推断的身份提交已跟踪文件（F-15a 断言）；`git config user.name` 为空 | 通过（v2，带对照 F-15c；旧版因 F-16 误判，已更正） |
| F-16 | 未跟踪文件不能直接 `commit -- <路径>`，须先 `add` | 稳定通过 |
| F-17 | `index.lock` 存在时 `git reset -- <路径>` 失败 | 通过（带对照 F-17c） |
| F-18 | `GIT_AUTHOR_NAME` 覆盖已配置的 user.name | 通过（带对照 F-18c） |
| F-19 | 提交阻塞在钩子中时，向进程组发 SIGTERM 不残留 `index.lock`；只对 git 发 SIGKILL 会残留 | 通过（F-19c 为对照） |
| F-20 | `author.name` 配置覆盖 `user.name` | 通过（带对照 F-20c） |
| F-21 | 自定义 trailer `EG-Run` 可由 `git log --format='%(trailers:key=EG-Run,valueonly)'` 读出 | 通过（带对照 F-21c） |

## 6. 实质选择

已决定：K1—K7 → D-026；X1—X5 → D-027；B1 后的 Y1、Y2、Y3、Y5、Y6 → D-028，Y4 → D-029；C1 后的 Z1、Z2 → D-030。

局部选择：C01（共用 EG-S2-C20 的入口行为）、C04（分支尚无提交时拒绝）。
