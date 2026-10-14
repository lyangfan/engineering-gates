# EG-S1 Review B1

- reviewer: 独立会话（Claude Opus 5.5，Cursor 子代理；未继承作者上下文）
- date: 2026-10-14
- verdict: FAIL

另有需用户决定的阻塞项：B1-01（锁冲突策略），B1-02、B1-03 的修复（失败恢复与超时终止方式，属"并发 / 提交点 / 恢复"触碰面），B1-06（D-015 外部大文件身份的去向）。修复时须一并交用户。

## 输入核对

`git rev-parse HEAD` = `be59a0ded51f358ff2f65492a87b1646068f613e`，分支 `eg/v2`，`git status --short` 为空。用 `git show be59a0d…:<path> | shasum -a 256` 逐个核对：

| 路径 | 结果 |
|---|---|
| docs/specs/EG-S1-checkpoint.md | 与给定 sha256 一致 |
| docs/reviews/EG-S1/checklist.md | 一致 |
| docs/design/decisions.json | 一致 |
| docs/design/design-v2.md | 一致 |
| docs/design/spec-map.md | 一致 |
| docs/specs/EG-S2-trace.md | 一致 |
| docs/specs/probes/EG-S1-git-probes.sh | 一致 |
| docs/specs/probes/EG-S1-git-probes.log.md | 一致 |

实验环境：git 2.50.1 (Apple Git-155)，macOS；全部实验在 `mktemp -d` 目录中进行。`sh docs/specs/probes/EG-S1-git-probes.sh` 本次运行全部 PASS，退出码 0。

## 检查表结果（R1—R8）

| 项 | 结果 | 证据 |
|---|---|---|
| R1 忠实性 | PASS（有 MINOR） | C02↔X1、C03↔X5、C04↔K1、C05↔K4、C06/C11↔X4、C07↔K7+X3、C08/C09↔K2+K3、C10↔K5、C12↔D-015+K5、C13↔K6、C14↔X2 逐条对照，没有与决定冲突的内容。`--spec`、`--message`、`blob` 字段、提交信息首行格式比 K5/K6 摘要更细，按约定不构成问题。C16 的措辞可被读成缩小 D-012（B1-08，MINOR）。 |
| R2 未标出的实质选择 | FAIL | C15 的"不重试"属于"并发 / 提交点 / 恢复"触碰面（spec 地图该项正指向 C15），引用的 K3 只讲钩子，不包含锁的处理（B1-01）。C05 引用的 F-15 不成立：探针因 F-16 的原因通过（B1-05）。C01 字节码一句引用 D-024，但 D-024 不含此内容（B1-07，MINOR）。 |
| R3 错误实现可区分性 | FAIL | 列出的 W 都能被合理测试区分。但 C05 最常见的错误实现（不检查配置、交给 git 自己失败）没有列出，并且这种实现能否通过 AC05 取决于主机（B1-05）。AC14 依赖 spec 未定义的注入接口（B1-10，MINOR）。 |
| R4 输入边界与失败路径 | FAIL | 非成功路径的退出码与 JSON 未定（B1-04）；身份来源的边界未定（B1-05）。另有 MINOR：怎样算"改动"（B1-09），`--message`/`--spec`/路径规范化（B1-11）。 |
| R5 目标与边界 | FAIL | D-015 整条分给 EG-S1，其中"不在 git 中的外部大文件只记录 sha256 与不可变来源"既没有条款落实，也没有写成非目标或交给其他 spec（B1-06）。其余边界与地图一致：不建 worktree、冻结记录归 EG-S5、写入时机归 EG-S6。 |
| R6 一致性 | FAIL | C13"路径规则同 C03"要求普通文件，但同一条款又规定工作区文件不存在时 `working_sha256` 为 `null`；C11 的 `refused`/`error` 没有映射规则（均并入 B1-04）。条款交叉引用（C11→C14、C15→C11、C06↔C11）与 §6 表一致。 |
| R7 影响登记 | PASS（有 MINOR） | 与 EG-S2 核对：EG-S2 非目标写明只建 `trace` 的最小分发部分；EG-S1-C01 沿用 EG-S2-C20 的字节码做法与 C19 的 stdout/stderr 约定；EG-S1 不读 `eg.json`，与 EG-S2-C01 不冲突。没有发现迫使 EG-S2 改变行为的影响。漏登记 EG-S3（B1-12，MINOR）。 |
| R8 故障与仓库状态 | FAIL | 三类故障都有验收（AC11 崩溃、AC15 并发、AC14 超时），但 C11 的前提"由 C06 保证可以精确恢复"在恢复命令本身拿不到锁时不成立。并发时恢复会失败（B1-02，已实测）；以 SIGKILL 终止超时进程会留下 `index.lock`，导致恢复失败（B1-03，已实测）。 |

## Findings

### B1-01

- check: R2
- severity: BLOCKER — NEEDS_USER_DECISION
- location: EG-S1-C15（AC15）
- spec 原文：C15"另一个 git 进程持有仓库锁（`index.lock`）时，命令按 C11 以 `result: error` 结束，不删除锁文件，不重试（D-026 K3）。"
- 依据：
  - K3 原文："尊重仓库钩子，钩子拦下提交时命令失败退出且不提交"。K3 不包含锁冲突时的处理，也不包含"不重试"。X2 只讲超时，X4 只讲已暂存内容与失败后恢复。
  - spec 地图定档清单："并发 / 提交点 / 恢复｜是：检查点提交与失败恢复（EG-S1-C11、EG-S1-C15）"。可见 C15 本身就落在触碰面上。
  - D-011：碰到触碰面的 AUTHOR-CHOICE 是实质选择，须冻结前交用户决定；把它写成"依据某决定"同样绕过了这一要求。
- 反例：IDE 的 git 集成在后台定期执行 `git status`，会短暂持有 `index.lock`。checkpoint 恰好在这时执行 `git add`：
  - 实现 A 立即失败：退出码 1，HEAD 不变；
  - 实现 B 有界重试（例如 3 次，每次间隔 200 ms），随后成功：退出码 0，HEAD 前进。
  两者都满足 K3 与 X1—X5。AC15-W2 只排除"循环重试直到成功"，没有排除有界重试。"不删除锁文件"可以从 K3"尊重仓库的保护"推出；"不重试"推不出来。
- 后果：用户没有决定过的并发行为会作为合同冻结。是否重试直接决定用户在 IDE 中使用时偶发失败的频率。
- 最小修复：把锁冲突策略（立即失败，或有界重试及其上限）交用户决定并登记，然后让 C15 引用新决定。建议与 B1-02、B1-03 的恢复策略一起作为一个决定包处理。

### B1-02

- check: R8
- severity: MAJOR（修复内容需用户决定，属"恢复"触碰面）
- location: EG-S1-C11、EG-S1-C15、EG-S1-AC15
- spec 原文：
  - C11"对列出的路径执行 `git reset -q -- <路径>`，使暂存区恢复到执行前的状态（由 C06 保证可以精确恢复）"；
  - AC15"两个 checkpoint 进程并发提交不同路径时，至多一个成功，另一个以 `error` 结束且其列出路径的暂存区恢复"。
- 依据：C06 只保证恢复的**目标状态**已知，不保证 `git reset` 能执行。`git reset` 同样需要 `index.lock`。检查表 R8 要求故障后的暂存区与锁文件状态被明确规定。
- 反例（实测）：
  - 锁在 `add` 与 `commit` 之间出现：先 `git add -- n.txt`，再 `touch .git/index.lock`。此时 `git commit --only -- n.txt` 与 `git reset -q -- n.txt` 都报 `Unable to create '.../index.lock': File exists`，`n.txt` 留在暂存区。
  - 真实并发：B 已 `git add -- p2`；A 执行 `git add -- p1 && SLOWHOOK=1 git commit --only -- p1`，A 的 pre-commit 钩子睡眠 2 秒，期间持有锁。0.5 秒后 B 的 `commit --only -- p2` 失败，B 的 `git reset -q -- p2` 也失败。最终输出 `B: restore failed (lock held by A)`、`A: ok`，`p2` 仍在暂存区。
  - 不带钩子，两个"add→commit --only→失败则 reset"序列并发 40 次：恰好一个成功 7 次，**两个都失败 33 次**，两个都成功 0 次。时序不重叠时两个都会成功。
  - 由此，实现 A 对恢复失败只报 `error`、留下已暂存路径；实现 B 等锁后重试恢复（C15 的"不重试"是否适用于恢复命令，没有规定）。两者留下的暂存区不同。AC15 的"至多一个成功"与"暂存区恢复"都不是正确实现能保证的结果，按字面写出的测试要么时有时无地失败，要么会判错一个正确实现。
  - 附带一点：并发下用 `git rev-parse HEAD` 读取刚产生的提交，可能读到另一个进程的提交；C12 没有规定提交号怎样取得。
- 后果：严格档要求的并发故障注入没有确定的预期状态，测试作者与实现者会在 AC15 上产生异议（D-014）。
- 最小修复：
  - 在 C11 中规定恢复失败的结果：`result: error`、退出码 1、`message` 列出仍处于已暂存状态的路径并给出恢复命令；不触碰其他路径；不删除锁。恢复时是否允许有界重试，随 B1-01 一并交用户决定。
  - 把 AC15 改为断言不变量：每个进程的退出码为 0 或 1；任何提交都不包含另一进程的路径；退出码为 1 的进程，其路径要么恢复到执行前，要么在 `message` 中列出；锁文件没有被删除。
  - 在 C12 中规定提交号的取得方式，例如比较提交前后的 HEAD 并核对父提交。

### B1-03

- check: R8
- severity: MAJOR（修复内容需用户决定，属"恢复"触碰面）
- location: EG-S1-C14、EG-S1-C11、EG-S1-AC14
- spec 原文：C14"超时即终止该 git 进程并按 C11 处理"；AC14"git 进程被终止，按 C11 恢复暂存区并以退出码 1 结束"。
- 依据：X2"超时按失败处理并恢复暂存区"；C15"不删除锁文件"；R8 要求故障后的锁文件状态被明确规定。
- 反例（实测）：pre-commit 钩子 `sleep 6`，用 Python 在 1 秒时终止 `git commit --only`：
  - `subprocess.run(..., timeout=1)` 是 Python 的默认写法，超时后发 SIGKILL。结果 `.git` 中留下 `index.lock` 与 `next-index-80684.lock`，随后 `git reset -q -- a.txt` 返回 128（锁已存在），`a.txt` 留在暂存区。
  - `Popen.terminate()` 发 SIGTERM，git 退出时自行清理锁文件，`git reset` 返回 0，暂存区恢复。
  - 两种方式下，钩子的子进程（`sleep 6`）都继续存活，因为只终止了 git 进程本身。
  
  于是：实现 A 用默认的 `subprocess.run(timeout=)`，无法满足 C11；如果它为了恢复而删除自己子进程留下的锁，又与 C15 的精神冲突。实现 B 用 SIGTERM。实现 C 终止整个进程组，钩子也被终止。三者在锁文件、暂存区、以及仍在运行的钩子是否会继续改动文件这几方面，留下的状态都不同。C11 中"由 C06 保证可以精确恢复"对 A 不成立。
- 后果：最自然的实现会在 AC14 上失败，或者为了通过而删除锁；超时后仓库会是什么状态，没有可测的规定。
- 最小修复：在 C14 中规定终止方式。例如：git 以新进程组启动；超时后向该进程组发 SIGTERM，等待一段固定时间，仍未退出再发 SIGKILL。若此后仍有锁文件残留，不删除，按 B1-02 的"恢复失败"输出。AC14 应断言：走 SIGTERM 路径时不残留 `index.lock`，暂存区已恢复，钩子进程已结束。这是对 X2 的细化，并落在恢复触碰面上，建议随 B1-01 的决定包交用户确认。

### B1-04

- check: R4（兼 R6）
- severity: MAJOR
- location: EG-S1-C02、C03、C11、C12、C13、C14；AC03、AC13
- spec 原文：
  - C02"1 表示前置条件不满足、提交被拒绝或身份不一致；2 表示用法错误或输入错误（命令行参数不合法、不在 git 仓库中、git 不可执行）"；
  - C03 列出路径规则，没有写退出码；AC03 只写"各自被拒绝且仓库无任何变化"；
  - C11"输出 `result: refused` 或 `result: error`"；
  - C13"路径规则同 C03"，同时规定"`working_sha256`：工作区文件的 SHA-256，文件不存在时为 null"。
- 依据：X1 只给出三类含义，没有把每种输入映射到类别。C04—C07 都写了"拒绝，退出码 1"，唯独 C03 没写。AC13 把"`--at` 无法解析"定为 2，这是一个引用仓库状态的参数错误，与"路径不存在"性质相近。D-013 要求测试作者只依据 spec 先写测试。
- 反例：
  - `checkpoint --kind review --path docs/reviews/EG-S1/reveiw-B1.md`（路径拼错，文件不存在；LLM 调用者常见）。实现 A 视为"命令行参数不合法 / 输入错误"，返回 2；实现 B 按 AC03 的"被拒绝"及 C04—C07 的惯例，返回 1。目录、符号链接、绝对路径同理。当 `--path /abs` 与 `main` 分支同时出现时，退出码还取决于未规定的检查顺序。
  - `identity --path old.md --at <旧提交>`，`old.md` 已从工作区删除（EG-S5 核对历史冻结时会遇到）。实现 A 按"同 C03：必须是普通文件"，以 2（或 1）拒绝，不输出提交中的身份；实现 B 输出 `blob`、`sha256`，`working_sha256: null`、`matches: false`，退出码 1。
  - 以下 JSON 形状未定：路径在该提交中不存在时，`blob`/`sha256` 是 `null` 还是省略；`--at` 无法解析时 `commit` 取什么值；identity 没有 `result`/`message` 字段，无法表达错误原因；checkpoint 退出码为 2 时输出什么（`result` 只有 `committed | refused | error` 三种值）；被拒绝时 `paths` 填什么（`status` 只有 `committed | unchanged`）。
  - `refused` 与 `error` 的分界：钩子拒绝与其他 git 失败从退出码上无法区分，实现 A 一律报 `error`，实现 B 解析 stderr 后报 `refused`。
  - identity 中 git 调用超时，退出码是 1 还是 2，没有规定。
- 后果：测试作者只要断言了具体退出码或字段值，就会与一半的合理实现冲突，引发测试异议（D-014）。EG-S5 依赖 identity 的失败输出时，也无法确定怎样解析。
- 最小修复：
  - 在 C03 中写明违反路径规则的退出码，并写明检查顺序（建议：参数与路径检查 → 分支 → 身份 → C06 → C07）；
  - 在 C13 中把普通文件规则限定为"存在时必须是普通文件"，不存在时按 `working_sha256: null` 处理；
  - 给 checkpoint 与 identity 各定义一份失败时的 JSON（可加 `result` 与 `message`，规定哪些字段为 `null`）；
  - 写明 `refused` 指前置条件拒绝（C04—C07、C03），`error` 指 git 执行失败、超时与锁冲突；
  - 补充对应的验收与 W。
  
  退出码属于公共 CLI；作者给出映射后，建议随决定包交用户确认。

### B1-05

- check: R4（兼 R2、R3）
- severity: MAJOR
- location: EG-S1-C05、EG-S1-AC05、§5 F-15
- spec 原文：C05"提交者身份取自 `git config user.name` 与 `git config user.email`；任一为空即拒绝……不以 `-c` 或环境变量补造身份（D-026 K4，F-15）"；§5"F-15｜未配置 user.name/email 时提交失败｜稳定通过"。
- 依据：K4"使用仓库已配置的 user.name 与 user.email，未配置即报错退出，不伪造身份"；D-012 要求每条事实带有能断言其陈述的探针。
- 反例（实测）：
  - **F-15 不成立。** 探针的命令是 `echo x > c.md; env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null HOME="$T" git commit -m c -- c.md`。`c.md` 是未跟踪文件，失败信息是 `error: pathspec 'c.md' did not match any file(s) known to git`，也就是 F-16，与身份无关。在同样的环境下改为提交已跟踪的文件，返回 0，提交作者是 `liuyangfan <liuyangfan@liuyangfandeMacBook-Pro.local>`（git 自动推断出的身份）；先 `add` 再 `commit --only` 也同样成功。本机钉住的 git 在未配置身份时**会**提交。这个探针以后每次重跑都会通过，起不到 D-012 的漂移检测作用。
  - 继承的环境变量：已配置 `user.name=cfg` 时，带 `GIT_AUTHOR_NAME=envname GIT_COMMITTER_NAME=envc …` 执行提交，结果为 `author=envname <env@x> committer=envc <envc@x>`。C05 只禁止命令自己**补造**身份，没有说是否清除继承来的 `GIT_AUTHOR_*`、`GIT_COMMITTER_*`、`EMAIL`。实现 A 原样透传，提交作者是 envname；实现 B 清除这些变量，提交作者是 cfg。两者都符合 C05 字面，产生的提交不同（作者不同，提交号也不同），而 K4 要求使用的是仓库已配置的身份。`author.name`、`committer.name` 配置项同理。
  - 漏列的错误实现：不检查配置、直接让 git 失败。在本机，这种实现会以自动推断的身份提交，被 AC05 抓住；在无法自动推断身份的主机上（如主机名没有域名的 CI 容器），git 报 "Please tell me who you are … user.email"，这种实现以退出码 1 结束，消息也"指出缺少的配置项"，于是通过 AC05，而它在其他机器上会伪造身份。AC05-W1 只列了"固定占位身份"，更常见的这种错误没有列出。
- 后果：严格档的现实核验对 C05 实际没有起作用；提交身份取决于调用环境，违背 K4"不伪造身份"。
- 最小修复：
  - 把 F-15 改为"未配置身份时 git 2.50.1 会自动推断身份并提交成功"，探针改用已跟踪的文件或先 `add`；
  - C05 写明：在任何 git 写操作之前检查两项配置；调用 git 时从子进程环境中去掉 `GIT_AUTHOR_*`、`GIT_COMMITTER_*`、`EMAIL`（或明确规定透传），这属于对 K4 的直接落实；
  - AC05 增加断言：没有产生提交、没有任何 git 写操作；另设一种环境，其中设置了 `GIT_AUTHOR_NAME`；
  - 增加 W："不检查配置，依赖 git 自身报错"。

### B1-06

- check: R5（兼 R1）
- severity: MAJOR — NEEDS_USER_DECISION
- location: §1 目标与非目标（整份 spec）
- spec 原文：§1 目标只有 `checkpoint` 与 `identity` 两条命令；C03 要求路径相对于仓库根目录，不得为绝对路径、不得含 `..`；identity 只读取提交中的内容。
- 依据：D-015 的最后一句"不在 git 中的外部大文件只记录 sha256 与不可变来源"，以及第一句"所有身份与清单由脚本生成和校验"。spec 地图把 D-015 整条只分给 EG-S1，EG-S1 的目标是"生成并校验所有身份字段"。机械检查只确认 D-015 被引用，所以看不出这一部分没有落实。
- 反例：某个项目有一份 2 GB 的数据集不入 git。按 D-015，它的身份应由脚本记录 sha256 与不可变来源。但没有任何 EG-S1 命令接受仓库外的路径或未跟踪的大文件，也没有任何其他 spec 认领这件事。结果是 LLM 只能自己计算或抄写 hash（违反 D-015），或者流程停在这里。
- 后果：一条已分配决定的一部分既没有落实、也没有交接，形成职责空档，以后必然要回来改 spec。
- 最小修复：由用户决定以下两者之一：
  - (a) EG-S1 增加外部文件身份命令（属公共 CLI，是实质选择）；
  - (b) 明确把这一部分推后，或交给某个 spec，登记为决定，并写入 EG-S1 非目标与 spec 地图。
  
  在没有当前使用者的情况下，(b) 更符合 R5 不预建能力的要求。

### B1-07

- check: R2
- severity: MINOR
- location: EG-S1-C01
- spec 原文："`scripts/eg.py` 在导入其他模块前关闭字节码写入，沿用 EG-S2-C20 的做法（D-024）"。
- 依据：D-024（F1—F8）不包含字节码相关内容。EG-S2-C20 把这一做法标为 `[AUTHOR-CHOICE:local]`。
- 后果：这项局部选择不会出现在冻结时交用户过目的 local 清单中（D-011）。
- 最小修复：这一句改标 `[AUTHOR-CHOICE:local]`，或改为说明"共用 EG-S2-C20 已实现的入口行为"，不引用 D-024。

### B1-08

- check: R1
- severity: MINOR
- location: EG-S1-C16
- spec 原文："已核验的 git 版本为 2.50.1，其他版本在实现开始前与审实现前按 D-012 重跑探针"。
- 依据：D-012 要求探针在写 spec 时、实现开始前、审实现前**各运行一次**，不论版本。
- 后果：这句话可被读成"版本相同就不必重跑"，从而缩小 D-012。AC16 只要求实现开始前重跑，覆盖不到审实现前这一次。
- 最小修复：改为"实现开始前与审实现前按 D-012 重跑探针；git 版本不是 2.50.1 时，探针结果须在运行记录中单列"。

### B1-09

- check: R4
- severity: MINOR
- location: EG-S1-C07、EG-S1-C08、EG-S1-C06
- spec 原文：C07"列出的路径全部与 HEAD 相同时，拒绝"；C08"`git commit --only … -- <有改动的路径>`"。
- 依据与反例（实测）：对一个已跟踪文件只做 `chmod +x`，按字节比较 sha256 时与 HEAD 相同，但 `git add` 之后 `git diff --cached` 显示 `mode change 100644 => 100755`，`commit --only` 成功提交。实现 A 按字节比较，判为全部无改动，拒绝；实现 B 按 git 的暂存视图比较，提交了一个只改模式的提交。HEAD 结果不同。clean/smudge 过滤器与换行转换也会造成反方向的分歧：字节不同而 git 认为无改动，此时把该路径单独传给 `commit --only` 会得到 "nothing to commit" 并以 1 退出。另外，在尚无提交的 `eg/` 分支上，`git rev-parse --verify HEAD` 失败，但 `commit --only` 可以产生首个提交；C06/C07 引用的"HEAD 中的内容"在这种情况下怎样处理，没有规定。
- 后果：属少见输入，不影响按常见方式写出的正确实现。
- 最小修复：定义"有改动"。例如：`add` 之后，`git diff --cached --quiet HEAD -- <路径>` 返回非零即为有改动（包含模式变化）。同时写明 HEAD 不存在时的处理方式（拒绝，或视为空树）。

### B1-10

- check: R3（兼 R6）
- severity: MINOR
- location: EG-S1-AC08、EG-S1-AC11、EG-S1-AC14
- spec 原文：AC14"用一个会睡眠的钩子与缩短的超时设置（测试可注入）运行"；AC08"用一个记录调用参数的 git 包装脚本运行"；AC11"人为在 `add` 之后终止进程（故障注入）"。
- 依据：D-013 要求测试作者在实现之前，只针对 spec 定义的对外接口写测试。
- 后果：
  - 缩短超时的方式（环境变量或参数）在 spec 中没有定义，测试作者只能自己发明，实现者再照着测试实现，于是这个接口由测试而不是 spec 决定。而且任何可调的超时都会改变 X2 写死的"300 秒"，若作为对外接口提供，须经用户确认。
  - AC08 与 AC11 的包装脚本要求 `git` 从 PATH 查找，spec 没有写明这一点。
  - 还漏了一个常见错误：在子目录中运行时，git 命令仍在当前目录执行，导致路径按当前目录解析，而 X5 要求相对于仓库根目录。
- 最小修复：
  - 在 C14 或 C16 中写明 `git` 从 PATH 解析；
  - 写明一个仅供测试使用的超时注入方式（交用户确认），或在 AC14 中接受使用真实的 300 秒；
  - 增加验收"在子目录中运行"，以及对应的 W。

### B1-11

- check: R4
- severity: MINOR
- location: EG-S1-C10、EG-S1-C03、EG-S1-C12
- spec 原文：C10"`--spec` 为可选的 spec ID"，"`--message` 为可选的一行摘要"。
- 反例：
  - `--message $'fix\n\nEG-Kind: candidate'` 会注入第二个 `EG-Kind` trailer。实现 A 拒绝（退出码 2），实现 B 原样写入，导致 `%(trailers:key=EG-Kind)` 读出两个值。
  - `--spec eg-s1`、`--spec ''` 是否要校验格式，没有规定。
  - `--path ./docs/a.md` 与 `--path docs/a.md` 重复给出时，输出中的 `path` 是原样回显还是规范化后的形式、是否去重，也没有规定。
- 后果：属边缘输入。
- 最小修复：
  - 摘要中含换行即为用法错误（退出码 2）；
  - `--spec` 须匹配 `EG-S\d+` 或 spec ID 的通用格式；
  - 路径先规范化再去重，输出规范化后的形式。

### B1-12

- check: R7
- severity: MINOR
- location: §4 影响登记
- 依据：spec 地图中 EG-S3 依赖 EG-S1，但影响登记没有列出 EG-S3。本 spec 的 F-11—F-16 与探针脚本采用临时格式，EG-S3 定义事实登记的正式格式后需要迁移这些内容。
- 后果：不影响任何已冻结的 spec。
- 最小修复：增加一行 EG-S3：F-11—F-16 与 `docs/specs/probes/` 在 EG-S3 落地后迁入正式事实登记；EG-S3 的探针运行记录用 `--kind record` 提交。

## 非阻塞备注

- F-14b 的不稳定：我用相同步骤（钩子中止后改用 `--no-verify` 提交）连续运行 60 次，0 次失败，未能复现。本 spec 不使用 `--no-verify`，不影响结论。
- D-018 规定身份字段只由脚本写。EG-S1 把写入时机交给 EG-S6，这没有问题；建议在影响登记的 EG-S6 一行写明"写入由脚本完成，不由 LLM 从输出中抄写"，以免 EG-S6 落到违反 D-015 的写法。
- §4"其字节已随 `f5f112a` 入库"是作者手写的提交号，在 D-015 落地前属于引导期的例外。EG-S1 实现后，建议改为引用脚本输出。
- C06 拒绝时的消息给出 `git reset -q -- <路径>`。如果拒绝的原因是用户自己暂存了一个不同的版本，照做会丢掉这个暂存版本。建议消息区分"疑似上次中断遗留"与"用户已暂存"两种情况。
- C12/C13 的"40 位十六进制"假定使用 SHA-1 对象格式；使用 `--object-format=sha256` 的仓库中，提交号是 64 位。
- 提交成功但输出前崩溃时，下次运行会因全部无改动而被拒绝，调用者拿不到提交号。这时仓库状态是确定的（提交已存在），不构成 R8 分歧；建议在拒绝消息中提示可用 identity 核对。
- K5 的命令摘要没有列出 `--spec`、`--message`。按本次审查的约定，这属于条款比决定更细，不计为问题。

## 裁定理由

有 1 条 BLOCKER（B1-01：并发锁策略未经用户决定，却写成依据 K3）和 5 条 MAJOR，按规则裁定 **FAIL**。

- B1-02、B1-03 已在临时仓库中实测：C11"恢复总能成功"的前提，在恢复命令拿不到锁时不成立；当前 spec 下，并发与超时两类故障后的暂存区与锁文件状态不确定。这正是严格档 R8 要防止的情况。
- B1-04 让测试作者无法确定非成功路径的退出码与 JSON。
- B1-05 显示 C05 引用的事实证据 F-15 在钉住的环境中不成立，并且身份来源存在分歧。
- B1-06 是 D-015 的一部分没有归属。

条款与 K1—K7、X1—X5 的对应总体忠实；R1 与 R7 没有阻塞问题。修复时，B1-01、B1-02/B1-03 的恢复策略以及 B1-06 须交用户决定。B1-04 的退出码映射属于公共 CLI，建议一并确认。
