# EG-S1 身份与检查点

> 状态：草稿 v0.2（阶段 4），实质选择 X1—X5 已由 D-027 决定，待 B1 审查，未冻结。
> 档位：严格。依赖：无。
> 分配决定：D-015、D-018（身份字段）、D-026、D-027；全局约束 D-020、D-021。
> 写法遵循 D-022、D-024；本文中描述语法的示例写在反引号或代码块内。

## 1. 目标与非目标

**目标**：两条命令。`checkpoint` 在流程工作分支上只提交明确列出的文件，并输出可核验的身份；`identity` 给出某个文件在某个 commit 中的身份，并核对工作区中的文件是否与之一致。LLM 不需要计算或抄写任何 hash（D-015）。

**非目标**：

- 不 push、不 merge、不建远端、不改写已有提交（D-015）；
- 不创建或切换分支，不建 worktree（D-026 K1）；
- 冻结记录、审查派发材料中如何引用身份，归 EG-S5；状态文件中的身份字段由 EG-S6 的协议规定写入时机，本 spec 只提供产生身份的命令（D-018）；
- 不修复中断后遗留的暂存状态，只检测并拒绝继续（见 C11）。

## 2. 条款

### 2.1 入口与输出

**[EG-S1-C01]** 入口为 `python3 scripts/eg.py checkpoint` 与 `python3 scripts/eg.py identity`，与 EG-S2 的 `trace` 共用 `scripts/eg.py`（D-022、D-026）。两个子命令都只在标准输出写一个 JSON 对象，可读摘要写到标准错误；`scripts/eg.py` 在导入其他模块前关闭字节码写入，沿用 EG-S2-C20 的做法（D-024）。

**[EG-S1-C02]** 退出码：0 表示提交成功或身份一致；1 表示前置条件不满足、提交被拒绝或身份不一致；2 表示用法错误或输入错误（命令行参数不合法、不在 git 仓库中、git 不可执行）。这是把 D-022 为 `trace` 规定的退出码含义推广到 `checkpoint` 与 `identity`。（D-027 X1）

### 2.2 checkpoint 的前置条件

**[EG-S1-C03]** 命令以 `git rev-parse --show-toplevel` 得到的仓库根目录为基准。`--path` 至少给出一个，可重复；每个路径相对于仓库根目录，不得为绝对路径，不得含 `..`，不得位于 `.git` 下，必须是普通文件（不是目录或符号链接）。（D-027 X5）

**[EG-S1-C04]** 当前分支名必须以 `eg/` 开头；分离 HEAD 或其他分支一律拒绝，退出码 1，不做任何 git 写操作（D-026 K1）。

**[EG-S1-C05]** 提交者身份取自 `git config user.name` 与 `git config user.email`；任一为空即拒绝，退出码 1，不以 `-c` 或环境变量补造身份（D-026 K4，F-15）。

**[EG-S1-C06]** 每个列出的路径，其暂存区内容必须与 HEAD 中的内容相同（或该路径在 HEAD 与暂存区中都不存在）；否则拒绝，退出码 1。这样命令执行 `add` 时不会覆盖用户另行暂存的版本，失败时也能把暂存区精确恢复到执行前的状态。（D-027 X4）

**[EG-S1-C07]** 列出的路径全部与 HEAD 相同时，拒绝并以退出码 1 结束，不产生空提交（D-026 K7）。只有部分路径无改动时照常提交有改动的路径，无改动的路径在输出中标为 `unchanged` 并给出其在 HEAD 中的身份。（D-027 X3）

### 2.3 checkpoint 的提交

**[EG-S1-C08]** 提交步骤固定为：`git add -- <列出的路径>`，然后 `git commit --only -F <提交信息> -- <有改动的路径>`；不使用 `git add -A`、`git add .`、`git commit -a`，也不使用 `--no-verify`（D-026 K2、K3，F-12、F-12b、F-16）。

**[EG-S1-C09]** 提交完成后，未列出的路径在工作区与暂存区中的状态必须与命令执行前完全相同（D-026 K2，F-12b）。

**[EG-S1-C10]** `--kind` 必须为 `spec-freeze`、`tests-freeze`、`candidate`、`review`、`record` 之一；`--spec` 为可选的 spec ID（缺省记为 `-`）；`--message` 为可选的一行摘要（缺省为 `checkpoint`）。提交信息格式如下，最后两行为固定的 trailer（D-026 K5）：

```text
eg(<kind>): <spec ID 或 -> <摘要>

EG-Kind: <kind>
EG-Spec: <spec ID 或 ->
```

**[EG-S1-C11]** 钩子拒绝提交、git 返回非零、或超时（见 C14）时：不产生提交；对列出的路径执行 `git reset -q -- <路径>`，使暂存区恢复到执行前的状态（由 C06 保证可以精确恢复）；输出 `result: refused` 或 `result: error`，退出码 1。命令被强行终止而来不及恢复时，下一次对相同路径执行 `checkpoint` 会因 C06 被拒绝，并在消息中给出恢复命令 `git reset -q -- <路径>`（D-026 K3，F-14）。

**[EG-S1-C12]** checkpoint 的 JSON 输出字段如下；`sha256` 为提交中该文件字节的 SHA-256，`blob` 为 git 对象 ID，均由命令从提交中读回计算，不取自工作区；状态文件等处的身份字段只取自本命令与 C13 的输出（D-015、D-018、D-026 K5，F-13）。

```json
{
  "schema": "eg-checkpoint/v1",
  "result": "committed | refused | error",
  "commit": "<40 位十六进制，未提交时为 null>",
  "branch": "eg/v2",
  "kind": "spec-freeze",
  "spec": "EG-S1",
  "paths": [
    {"path": "docs/specs/EG-S1-checkpoint.md", "status": "committed | unchanged", "blob": "<git 对象 ID>", "sha256": "<64 位十六进制>"}
  ],
  "message": "<拒绝或出错时的原因，成功时为空字符串>"
}
```

### 2.4 identity

**[EG-S1-C13]** `identity --path <路径> [--at <版本>]`：`--at` 缺省为 `HEAD`，可为任何 git 能解析为 commit 的写法。输出该路径在该 commit 中的 `blob` 与 `sha256`，以及工作区文件的 `sha256` 和二者是否一致（`matches`）。路径在该 commit 中不存在或二者不一致时退出码为 1；路径规则同 C03（D-026 K6，F-13）。

```json
{
  "schema": "eg-identity/v1",
  "path": "docs/specs/EG-S2-trace.md",
  "commit": "<40 位十六进制>",
  "blob": "<git 对象 ID>",
  "sha256": "<提交中字节的 SHA-256>",
  "working_sha256": "<工作区文件的 SHA-256，文件不存在时为 null>",
  "matches": true
}
```

### 2.5 执行与故障

**[EG-S1-C14]** 每次调用 git 都以参数列表方式执行（不经过 shell），单次调用超时 300 秒；超时即终止该 git 进程并按 C11 处理。（D-027 X2）

**[EG-S1-C15]** 另一个 git 进程持有仓库锁（`index.lock`）时，命令按 C11 以 `result: error` 结束，不删除锁文件，不重试（D-026 K3）。

**[EG-S1-C16]** 实现只依赖 Python 3.9 及以上的标准库与 git 命令行；已核验的 git 版本为 2.50.1，其他版本在实现开始前与审实现前按 D-012 重跑探针（D-020、D-021，F-11—F-16）。

## 3. 验收

**[EG-S1-AC01]** 覆盖 EG-S1-C01：两个子命令的标准输出各为一个可被 `json.loads` 解析的对象，摘要只出现在标准错误；运行后仓库中不出现 `__pycache__`。
- [EG-S1-AC01-W1] 把摘要也写到标准输出。

**[EG-S1-AC02]** 覆盖 EG-S1-C02：缺少 `--kind` 时退出码为 2；在非 git 目录运行时退出码为 2；在 `main` 分支上运行时退出码为 1；成功提交时为 0。
- [EG-S1-AC02-W1] 在非 eg 分支上以退出码 2 拒绝。
- [EG-S1-AC02-W2] 不在 git 仓库中时以退出码 1 结束。

**[EG-S1-AC03]** 覆盖 EG-S1-C03：绝对路径、含 `..` 的路径、`.git/config`、目录、符号链接各自被拒绝且仓库无任何变化。
- [EG-S1-AC03-W1] 接受目录并把其中所有文件一起提交。
- [EG-S1-AC03-W2] 跟随符号链接提交其指向的文件。

**[EG-S1-AC04]** 覆盖 EG-S1-C04：在 `main`、`feature/x`、分离 HEAD 上运行均被拒绝，且 HEAD、暂存区不变；在 `eg/v2` 上可以提交。
- [EG-S1-AC04-W1] 只拒绝 `main`，放行其他非 eg 分支。
- [EG-S1-AC04-W2] 分离 HEAD 时照常提交。

**[EG-S1-AC05]** 覆盖 EG-S1-C05：在 `GIT_CONFIG_GLOBAL=/dev/null` 且仓库未配置身份的环境中运行被拒绝，消息指出缺少的配置项。
- [EG-S1-AC05-W1] 缺身份时用固定的占位身份提交。

**[EG-S1-AC06]** 覆盖 EG-S1-C06：列出的路径已有与 HEAD 不同的暂存内容时被拒绝，用户暂存的那个版本保持不变。
- [EG-S1-AC06-W1] 直接 `add` 覆盖用户暂存的版本后提交工作区版本。

**[EG-S1-AC07]** 覆盖 EG-S1-C07：两个列出的路径都无改动时退出码为 1 且不产生提交；一个有改动、一个无改动时只提交有改动的那个，另一个在输出中为 `unchanged` 并带 HEAD 中的身份。
- [EG-S1-AC07-W1] 全部无改动时产生空提交（`--allow-empty`）。
- [EG-S1-AC07-W2] 只要有一个路径无改动就整体拒绝。

**[EG-S1-AC08]** 覆盖 EG-S1-C08：用一个记录调用参数的 git 包装脚本运行，调用序列中只有 `add -- <路径>` 与 `commit --only -F … -- <路径>` 两个写操作，不出现 `-A`、`.`、`-a`、`--no-verify`；新建的未跟踪文件能被正确提交。
- [EG-S1-AC08-W1] 不先 `add`，对未跟踪文件直接 `commit -- <路径>`，第一次提交新文件即失败（F-16）。
- [EG-S1-AC08-W2] 使用 `git add -A`。

**[EG-S1-AC09]** 覆盖 EG-S1-C09：执行前另有一个已暂存的无关改动和一个未暂存的无关改动；提交后新提交只含列出的路径，两个无关改动的暂存与工作区状态与执行前逐字节相同。
- [EG-S1-AC09-W1] 用不带 `--only` 的 `git commit`，把已暂存的无关改动一起提交。
- [EG-S1-AC09-W2] 提交后执行 `git reset` 清空整个暂存区，丢失用户暂存的无关改动。

**[EG-S1-AC10]** 覆盖 EG-S1-C10：提交信息首行为 `eg(spec-freeze): EG-S1 freeze v0.1`，末尾两行 trailer 可被 `git log --format=%(trailers:key=EG-Kind)` 读出；`--kind other` 退出码为 2。
- [EG-S1-AC10-W1] 省略 trailer，只写首行。
- [EG-S1-AC10-W2] 接受任意 `--kind` 值。

**[EG-S1-AC11]** 覆盖 EG-S1-C11：安装一个总是失败的 pre-commit 钩子后运行，退出码为 1，HEAD 不变，列出路径的暂存区恢复为执行前状态；人为在 `add` 之后终止进程（故障注入），再次运行时被 C06 拒绝且消息含 `git reset -q -- <路径>`。
- [EG-S1-AC11-W1] 钩子失败后重试并加 `--no-verify`。
- [EG-S1-AC11-W2] 钩子失败后不恢复暂存区，列出的路径停留在已暂存状态。

**[EG-S1-AC12]** 覆盖 EG-S1-C12：输出中每个 `committed` 路径的 `sha256` 等于 `git show <commit>:<路径>` 字节的 SHA-256；在提交后、读回前修改工作区文件（故障注入），输出仍是提交中字节的身份。
- [EG-S1-AC12-W1] 从工作区文件计算 `sha256`。

**[EG-S1-AC13]** 覆盖 EG-S1-C13：对未修改的已提交文件 `matches` 为 true、退出码 0；修改工作区后为 false、退出码 1；`--at` 指定的 commit 中不存在该路径时退出码 1；`--at` 无法解析时退出码 2。
- [EG-S1-AC13-W1] 只比较文件大小或修改时间。
- [EG-S1-AC13-W2] 忽略 `--at`，总是读 HEAD。

**[EG-S1-AC14]** 覆盖 EG-S1-C14：用一个会睡眠的钩子与缩短的超时设置（测试可注入）运行，git 进程被终止，按 C11 恢复暂存区并以退出码 1 结束；源码中调用 git 时不经过 shell。
- [EG-S1-AC14-W1] 不设超时，命令随钩子一直挂起。
- [EG-S1-AC14-W2] 以 `shell=True` 拼接命令字符串，路径中含空格或引号时出错。

**[EG-S1-AC15]** 覆盖 EG-S1-C15：预先创建 `index.lock`（模拟并发的 git 进程）后运行，退出码为 1，锁文件仍在且内容不变，未产生提交；两个 checkpoint 进程并发提交不同路径时，至多一个成功，另一个以 `error` 结束且其列出路径的暂存区恢复。
- [EG-S1-AC15-W1] 发现锁文件时删除它再继续。
- [EG-S1-AC15-W2] 遇到锁时循环重试直到成功。

**[EG-S1-AC16]** 覆盖 EG-S1-C16：在 Python 3.9 的干净虚拟环境中运行全部验收；源码中不出现 science-gates 的 import；实现开始前在本机重跑 `docs/specs/probes/EG-S1-git-probes.sh`。
- [EG-S1-AC16-W1] 使用 Python 3.10 及以上才有的语法或标准库参数。
- [EG-S1-AC16-W2] 依赖第三方 git 库（如 GitPython）。

## 4. 影响登记与迁移（严格档）

| 受影响对象 | 影响 | 处理 |
|---|---|---|
| EG-S2 | 共用 `scripts/eg.py`；EG-S2 只建 `trace` 所需的最小分发部分 | 后实现的一方只增加子命令分支，不改已有子命令的行为；冲突时以 EG-S6 的入口约定为准 |
| EG-S4 | 测试冻结使用 `--kind tests-freeze`（D-014 要求记录 commit） | EG-S4 引用本 spec 的 C10、C12 |
| EG-S5 | 冻结记录、审查派发引用 checkpoint 与 identity 的输出 | EG-S5 定义冻结记录格式，引用本 spec 的 C12、C13 |
| EG-S6 | 状态文件中的身份字段由脚本写入（D-018） | EG-S6 规定写入时机，调用本 spec 的命令 |
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
| F-14b | `--no-verify` 跳过钩子 | 不稳定（6 次中 1 次失败，原因未查明）；本 spec 不使用 |
| F-15 | 未配置 user.name/email 时提交失败 | 稳定通过 |
| F-16 | 未跟踪文件不能直接 `commit -- <路径>`，须先 `add` | 稳定通过 |

## 6. 实质选择

已决定：K1—K7 → D-026；起草中出现的 X1—X5 → D-027：

| 项 | 内容 | 所在条款 |
|---|---|---|
| X1 | 退出码：0 成功或一致；1 前置条件不满足、被拒绝、不一致；2 用法或输入错误（把 D-022 的含义推广到新子命令） | C02 |
| X2 | 每次调用 git 不经过 shell，单次超时 300 秒，超时按失败处理并恢复暂存区 | C14 |
| X3 | 部分路径无改动时照常提交其余路径，无改动的标为 `unchanged`；全部无改动才拒绝 | C07 |
| X4 | 列出的路径若已有与 HEAD 不同的暂存内容则拒绝；失败时把这些路径的暂存区恢复到执行前 | C06、C11 |
| X5 | 路径相对于仓库根目录；只接受普通文件，不接受目录、符号链接和 `.git` 下的路径 | C03 |
