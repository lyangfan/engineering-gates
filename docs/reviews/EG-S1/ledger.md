# EG-S1 审查账本

> 协调者维护；审查报告不可变，本账本是其动态投影（D-016）。预算：严格档 1 Baseline + 2 Closure。

## 轮次

| 轮次 | 报告 | sha256 | 受审 commit | 裁定 |
|---|---|---|---|---|
| B1 | review-B1.md | 69556890c4887ed11cf6ab941f277c341d03eca180cb2285bbb98680f2a4dcdd | be59a0d | FAIL（1 BLOCKER、5 MAJOR、6 MINOR） |

| C1 | review-C1.md | 64c963a5320928f5d1db65ca34724778660df33a80aee63cb652822c778d7be4 | ffccdf5 | FAIL（2 MAJOR、4 MINOR；B1 关闭 11/12） |

剩余预算：C2（最后一轮；仍不通过即 NON_CONVERGENT，由用户选择重置方式，D-016）。

## Findings

| ID | 严重度 | 检查项 | 摘要 | 处置 | 状态 |
|---|---|---|---|---|---|
| B1-01 | BLOCKER | R2 | C15"不重试"是并发选择，却引用只讲钩子的 K3 | D-028 Y1 → C15 有界重试 | VERIFIED_CLOSED（C1） |
| B1-02 | MAJOR | R8 | 恢复命令 `git reset` 同样需要锁，并发下恢复可能失败；AC15 不可保证 | D-028 Y2 → C11 恢复与恢复失败输出；C12 提交号校验；AC15 改为不变量 | OPEN（C1：并发部分未关闭，见 C1-01） |
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

| C1-01 | MAJOR | R8/R2 | C12 要求新提交的父提交等于记录的 HEAD，并发时正确的提交被判失败（20/20）；且 Y2 不含此规则 | 交用户决定（Z1） | USER_DECISION_PENDING |
| C1-02 | MAJOR | R3/R8 | AC15 时间上限过紧，用满 2 秒重试预算的正确实现失败（3/3）；C11 恢复是否另计预算有歧义 | 修复 | OPEN |
| C1-03 | MINOR | R3 | F-15 探针只断言 config 为空，"会自动推断身份提交"只打印未断言 | 修复 | OPEN |
| C1-04 | MINOR | R4 | `author.*`、`committer.*` 配置仍会覆盖 `user.*` | 交用户决定（Z2） | USER_DECISION_PENDING |
| C1-05 | MINOR | R4 | identity 违反路径规则时的 result 与退出码未定 | 修复 | OPEN |
| C1-06 | MINOR | R1 | `EG_GIT_TIMEOUT_SECONDS` 可调高到 300 秒以上，Y3 只允许测试缩短 | 修复 | OPEN |

## 复盘候选

- RC-09：F-15 探针因错误的原因通过（用未跟踪文件测身份，失败实为 F-16 所致）。探针与测试一样需要对照，证明它是因为所声称的原因通过或失败。
- RC-10：C12 的父提交规则再次写成"依据 D-028 Y2"而 Y2 不含它（RC-03 复发）。修订时新加的规则同样要过 D-011 分流，不能挂在最近的决定上。
