# EG-S1 Review C2

- reviewer: 独立会话（Claude Opus 5.5，Cursor 子代理；未参与写作、B1 与 C1，对它们的了解只来自 review-B1.md、review-C1.md 与 ledger.md）
- date: 2026-10-14
- verdict: PASS

C1-01 至 C1-06 与 B1-02 的并发部分均已关闭。本轮变化没有引入新的 BLOCKER 或 MAJOR，只有 1 条 MINOR（C2-01，C1-02 第二点的残留歧义）和若干备注。

## 输入核对

| 项 | 结果 |
|---|---|
| `git rev-parse --short HEAD` | `3955513`，分支 `eg/v2` |
| `git status --short` | 空（审查结束时再次确认为空） |
| C1 受审 commit → C2 受审 commit | `ffccdf5` → `3955513`；`git diff --stat` 共 9 个文件：decisions.json、design-v2.md、dialogue.md、spec-map.md、ledger.md、review-C1.md、EG-S1-checkpoint.md、探针脚本与运行记录 |
| `git diff ffccdf5 3955513 -- docs/reviews/EG-S1/checklist.md` | 无变化（R1—R8 冻结） |
| `review-B1.md` | 本轮无变化；sha256 `69556890…dcdd`，与账本一致 |
| `review-C1.md` | sha256 `64c963a5320928f5d1db65ca34724778660df33a80aee63cb652822c778d7be4`，与账本一致 |
| `docs/specs/EG-S2-trace.md` sha256 | `97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62`，与给定值一致 |
| decisions.json | 可解析；D-030 `amends` D-026、D-028，D-026 与 D-028 的 `amended_by` 均含 D-030；spec 地图把 D-030 分给 EG-S1；设计稿 §3 引用 D-030；dialogue.md 有 `round-s1-z` 一节 |
| 探针 | `sh docs/specs/probes/EG-S1-git-probes.sh` 连续 3 次退出码 0；每次 20 项 PASS，含新增的 F-15a、F-20、F-20c、F-21、F-21c；git 2.50.1 (Apple Git-155)，Python 3.13.5，macOS |

全部实验都在 `mktemp -d` 创建的临时仓库中进行，设置了 `GIT_CONFIG_GLOBAL=/dev/null`、`GIT_CONFIG_SYSTEM=/dev/null`。参考实现与运行脚本放在项目目录之外，审查结束后已删除；关键逻辑见下文。

### 参考实现（按 v0.4 的 C06—C08、C10—C12、C15 编写）

`ck.py <路径>…`：C06 用 `git diff-index --cached --quiet HEAD -- p` 检查暂存内容，C07 用 `git diff-index --quiet HEAD -- p` 判断有无改动；用 `secrets.token_hex(16)` 生成运行标识，写入带 `EG-Kind`、`EG-Spec`、`EG-Run` 三行 trailer 的提交信息文件；记录 HEAD 为 `h0`；`git add -- <有改动的路径>`；`git commit -q --only -F <文件> -- <路径>`。C12 的实现是：执行 `git log --format='%H %P%x09%(trailers:key=EG-Run,valueonly,separator=%x2C)' h0..HEAD`，取 EG-Run 等于本次标识的提交，要求恰好一个、只有一个父提交、`git diff-tree --name-only -r <父> <提交>` 恰好等于有改动的路径。C15：标准错误含 `index.lock` 且含 `File exists` 时重试，等待依次为 0.2、0.3、0.4、0.5、0.6 秒（合计 2.0 秒）。C11 的恢复是另起一份同样预算的 `git reset -q -- <路径>…`。环境变量 `CK_RESET_AFTER_FAILED_ADD=1` 切换到 C11 的另一种读法（见 C2-01）。

## C1 finding 与 B1-02 关闭核对

| finding | 原严重度 | 结论 | 依据（用 v0.4 文本重试原反例） |
|---|---|---|---|
| C1-01 | MAJOR | **关闭** | C12 现在按 `EG-Run` 在"记录的 HEAD（不含）到当前 HEAD（含）"之间找本次提交，并明确写了"不要求它是当前 HEAD，也不要求它的父提交等于 C08 记录的 HEAD"，内容与 D-030 Z1 一致，原来缺少决定依据的问题（R2）随之消除。我用参考实现重做 C1 的并发实验：2 个进程 ×20 次、2 个进程 ×50 次、3 个进程 ×20 次，**全部满足 AC15 的不变量**，所有进程都以退出码 0 结束（40/40、100/100、60/60）。C1 中被判为失败的情形（后提交一方的父提交是对方的提交）在 2 进程实验中每次都出现（20/20、50/50），3 进程实验中出现 40 次，现在都判为 `committed`。每个报告的提交都带本进程的 EG-Run，且只含本进程的路径；没有残留锁。C1 指出的分歧（`message` 是否列出路径导致 AC15 结论相反）已不存在：正确实现在普通并发下不再进入失败分支。AC12-W3 正是 C1 中的实现 A；它可以被一个确定的测试区分（见备注 3，已实测）。 |
| B1-02（并发部分） | MAJOR | **关闭** | 普通并发见上。B1 的慢钩子反例也重做了：pre-commit 钩子睡眠 2.5 秒并持有锁，6 次；睡眠 5 秒，4 次。每次都是一方退出码 0，另一方因重试用尽以退出码 1 结束，然后按 C11 用独立预算恢复。10/10 次满足不变量：失败方的路径或者已恢复，或者列在 `message` 中；任何新提交都不含另一方的路径；没有锁被删除。故障后的仓库状态由 C11 规定，测试可以观察。 |
| C1-02 | MAJOR | **关闭**（余 MINOR C2-01） | AC15 的上限改为 6 秒，并写明构成：提交与恢复各 2 秒等待，另留 2 秒给 git 调用；C11、C15 写明恢复另有一份预算。实测预先创建并保持 `index.lock`（内容 `LOCKDATA`）：只在 `add` 成功时恢复的实现耗时 2.201 秒和 2.207 秒；`add` 失败也执行恢复的实现耗时 4.328 秒和 4.337 秒。四次都是退出码 1、`result: error`、锁内容不变、没有新提交，**都在 6 秒内**。C11 两种读法的耗时差异已不影响 AC15 的结论。不过 C1-02 第二点的文字歧义仍在，只影响 `message`，见 C2-01。 |
| C1-03 | MINOR | 关闭 | F-15a 现在用 `check` 断言"未配置身份时会以自动推断的身份提交"，3 次运行都是 PASS，本机作者为 `liuyangfan <liuyangfan@liuyangfandeMacBook-Pro.local>`。§5 F-15 的陈述注明了"F-15a 断言"。在不能自动推断身份的主机上，F-15a 会失败，D-012 的重跑因此能发现环境漂移，这正是期望的行为。 |
| C1-04 | MINOR | 关闭 | C05 拒绝 `author.*`、`committer.*` 配置，依据是 D-030 Z2；AC05 增加了 `author.name` 场景与 W4；F-20 和对照 F-20c 都通过。 |
| C1-05 | MINOR | 关闭 | C13 规定：路径违反形式规则，或工作区中存在但不是普通文件时，`result: error`、退出码 1，各身份字段为 `null`，`matches: false`；`result` 的取值说明同步更新；AC13 增加了目录与 `..` 用例。对它与 D-028 Y6 用词的关系，见备注 1。 |
| C1-06 | MINOR | 关闭 | C14 限定取值为 1 到 300 的整数，其他取值为参数错误（退出码 2）；AC14 增加 `301`，与 D-028 Y3"缩短"一致。 |

## 变化范围审查（R1—R8）

| 项 | 结果 | 说明 |
|---|---|---|
| R1 | PASS | C10 第三行 trailer 与 C12 的找提交方式对照 D-030 Z1；C05 对照 Z2；C14 的 1—300 对照 Y3；C11、C15 的恢复独立预算对照 Y2"恢复同样按 Y1 有界重试"。均未扩大或缩小决定。C12 增加的"恰好一个""只有一个父提交"是比决定摘要更细的条款，不构成问题。D-026 K5 原文为"两行 trailer"，已由 D-030 修订并在两端登记。C13 中 `error` 与 Y6 用词的关系见备注 1，不判为冲突。 |
| R2 | PASS | C1 发现的 C12 规则错挂在 Y2 下的问题，已改为引用 D-030 Z1。C12 末尾引用列表中仍保留了 D-028 Y2，但这一句（身份从提交中读回，身份字段只取自命令输出）由同时引用的 D-015、D-018、K5 覆盖；多出的 Y2 不支撑任何没有依据的内容（备注 2）。 |
| R3 | PASS | AC10-W4（固定或可预测的运行标识）可以用"两次运行的值不同"区分。AC12-W2（报告当前 HEAD）可以用 post-commit 钩子场景区分，已实测：参考实现报告本次提交 `b1b328b`，当前 HEAD 是 `e3f5300`。AC12-W3（要求父提交等于执行前的 HEAD）可以用 PATH 上的 git 包装脚本区分：包装脚本在 `commit` 之前插入一个提交，已实测，参考实现输出 `committed`，父提交不是记录的 HEAD。AC05-W4 可以用 `author.name` 场景区分。AC14 的 `301` 可以区分只检查正整数的实现。 |
| R4 | PASS（有 MINOR） | C11 中"若 C08 的 `add` 已执行"在 `add` 本身失败时仍有两种读法，只影响 `message`（C2-01）。identity 在路径非法与 `--at` 无法解析同时出现时，退出码取 1 还是 2 没有规定，属少见组合（备注 4）。 |
| R5 | PASS | 本轮变化没有改变目标、非目标或边界。 |
| R6 | PASS | C12 与 C17 的 `commit` 字段一致：找到但校验不通过时为该提交号，没找到时为 `null`。C13 正文与 `result` 取值说明一致。C16 的事实范围更新为 F-11—F-21，与 §5 一致。AC10 中 W4 排在 W2 之前，只是顺序问题。 |
| R7 | PASS | EG-S2 字节未变；影响登记中 EG-S3、EG-S4、EG-S5 引用 C10、C12，C10 的 trailer 增加一行不改变这些引用的含义。 |
| R8 | PASS | 并发：AC15 的不变量能被正确实现稳定满足（上表 190/190 次）；第一个场景的 6 秒上限能被两种 C11 读法满足（4/4 次）。AC12 的两个故障注入都可以构造，预期状态确定：带防递归保护的 post-commit 钩子输出 `committed`、`commit` 不是 HEAD；在 pre-commit 钩子中 `git add` 另一个文件，会使该文件进入 `commit --only` 的提交，输出 `result: error` 并给出提交号 `7c4139f`。无关路径 `other.txt`、`u.txt` 的暂存条目与执行前逐字节相同，可以认为 C09 在这一路径上仍然成立。崩溃（AC11）、超时（AC14）两部分本轮没有变化，C1 已实测。 |

## Findings

### C2-01

- check: R4
- severity: MINOR
- scope: PRIOR_FINDING（C1-02 第二点：C1 建议写明"`add` 返回成功的路径才需要恢复"，本轮没有采纳这句）
- location: EG-S1-C11
- spec 原文："钩子拒绝提交、git 返回非零、超时（C14）或锁冲突重试用尽（C15）时：不产生提交；若 C08 的 `add` 已执行，对本次全部有改动的路径执行一次 `git reset -q -- <路径>…`……恢复仍失败时……`message` 列出仍处于已暂存状态的路径"。
- 依据：`add` 本身失败时（锁在命令开始前就存在），"`add` 已执行"可以读成"调用过 `add`"，也可以读成"`add` 成功"。git 的 `add` 只在成功时写入暂存区，失败时暂存区没有变化。
- 反例（实测）：在临时仓库中预先创建并保持 `index.lock`，运行参考实现。读法 B（只在 `add` 成功时恢复）用时 2.20 秒，`message` 为 git 的锁错误。读法 A（调用过就恢复，`CK_RESET_AFTER_FAILED_ADD=1`）用时 4.33 秒，恢复同样遇到锁，`message` 为 `still staged: p0.txt; run git reset -q -- p0.txt`；而 `p0.txt` 实际上没有被暂存。两种读法的退出码、`result`、HEAD、暂存区与锁文件完全相同，AC15 第一个场景两者都能通过（都不超过 6 秒）。
- 后果：只影响 `message` 的准确性。读法 A 会误报路径"仍处于已暂存状态"，用户照着执行 `git reset` 也没有害处。仓库状态与通过/失败结论都不受影响，因此不阻塞。
- 最小修复：把 C11 的"若 C08 的 `add` 已执行"改为"若 C08 的 `add` 已返回成功"。

## 非阻塞备注

1. C13 把 identity 的路径规则违反记为 `result: error`、退出码 1，而 D-028 Y6 写的是"路径与仓库状态问题为 1 并记为 refused"。我不判为冲突，理由有三。第一，退出码与 Y6 一致。第二，Y6 中的 `refused`/`error` 来自 checkpoint 的 `result` 取值，来源 B1-04 讨论的也是 checkpoint 的分界；identity 的 `result` 取值从 v0.3 起就是 `match`/`mismatch`/`missing`/`error`，C1 审过并在 R1 判为通过。第三，C1-05 给出的两种修复中本来就包括"记为 error"。如果用户认为 Y6 的 `refused` 也约束 identity，修复只需给 identity 的 `result` 增加 `refused` 一个值。
2. C12 末尾的引用列表"（D-015、D-018、D-026 K5、D-028 Y2，F-13）"中，Y2 已不支撑这一句的任何内容，可以删去，以免再出现 RC-10 那样的误挂。
3. AC12-W3 的说明是"在 post-commit 钩子之外有并发提交时"，但 AC12 正文没有给出对应的注入方式。post-commit 钩子场景中，本次提交的父提交仍等于记录的 HEAD，所以区分不了 W3；AC15 也只有在 W3 实现的 `message` 不列路径时才能区分它。可以确定区分 W3 的写法（已实测）是：PATH 上的 git 包装脚本在遇到 `commit` 时，先用 `read-tree --index-output`、`commit-tree`、`update-ref HEAD` 在单独的暂存文件上插入一个提交，再执行真正的 `commit`。建议在 AC12 中点明这一写法，或者在 AC15 中加一句"并发且无锁超时的场景下，两个进程都应退出码 0"。
4. identity 的检查顺序没有规定：`--path ../x --at nosuchref` 时，先检查参数的实现退出码为 2，先检查路径的实现为 1。属少见组合。
5. AC15 中"报告的提交带本次运行的 `EG-Run`"：输出 JSON 中没有运行标识，测试不能直接读到"本次"的值。可以通过以下方式间接断言：两个进程报告的提交 EG-Run 不同，并且各自只含本进程的路径；也可以用 git 包装脚本截获 `-F` 文件。不影响区分 W2 类错误。如果希望直接断言，可以在 C12 的输出中增加 `run` 字段。
6. F-20 用 `-c author.name=…` 作为配置来源，而 C05 与 AC05 针对的是仓库配置。两者经过同一配置机制，C1 也已在仓库配置下实测过覆盖行为，不影响结论。
7. 读取 trailer 时，`%(trailers:key=EG-Run,valueonly)` 不加 `separator` 会在值后输出换行，按行解析 `git log` 时容易错位；我的第一个运行脚本就因此报错。这属于实现细节，探针已用 `tr -d '\n'` 处理。

## 裁定理由

- C1 的 6 条 finding 全部关闭，B1-02 的并发部分也已关闭：
  - C1-01 与 B1-02 在 v0.4 下重做原反例，覆盖普通并发（共 90 次，含 3 进程）和持锁的慢钩子（10 次），全部满足 AC15 的不变量。C1 中导致相反结论的 `message` 差异，在正确实现中已不会出现。
  - C12 的新规则以 D-030 Z1 为依据，D-030 由用户采纳，登记一致。
- C1-02 的耗时问题已关闭，两种 C11 读法都在 6 秒内（4/4 次）。残留的文字歧义只影响 `message`，判为 MINOR（C2-01）。
- 本轮变化（C05、C10—C15、相应验收、F-15a/F-20/F-21）都能找到决定依据。新增的错误实现都能被合理的测试区分，AC12 的两个故障注入可以构造且结果确定，探针连续 3 次通过。
- 没有未关闭或新增的 BLOCKER/MAJOR，按规则裁定 **PASS**。
