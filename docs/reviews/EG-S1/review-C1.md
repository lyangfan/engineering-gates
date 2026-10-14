# EG-S1 Review C1

- reviewer: 独立会话（Claude Opus 5.5，Cursor 子代理；未参与写作与 B1，对 B1 的了解只来自 review-B1.md 与 ledger.md）
- date: 2026-10-14
- verdict: FAIL

C1-01 的修复涉及"并发 / 提交点"触碰面（C12 的提交校验规则不在 D-028 中），修复方案需交用户决定；C1-02 可由作者直接修正。剩余预算：C2。

## 输入核对

| 项 | 结果 |
|---|---|
| `git rev-parse --short HEAD` | `ffccdf5`（完整 `ffccdf561aca2ea62b6c086d0394d3b11cfb3f8f`），分支 `eg/v2` |
| `git status --short` | 空 |
| B1 受审 commit | `be59a0d` = `be59a0ded51f358ff2f65492a87b1646068f613e` |
| `git diff be59a0d ffccdf5 -- docs/reviews/EG-S1/checklist.md` | 无输出（检查表未变） |
| `docs/specs/EG-S2-trace.md` sha256 | `97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62`，与给定值一致 |
| 变化范围 | decisions.json、design-v2.md、dialogue.md、spec-map.md、ledger.md、review-B1.md、EG-S1-checkpoint.md、探针脚本与运行记录（9 个文件） |
| 探针 | `sh docs/specs/probes/EG-S1-git-probes.sh` 连续 3 次退出码 0，F-11—F-19 及对照全部 PASS；git 2.50.1 (Apple Git-155)，Python 3.13.5，macOS |

决定登记核对：D-028 `amends` D-027、D-027 `amended_by` D-028；D-029 `amends` D-015、D-015 `amended_by` D-029；spec 地图把 D-028 分给 EG-S1，D-029 记为"不进 spec"；设计稿 §3 引用 D-028、D-029。均一致。

全部实验在 `mktemp -d` 创建的临时仓库中进行；参考实现脚本放在项目目录之外，审查结束后已删除，关键脚本原文附在 C1-01 中。

## B1 finding 关闭核对

| B1 | 原严重度 | 结论 | 依据（用 v0.3 文本重试 B1 反例） |
|---|---|---|---|
| B1-01 | BLOCKER | 关闭 | C15 改为"仅锁冲突有界重试，最多 5 次，等待合计 ≤ 2 秒，不删锁"，与 D-028 Y1 原文一致。B1 的反例（IDE 后台 `git status` 短暂持锁）：实现 A"立即失败"现在违反 C15，并被 AC15-W3 区分；实现 B"有界重试"即规定行为。分歧消除。 |
| B1-02 | MAJOR | **未关闭** | 原反例一（锁出现在 `add` 与 `commit` 之间）已关闭：C11 规定恢复按 C15 重试，仍失败时 `error`、退出码 1、`message` 列出仍暂存的路径，不删锁；AC11 第三个场景可用 PATH 上的 git 包装脚本注入，预期状态确定。原反例二（真实并发）没有关闭：新 C12 的父提交校验使并发时第二个提交者几乎必然以退出码 1 结束，而它的提交已经产生；AC15 的不变量不覆盖这种状态，能否通过取决于 spec 未规定的 `message` 内容。实测 20/20 次出现，见 C1-01。 |
| B1-03 | MAJOR | 关闭 | C14 规定独立进程组、SIGTERM→10 秒→SIGKILL、残留锁不删除；F-19/F-19c 带对照通过。按 C14 写的参考实现用 AC14 的钩子（`sleep 6` 并另起后台子进程）实测 3 次：git 以 −15 退出，没有残留 `index.lock`，`git reset` 返回 0，暂存区恢复，HEAD 不变，钩子与其子进程都已不存在（子进程从未写出完成标记）。AC14-W2（`subprocess.run(timeout=)` 缺省 SIGKILL）与 F-19c 对应，能被区分。 |
| B1-04 | MAJOR | 关闭（余 MINOR C1-05） | 逐个重试：拼错路径 → C03 `refused`、退出码 1；绝对路径 + `main` → C02 规定先查路径，AC02 断言消息指向路径；identity 查询工作区已删除的文件 → C13 输出提交中的身份、`working_sha256: null`、`mismatch`、退出码 1（与 D-028 Y6 末句一致）；该 commit 中不存在 → `missing`，`blob`/`sha256` 为 `null`；`--at` 无法解析 → 退出码 2、`commit: null`；checkpoint 退出码 1/2 的 JSON 由 C17 规定；`refused`/`error` 分界由 C02、C11 规定；identity 中 git 超时按 C02 属 `error`、退出码 1。B1 列出的分歧均已消除。 |
| B1-05 | MAJOR | 关闭（余 MINOR C1-03、C1-04） | F-15 改用已跟踪文件并加对照；本机实测未配置身份时 git 以 `liuyangfan <liuyangfan@liuyangfandeMacBook-Pro.local>` 提交，与 F-15 v2 陈述一致。C05 要求命令自行检查配置，检查位于任何写操作之前（C02 顺序：身份先于 C06、C07 与提交）。`GIT_AUTHOR_*`、`GIT_COMMITTER_*` 存在即 `refused`（D-028 Y5），B1 的"透传 vs 清除"分歧消除；`EMAIL` 只在 `user.email` 未配置时生效，而 C05 已要求其非空，不再构成分歧。AC05-W2、W3 补齐。即使在 git 不能自动推断身份的主机上，W2 实现得到的是 git 执行失败（`error`），AC05 断言 `refused`，仍能区分。 |
| B1-06 | MAJOR | 关闭 | D-029 把外部大文件身份明确后置；EG-S1 §1 非目标、spec 地图 §2（"不进 spec"）、设计稿 §3 均已写明，满足 D-029 末句"EG-S1 的非目标与 spec 地图须写明"。 |
| B1-07 | MINOR | 关闭 | C01 改为"共用 EG-S2-C20 已规定的入口行为"并标 local。EG-S2-C20 原文确为在导入其他模块前设置 `sys.dont_write_bytecode = True`，且本身标为 local。该行为只影响是否产生 `__pycache__`，不涉及 CLI 合同、身份、提交点、恢复或外部副作用，确属局部。 |
| B1-08 | MINOR | 关闭 | C16 改为实现开始前与审实现前各重跑一次，版本不同则单列；AC16 要求两份运行记录。与 D-012 一致。 |
| B1-09 | MINOR | 关闭 | C07 定义"有改动"，包含可执行位，并以"`git add` 之后暂存条目与 HEAD 不同"为准；AC07 增加只改可执行位的用例与 W3。C04 规定尚无提交的分支 `refused`（local）。按 R2 判断：这是一条只拒绝、不写入的前置条件，退出码与 `result` 归类由 D-028 Y6（"仓库状态问题为 1 并记为 refused"）覆盖；它不改变身份格式、提交点或恢复语义，用户只需先做一次初始提交即可绕过。确属局部。clean/smudge 过滤器与换行转换的边角见备注。 |
| B1-10 | MINOR | 关闭 | C14 规定经 `PATH` 查找 git（AC08、AC11 的包装脚本因此可行），`EG_GIT_TIMEOUT_SECONDS` 有 D-028 Y3 依据；AC03 增加子目录运行与 W3。 |
| B1-11 | MINOR | 关闭 | C10 规定 `--message` 必须为非空单行、`--spec` 限定字符集，违者退出码 2；C03 要求路径采用规范形式、重复即拒绝（不做规范化，因而不存在回显哪种形式的问题）；AC10 增加含换行的 `--message` 与 W3。 |
| B1-12 | MINOR | 关闭 | §4 增加 EG-S3 一行。 |

## 变化范围审查（R1—R8）

| 项 | 结果 | 说明 |
|---|---|---|
| R1 | PASS（有 MINOR） | C02/C03/C10/C13/C17 ↔ D-028 Y6，C05 ↔ Y5，C11 ↔ Y2，C14 ↔ Y3，C15 ↔ Y1，非目标 ↔ D-029，逐条对照，没有冲突。C14 允许用环境变量把超时调到 300 秒以上，比 Y3"缩短"更宽（C1-06，MINOR）。 |
| R2 | FAIL | C12 的"唯一父提交必须是记录的 HEAD，否则 error"引用 D-028 Y2，但 Y2 只讲恢复重试、恢复失败输出与"并发验收以不变量断言"，不包含提交成功的判定规则。这条规则决定了并发时一次正确的提交被报告为失败，落在"并发 / 提交点"触碰面上（并入 C1-01）。C01、C04 的 local 标注确属局部（见上表 B1-07、B1-09）。F-15 v2 的陈述只断言了一半（C1-03，MINOR）。 |
| R3 | PASS | 新增的 W（AC02-W3、AC03-W3、AC05-W2/W3、AC07-W3、AC10-W3、AC11-W3、AC13-W3、AC14-W2、AC15-W3、AC17-W1/W2）都能被对应验收区分。 |
| R4 | PASS（有 MINOR） | identity 违反路径形式规则时的 `result` 未定（C1-05）；`author.name`/`committer.name` 配置会绕过 C05（C1-04）。均为少见输入。 |
| R5 | PASS | D-029 后置已写入非目标与地图；C17 的失败输出供 EG-S5 使用，已登记。 |
| R6 | PASS | C11↔C14↔C15↔C17、C12↔C17 的交叉引用与字段一致；C17 中 `commit` 在校验失败时取提交号，与 C12 一致。 |
| R7 | PASS | EG-S2 字节未变；EG-S3、EG-S5（含 C17）登记已补。 |
| R8 | FAIL | 崩溃（AC11）、超时（AC14）的故障注入可观察、可实现、预期状态确定，AC14 已实测稳定。AC12 的两个故障注入可以用 post-commit 钩子实现（实测在 `commit --only` 的 post-commit 钩子中再提交可行，钩子须自带防递归保护）。并发（AC15）有两处问题：第三个场景的不变量不能被符合 C12 的实现稳定满足（C1-01）；第一个场景的耗时上限按字面不能被用满 2 秒预算的正确实现满足（C1-02）。 |

## Findings

### C1-01

- check: R8（兼 R2）
- severity: MAJOR（修复需用户决定：属"并发 / 提交点"触碰面）
- scope: PRIOR_FINDING（B1-02 的并发部分未关闭；由新 C12 引起）
- location: EG-S1-C12、EG-S1-C17、EG-S1-AC15（第三个场景）
- spec 原文：
  - C08"提交步骤固定为：记录当前 HEAD；`git add -- <有改动的路径>`；`git commit --only …`"；
  - C12"提交后读取新的 HEAD，它的唯一父提交必须是 C08 记录的 HEAD……否则视为执行出错（`result: error`、退出码 1），已产生的提交不改写，`message` 给出该提交号"；
  - C17"`paths` 列出命令行给出的每个路径，`status` 取 `not_committed`"；
  - AC15"两个 checkpoint 进程并发提交不同路径，重复 20 次，每次都满足以下不变量：……退出码为 1 的进程，其路径要么已恢复，要么列在 `message` 中"。
- 依据：
  - 检查表 R8：并发故障后的仓库状态须明确规定且可被测试观察；MAJOR 定义包括"验收无法被正确实现稳定通过"。
  - C12 引用的 D-028 Y2 原文只包含"失败后的暂存区恢复按 Y1 有界重试，仍无法恢复时返回 error……并发验收以不变量断言"，不包含"父提交必须等于记录的 HEAD"这一提交成功判定规则（R2：引用的决定不包含条款的实质内容）。这条规则决定了并发下一次正确的提交被报告为失败，落在地图"并发 / 提交点 / 恢复｜是"一项上（D-011）。
- 反例（实测）：按 C08、C11、C12、C15 写的最小参考实现（下附），两个进程同时对 `p1.txt`、`p2.txt` 执行，重复 20 次：
  - 命令：`N=20 sh run.sh ck.py`（run.sh 在 `mktemp -d` 仓库中并发启动两个 `python3 -B ck.py pN.txt`，然后按 AC15 的不变量检查）。
  - 结果：**20/20** 次退出码为 (0,1) 或 (1,0)，两次都产生了提交（`new_commits=2`）。退出码为 1 的一方 `message` 为 `commit 414a8cf… failed verification (parent ['2fa5bd1…'], expected 8e04acc…)`：两个进程都在对方提交之前记录了同一个 HEAD，后提交的一方父提交是对方的提交，按 C12 判为 error。它的路径已经提交，提交内容正确（相对父提交只改了自己的路径），但暂存区并没有"恢复到执行前"，`message` 中按 C12 只要求给出提交号。20 次全部判为不变量违反：`invariant=VIOLATED(p2.txt: index!=pre, not in message)`。
  - 于是，实现 A 的 `message` 只给提交号（符合 C12 字面），在 AC15 上每次失败；实现 B 在 `message` 中顺带写出路径，每次通过。两个都符合 spec 的实现得到相反的通过/失败结论。测试作者把"已恢复"读成"暂存区与 HEAD 一致"时，两者又都通过。
  - 另一个后果：按 C17，这次已经提交的路径在输出中标为 `not_committed`，`blob`/`sha256` 为 `null`。EG-S5 按失败输出处理时会认为它没有提交；而下次对同一路径运行 checkpoint，又会因"全部无改动"被拒绝。
  - 参考实现 ck.py（重试等待 0.2/0.3/0.4/0.5/0.6 秒，合计 2 秒）：

    ```python
    import json, subprocess, sys, time
    WAITS = [0.2, 0.3, 0.4, 0.5, 0.6]
    def git(*a):
        for i in range(len(WAITS) + 1):
            p = subprocess.run(["git", *a], capture_output=True, text=True)
            if p.returncode != 0 and "index.lock" in p.stderr and "File exists" in p.stderr and i < len(WAITS):
                time.sleep(WAITS[i]); continue
            return p
    path = sys.argv[1]
    h0 = git("rev-parse", "HEAD").stdout.strip()          # C08: record HEAD
    added = False
    p = git("add", "--", path)
    if p.returncode == 0:
        added = True
        open(".msg-" + path, "w").write("eg(record): - x\n\nEG-Kind: record\nEG-Spec: -\n")
        p = git("commit", "-q", "--only", "-F", ".msg-" + path, "--", path)
        if p.returncode == 0:                              # C12
            h = git("rev-parse", "HEAD").stdout.strip()
            parents = git("rev-list", "--parents", "-n1", h).stdout.split()[1:]
            changed = git("diff-tree", "--no-commit-id", "--name-only", "-r", h).stdout.split()
            if parents == [h0] and changed == [path]:
                print(json.dumps({"result": "committed", "commit": h, "message": ""})); sys.exit(0)
            print(json.dumps({"result": "error", "commit": h, "message": "commit %s failed verification (parent %s, expected %s)" % (h, parents, h0)})); sys.exit(1)
    if added:                                              # C11
        r = git("reset", "-q", "--", path)
        if r.returncode != 0:
            print(json.dumps({"result": "error", "commit": None, "message": "still staged: %s; run git reset -q -- %s" % (path, path)})); sys.exit(1)
    print(json.dumps({"result": "error", "commit": None, "message": p.stderr.strip()[:80]})); sys.exit(1)
    ```

- 后果：严格档的并发验收仍不能被正确实现稳定通过，测试作者与实现者会在 AC15 上产生异议（D-014）；并且在正常的并发使用中，正确的提交会被报告为失败，下游（EG-S5）会得到与仓库不符的身份信息。
- 最小修复（需用户决定，二选一）：
  - (a) 保留 C12 的严格判定：在 C12/C17 中规定校验不通过时 `paths` 标为什么（例如 `committed_unverified`，并给出从该提交读回的 `blob`/`sha256`），`message` 必须列出这些路径；AC15 的不变量增加第三种允许的状态"路径已包含在输出 `commit` 所指的提交中，且该提交相对其父提交只改了本进程的路径"。
  - (b) 放宽 C12：新 HEAD 相对其父提交改动的路径恰好等于本次路径、提交信息与本次写入的一致，且 C08 记录的 HEAD 是其祖先时，视为成功；AC15 随之断言"每个进程退出码为 0，或者其路径已恢复且列在 message 中"。
  
  无论选哪一种，都应登记为 D-028 的补充决定，C12 再引用该决定。

### C1-02

- check: R8
- severity: MAJOR
- scope: CHANGED
- location: EG-S1-AC15（第一个场景）、EG-S1-C11
- spec 原文：
  - AC15"预先创建 `index.lock` 并保持，运行后退出码 1、`result: error`……总耗时不超过 2 秒加单次 git 调用时间"；
  - C15"最多 5 次，各次之间的等待合计不超过 2 秒"；
  - C11"对已执行过 `add` 的路径执行 `git reset -q -- <路径>`……恢复遇到锁冲突时按 C15 有界重试"。
- 依据：MAJOR 定义"验收无法被正确实现稳定通过"。C15 允许等待合计正好 2 秒，但一次 checkpoint 除了被重试的那次调用外，还要启动 Python 并执行若干次只读 git 调用（C03—C07 的检查、C08 记录 HEAD），这些时间不在"单次 git 调用时间"之内。
- 反例（实测）：用 C1-01 中的 ck.py（等待合计 2.0 秒，只多做一次 `rev-parse`，比真实实现的前置检查少得多），预先创建并保持 `index.lock` 后运行 3 次：总耗时 2.165、2.180、2.171 秒；同一仓库中单次 `git add` 失败耗时 0.013 秒，按字面计算的上限为 2.013 秒，**3 次全部超出**。把等待改成合计 1.5 秒的实现则能通过。两个都符合 C15 的实现，在 AC15 上一个必然失败、一个通过。
  - 另一处会拉开耗时的不确定性：锁从一开始就存在时，`git add` 本身失败。C11 的"已执行过 `add` 的路径"可以读成"执行了 `add`"（于是再对这些路径执行 `git reset`，又遇到锁，再重试最多 2 秒，总耗时约 4 秒，并在 `message` 中误报路径"仍处于已暂存状态"），也可以读成"`add` 成功的路径"（不执行 reset，约 2 秒）。两种读法得到的耗时与 `message` 不同。
- 后果：按字面写出的耗时断言会稳定判错一个正确实现；测试作者只能自己发明一个余量，造成测试异议（D-014）。
- 最小修复：
  - AC15 改为断言一个固定的、可直接测量的上限，例如"总耗时小于 4 秒"（明确包含进程启动与其他 git 调用），或改为"用 PATH 上的 git 包装脚本统计：对同一调用的尝试不超过 6 次，且相邻尝试的间隔合计不超过 2 秒"；
  - C11 写明"`add` 返回成功的路径"才需要恢复；`add` 本身失败时暂存区未被改动，不执行 reset。

### C1-03

- check: R2
- severity: MINOR
- scope: CHANGED
- location: §5 F-15、探针 F-15 段、EG-S1-C05、EG-S1-AC05-W2
- spec 原文：F-15"未配置 user.name/email 时，git 会以自动推断的身份提交已跟踪文件；`git config user.name` 为空｜通过（v2，带对照 F-15c）"；C05"（git 在未配置时会自动推断身份并提交，F-15）"。
- 依据：D-012 要求每条事实带有能断言其陈述的探针。探针只对 `git config user.name` 为空做 `check`，"会以自动推断的身份提交"一句只以 `F-15 INFO` 打印，不断言；F-15c 的对照（配置身份后提交成功）也不对应前半句。在不能自动推断身份的主机上，前半句不成立，而探针仍报 PASS。
- 后果：不影响正确实现（C05 要求无论 git 是否会自动推断，命令都自行检查）。只是 F-15 的前半句在漂移检测中不起作用，AC05-W2 的描述"git 以自动推断的身份提交成功"也只在部分主机上成立（在其他主机上 W2 得到的是 `error`，仍会被 AC05 的 `refused` 断言区分）。
- 最小修复：把 F-15 的陈述限定为可断言的部分（"未配置时 `git config user.name` 为空；在本机钉住环境下 git 会自动推断身份提交"），并把后半句改为 `check`，或在结果栏注明"前半句仅记录、不断言、依主机而定"。

### C1-04

- check: R4
- severity: MINOR
- scope: PRIOR_FINDING（B1-05 中"`author.name`、`committer.name` 配置项同理"一句未处理）
- location: EG-S1-C05
- spec 原文："提交者身份取自 `git config user.name` 与 `git config user.email`……不以 `-c` 或环境变量补造身份"。
- 反例（实测）：仓库配置 `user.name=cfg`、`user.email=cfg@x`，再配置 `author.name=other`、`committer.email=c@other`，执行 `git commit --only`，得到 `author=other <cfg@x> committer=cfg <c@other>`。实现 A 只检查 `user.*`，以 `other` 为作者提交；实现 B 发现 `author.*`/`committer.*` 后拒绝。由于 C05 禁止用 `-c` 覆盖，实现无法在不拒绝的前提下改用 `user.*`。
- 后果：这些配置项很少使用，不影响常见情况。
- 最小修复：C05 增加一句"`author.name`、`author.email`、`committer.name`、`committer.email` 任一已配置即同样拒绝"，或明确接受其覆盖。

### C1-05

- check: R4
- severity: MINOR
- scope: CHANGED
- location: EG-S1-C13
- spec 原文："路径的形式规则同 C03，但工作区中不要求存在；存在时必须是普通文件"；`result` 取值"`match`、`mismatch`、`missing`、`error`（命令写错或 git 执行出错）"。
- 依据：C02 与 D-028 Y6 把路径问题归为退出码 1、`refused`，但 identity 的 `result` 没有 `refused`，`error` 又定义为"命令写错或 git 执行出错"，两者都不对应路径规则违反。
- 反例：`identity --path /abs/a.md` 或 `--path docs`（目录）：实现 A 输出 `result: error`、退出码 1；实现 B 视为命令写错，退出码 2。AC13 没有覆盖这种情况。
- 后果：只影响 identity 的少见错误输入。
- 最小修复：C13 写明违反路径规则时 `result: error`、退出码 1（或给 identity 增加 `refused`），并补一条验收。

### C1-06

- check: R1
- severity: MINOR
- scope: CHANGED
- location: EG-S1-C14
- spec 原文："单次调用超时为 300 秒；环境变量 `EG_GIT_TIMEOUT_SECONDS` 为正整数时以它为准"。
- 依据：D-028 Y3"测试可用环境变量 EG_GIT_TIMEOUT_SECONDS 缩短超时，缺省 300 秒"；D-027 X2"单次超时 300 秒"。C14 也允许把超时调长（如 `3600`），比决定更宽。
- 反例：`EG_GIT_TIMEOUT_SECONDS=600`：实现 A 按 600 秒执行；实现 B 认为超出"缩短"的范围，按参数错误以 2 退出或截到 300。验收没有覆盖。
- 后果：不影响按缺省值运行的正确实现。
- 最小修复：C14 写明取值范围为 1—300，超出为参数错误（退出码 2）；或经用户确认允许调长。

## 非阻塞备注

- C15 以标准错误中的 `index.lock` 与 `File exists` 判断锁冲突。本机钉住的 Apple Git 在 `LC_ALL=zh_CN.UTF-8`、`de_DE`、`ja_JP` 下输出的都是英文，不构成分歧；在带 gettext 的 Linux git 与中文 locale 下，提示会被翻译，透传 locale 的实现将不再重试。建议在 C15 写明以 `LC_ALL=C` 调用 git，或在 D-012 的重跑中加一条锁提示文本的探针。
- C15"最多 5 次"可以读成 5 次重试（共 6 次尝试）或共 5 次尝试；AC15 的场景两种读法都能通过，建议写明。AC15"在第 2 次重试前移除锁"在时间上依赖实现的重试间隔，测试应使用 PATH 上的 git 包装脚本按调用次数移除锁，建议在验收中点明。
- C14"等待 10 秒仍未退出再发 SIGKILL"中的"仍未退出"指 git 进程还是整个进程组，没有写明。只有钩子忽略 SIGTERM 时才会产生差别（AC14 的钩子不会），属不现实输入。
- C11"钩子拒绝时为 `refused`"：git 2.50.1 在 pre-commit 钩子失败时退出码为 1 且自己不打印任何信息（实测），而 gpg 签名失败等致命错误退出码为 128。实现只能依据退出码或钩子是否存在来推断，"nothing to commit"等其他退出码为 1 的情形会被归为 `refused`。常见情况下不产生分歧。
- C02 的检查顺序没有写明"不在 git 仓库中"相对于路径形式检查的位置：在仓库外给出绝对路径时，先做纯语法检查的实现返回 1，先找仓库根目录的实现返回 2。属少见组合。
- C07 以"`git add` 之后暂存条目与 HEAD 不同"为准是对的，但前半句"工作区内容或可执行位不同"在 `core.fileMode=false` 或 `core.autocrlf=input` 下与后半句不等价（实测 `core.fileMode=false` 时只改可执行位，`add` 后暂存区没有变化）。建议把后半句明确为定义，前半句改为举例。
- C17 规定失败时 `spec` 未给出为 `null`；成功输出中未给出 `--spec` 时取 `"-"` 还是 `null`，C10 的"缺省记为 `-`"只明确指提交信息。建议写明。
- AC12 用 post-commit 钩子再做一次提交来注入"额外提交"可行（已实测），但钩子必须防止自身递归（内层提交会再次触发 post-commit）；首次实测时缺少保护导致无限递归。建议在验收中提示。

## 裁定理由

B1 的 12 条中 11 条已关闭；B1-02 的并发部分没有关闭。另有 2 条新的 MAJOR，按规则裁定 **FAIL**。

- C1-01：新 C12 的父提交校验没有决定依据（D-028 Y2 不包含这条规则），并且在实测中 20/20 次让并发的第二个进程在提交已经产生的情况下以退出码 1 结束；AC15 的不变量能否通过取决于 spec 没有规定的 `message` 内容。修复须由用户在两种提交判定语义中选择。
- C1-02：AC15 的耗时上限按字面不能被用满 C15 允许的 2 秒预算的正确实现满足（实测 3/3 超出）；C11"已执行过 add"的两种读法也会让耗时相差约一倍。属文字修正，不需要用户决定。

D-028、D-029 的落实总体忠实，B1-01、B1-03、B1-04、B1-05、B1-06 这几条阻塞项的原反例在 v0.3 下都已消除（B1-03 在临时仓库中实测）。C01、C04 的 local 标注确属局部。其余为 MINOR 与备注，不阻塞。
