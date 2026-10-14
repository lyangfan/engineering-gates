# EG-S1 审查账本

> 协调者维护；审查报告不可变，本账本是其动态投影（D-016）。预算：严格档 1 Baseline + 2 Closure。

## 轮次

| 轮次 | 报告 | sha256 | 受审 commit | 裁定 |
|---|---|---|---|---|
| B1 | review-B1.md | 69556890c4887ed11cf6ab941f277c341d03eca180cb2285bbb98680f2a4dcdd | be59a0d | FAIL（1 BLOCKER、5 MAJOR、6 MINOR） |

| C1 | review-C1.md | 64c963a5320928f5d1db65ca34724778660df33a80aee63cb652822c778d7be4 | ffccdf5 | FAIL（2 MAJOR、4 MINOR；B1 关闭 11/12） |

| C2 | review-C2.md | 51084a983922b9deec60ad817bacd9d1d61355c63c678691b2166ef6f9612f72 | 3955513 | PASS（1 MINOR） |

预算 B1 + C1 + C2 已用完。

**状态：FROZEN（2026-10-14）**，冻结字节为 commit `3955513` 中的 `docs/specs/EG-S1-checkpoint.md`（sha256 `55c44f27fe9f83f0c3d474f7cc42f37d5aaf4dfdf16829515e67d4f3bf2e9682`），冻结记录见 `freeze.json`。冻结后的变更按 D-017 处理。局部选择 C01、C04 已经用户过目认可（2026-10-14，D-011）。

## Findings

| ID | 严重度 | 检查项 | 摘要 | 处置 | 状态 |
|---|---|---|---|---|---|
| B1-01 | BLOCKER | R2 | C15"不重试"是并发选择，却引用只讲钩子的 K3 | D-028 Y1 → C15 有界重试 | VERIFIED_CLOSED（C1） |
| B1-02 | MAJOR | R8 | 恢复命令 `git reset` 同样需要锁，并发下恢复可能失败；AC15 不可保证 | D-028 Y2 → C11 恢复与恢复失败输出；C12 提交号校验；AC15 改为不变量 | VERIFIED_CLOSED（C2） |
| B1-03 | MAJOR | R8 | 超时终止方式未定；SIGKILL 会残留锁，钩子子进程存活 | D-028 Y3 → C14 进程组 SIGTERM→SIGKILL、环境变量缩短超时；F-19 探针 | VERIFIED_CLOSED（C1） |
| B1-04 | MAJOR | R4/R6 | 非成功输出未定义：路径错误退出码、refused/error 分界、失败 JSON、identity 对已删除文件 | D-028 Y6 → C02 退出码与检查顺序、C03、C13、新 C17 | VERIFIED_CLOSED（C1） |
| B1-05 | MAJOR | R4/R2/R3 | F-15 为假：未配置身份时 git 会自动推断身份提交；GIT_AUTHOR_* 环境变量会覆盖身份 | F-15 v2 带对照；C05 自行检查配置 + D-028 Y5 拒绝身份环境变量；AC05-W2/W3；F-18 探针 | VERIFIED_CLOSED（C1） |
| B1-06 | MAJOR | R5 | D-015 外部大文件身份无条款、无归属 | D-029 后置，写入非目标与地图 | VERIFIED_CLOSED（C1） |
| B1-07 | MINOR | R2 | C01 字节码一句引用 D-024 不成立，应标 local | C01 改标 local | VERIFIED_CLOSED（C1） |
| B1-08 | MINOR | R1 | C16 可被读成只在版本不同时重跑探针，缩小 D-012 | C16 按 D-012 两次重跑，版本不同单列 | VERIFIED_CLOSED（C1） |
| B1-09 | MINOR | R4 | 何为"有改动"未定义（仅 chmod、无提交的分支） | C07 定义"有改动"含可执行位；C04 无提交分支拒绝（local） | VERIFIED_CLOSED（C1） |
| B1-10 | MINOR | R3/R6 | AC14 缩短超时的方式未定；git 经 PATH 查找；子目录运行未测 | C14 环境变量缩短超时、经 PATH 查找 git；AC03 子目录运行 | VERIFIED_CLOSED（C1） |
| B1-11 | MINOR | R4 | `--message` 换行可注入 trailer；`--spec` 未校验；路径规范化与重复未定 | C10 校验 --message 单行与 --spec 字符集；C03 规范路径与重复 | VERIFIED_CLOSED（C1） |
| B1-12 | MINOR | R7 | 影响登记漏 EG-S3 | 影响登记加 EG-S3 | VERIFIED_CLOSED（C1） |

| C1-01 | MAJOR | R8/R2 | C12 要求新提交的父提交等于记录的 HEAD，并发时正确的提交被判失败（20/20）；且 Y2 不含此规则 | D-030 Z1 → C10 EG-Run trailer、C12 按运行标识找提交；AC12、AC15 更新；F-21 | VERIFIED_CLOSED（C2） |
| C1-02 | MAJOR | R3/R8 | AC15 时间上限过紧，用满 2 秒重试预算的正确实现失败（3/3）；C11 恢复是否另计预算有歧义 | AC15 上限改为 6 秒并说明预算；C11、C15 写明恢复另有一份预算 | VERIFIED_CLOSED（C2） |
| C1-03 | MINOR | R3 | F-15 探针只断言 config 为空，"会自动推断身份提交"只打印未断言 | F-15a 改为断言 | VERIFIED_CLOSED（C2） |
| C1-04 | MINOR | R4 | `author.*`、`committer.*` 配置仍会覆盖 `user.*` | D-030 Z2 → C05 拒绝 author.*/committer.* 配置；AC05-W4；F-20 | VERIFIED_CLOSED（C2） |
| C1-05 | MINOR | R4 | identity 违反路径规则时的 result 与退出码未定 | C13 规定路径违规时为 error、退出码 1；AC13 | VERIFIED_CLOSED（C2） |
| C1-06 | MINOR | R1 | `EG_GIT_TIMEOUT_SECONDS` 可调高到 300 秒以上，Y3 只允许测试缩短 | C14 限定 1—300；AC14 | VERIFIED_CLOSED（C2） |

| C2-01 | MINOR | R4 | C11"若 add 已执行"在 add 本身失败时有两种读法，只影响 message 文字 | 接受为已知限制，编辑性修订时改为"add 已返回成功"（D-017 编辑性） | ACCEPTED_LIMITATION |

## 阶段 6：测试冻结

- 独立测试作者交付 69 个测试，覆盖 AC01—AC17 与全部 44 个错误实现；实现前全部失败（0 报错、0 skip）。协调者另以立即退出的空桩运行：69 个测试耗时约 37 秒、114 处断言失败、无测试自身报错，确认夹具被实际执行、失败原因是实现缺失而非测试错误（RC-09）。
- 测试冻结于 `63fd6f1`（`EG-Kind: tests-freeze`）。实现开始前探针全部通过（见探针运行记录）。
- 测试作者 NOTES 中需实现者知悉的点：
  - `probe_log_records_run_before_implementation_review` 在阶段 8 之前必然失败：该记录由协调者在派发审查前写入，实现者不得为通过它而编辑探针记录；
  - C11 要求钩子拒绝时为 `refused`，但 git 对 pre-commit 失败只返回 1，spec 未规定识别方法；若实现者无法可靠满足 AC11，按 D-014 提测试异议，不得自行改测试；
  - 其余读法见 `tests/acceptance/eg_s1/NOTES.md`。

## 阶段 7：实现

- 实现者（按用户会话指示为 Grok 4.7，派发原文 `dispatch-impl-1.md`）交付；协调者复核：写入范围合规（`eg.py` 只增加两个分发项，`egtrace/` 与 0.1.0 未改动），无测试特判，无 `__pycache__`、无残留进程；EG-S2 与 0.1.0 测试全部通过；EG-S1 69 项中 67 项通过，失败的 2 项均为 AC16"审实现前探针记录"（及在 venv 中重跑整套时的同一项），按预期待阶段 8 前补记后通过。候选实现提交见下一个 candidate 提交。
- 协调者错误：此前在探针记录中预先写了"审实现前"标题与"待补记"正文，使 AC16 该项在实现阶段错误地通过（只检查标题存在，RC-09 同类）。已删除占位标题。
- 交阶段 8 重点核对：`git commit` 额外使用 `--cleanup=verbatim`（C08 规定的提交命令是固定写法）；钩子拒绝的识别以 `GIT_TRACE2_EVENT` 的 hook 退出码为主、以"存在可执行钩子"为兜底；`eg.py` 启动即导入 `egcheckpoint`，`trace` 因而依赖其可导入；"最多 5 次"按含首次共 5 次调用实现。

### 补丁检查与测试修正

- 补丁检查（派发 `dispatch-mutants-1.md`）：44 个错误实现补丁全部被杀死；协调者在 `cc6cada` 的干净 worktree 中独立重跑，结论一致（44/44）。
- 补丁作者另报：AC01 的 `__pycache__` 断言在 macOS 系统 Python 上看不到字节码写入（`sys.pycache_prefix` 指向被测试改写的 `HOME` 下）；AC14 超时测试在 venv 内运行时出现过一次"hook did not start"。
- 测试修正（派发 `dispatch-tests-fix-1.md`）：AC01 改以 `-X pycache_prefix=` 运行并加前置检查；AC14 不稳定的原因是 macOS 首次执行新写入的脚本有约 0.4—1 秒延迟（测试时序问题，非实现问题），改为安装钩子后先预热执行一次，断言不变。协调者复核：AC01 能杀死"去掉字节码开关"的变体；AC14 连续 5 次通过；AC01-W1、AC14-W1、AC14-W2 仍被杀死。测试重新冻结于 `e440b8b`。
- 审实现前探针（D-012）：实际运行后写入记录（`6ced659`），全部通过；AC16 两项随之通过，69 项全部通过。

### 补丁作者指出的错误实现描述不清处（冻结后编辑性修订候选，D-017）

AC09-W1"不带 `--only` 的 `git commit`"在给出路径时等同于 `--only`，应写作"不带路径的 `git commit`"；AC10-W4"可预测的运行标识（如时间戳）"中按秒的时间戳可能在相邻两次运行间不同；AC10-W3 在本实现的消息结构下伪造行可能不会成为 trailer；AC12-W2 未说明是否保留改动路径核对；AC16-W1 把"3.10+ 语法"与"3.10+ 标准库参数"两种错误合在一条，编译测试只能抓前者；AC09-W1、AC10-W1 的补丁先被 C12 自身的校验拦下。

## 阶段 8：实现审查

预算：严格档 1 Baseline + 2 Closure。检查表 `checklist-impl.md`（I1—I8）冻结于 `0d57ac5`；受审 commit `0d57ac5`（`eg.py` 与 `egcheckpoint/` 同候选 `d499fe4`）；派发 `dispatch-impl-review-B1.md`。

## 冻结后待办（编辑性，不改 EG-S1 冻结字节）

- C11：改为"若 C08 的 `add` 已返回成功"（C2-01）。
- C12：引用列表去掉不再需要的 D-028 Y2（C2 备注）。
- AC12-W3：写明用 PATH 上的 git 包装脚本在提交前插入一个提交来注入（C2 备注）。
- spec 头部状态行仍写"草稿 v0.4…未冻结"，与冻结状态不一致（测试作者 NOTES）；冻结状态以本账本与 `freeze.json` 为准。
- identity 的路径违规记为 `error` 而 D-028 Y6 用词为 `refused`：审查者判为不冲突（Y6 的用词针对 checkpoint 结果）；如用户认为 Y6 也约束 identity，再行处理。

## 复盘候选

- RC-09：F-15 探针因错误的原因通过（用未跟踪文件测身份，失败实为 F-16 所致）。探针与测试一样需要对照，证明它是因为所声称的原因通过或失败。
- RC-10：C12 的父提交规则再次写成"依据 D-028 Y2"而 Y2 不含它（RC-03 复发）。修订时新加的规则同样要过 D-011 分流，不能挂在最近的决定上。
- RC-11：AC12 初稿描述的 post-commit 钩子场景会无限递归（实测产生 1153 个提交）；协调者在派发前自行验证验收场景可构造，避免在最后一轮被判为不可实现。
- RC-16：协调者在探针记录中预写占位标题，使检查"记录存在"的测试错误通过；过程证据只能在事件发生后写入，不能预先占位。
