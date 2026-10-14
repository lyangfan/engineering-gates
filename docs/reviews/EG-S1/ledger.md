# EG-S1 审查账本

> 协调者维护；审查报告不可变，本账本是其动态投影（D-016）。预算：严格档 1 Baseline + 2 Closure。

## 轮次

| 轮次 | 报告 | sha256 | 受审 commit | 裁定 |
|---|---|---|---|---|
| B1 | review-B1.md | 69556890c4887ed11cf6ab941f277c341d03eca180cb2285bbb98680f2a4dcdd | be59a0d | FAIL（1 BLOCKER、5 MAJOR、6 MINOR） |

剩余预算：C1、C2。

## Findings

| ID | 严重度 | 检查项 | 摘要 | 处置 | 状态 |
|---|---|---|---|---|---|
| B1-01 | BLOCKER | R2 | C15"不重试"是并发选择，却引用只讲钩子的 K3 | D-028 Y1 → C15 有界重试 | FIX_PROPOSED |
| B1-02 | MAJOR | R8 | 恢复命令 `git reset` 同样需要锁，并发下恢复可能失败；AC15 不可保证 | D-028 Y2 → C11 恢复与恢复失败输出；C12 提交号校验；AC15 改为不变量 | FIX_PROPOSED |
| B1-03 | MAJOR | R8 | 超时终止方式未定；SIGKILL 会残留锁，钩子子进程存活 | D-028 Y3 → C14 进程组 SIGTERM→SIGKILL、环境变量缩短超时；F-19 探针 | FIX_PROPOSED |
| B1-04 | MAJOR | R4/R6 | 非成功输出未定义：路径错误退出码、refused/error 分界、失败 JSON、identity 对已删除文件 | D-028 Y6 → C02 退出码与检查顺序、C03、C13、新 C17 | FIX_PROPOSED |
| B1-05 | MAJOR | R4/R2/R3 | F-15 为假：未配置身份时 git 会自动推断身份提交；GIT_AUTHOR_* 环境变量会覆盖身份 | F-15 v2 带对照；C05 自行检查配置 + D-028 Y5 拒绝身份环境变量；AC05-W2/W3；F-18 探针 | FIX_PROPOSED |
| B1-06 | MAJOR | R5 | D-015 外部大文件身份无条款、无归属 | D-029 后置，写入非目标与地图 | FIX_PROPOSED |
| B1-07 | MINOR | R2 | C01 字节码一句引用 D-024 不成立，应标 local | C01 改标 local | FIX_PROPOSED |
| B1-08 | MINOR | R1 | C16 可被读成只在版本不同时重跑探针，缩小 D-012 | C16 按 D-012 两次重跑，版本不同单列 | FIX_PROPOSED |
| B1-09 | MINOR | R4 | 何为"有改动"未定义（仅 chmod、无提交的分支） | C07 定义"有改动"含可执行位；C04 无提交分支拒绝（local） | FIX_PROPOSED |
| B1-10 | MINOR | R3/R6 | AC14 缩短超时的方式未定；git 经 PATH 查找；子目录运行未测 | C14 环境变量缩短超时、经 PATH 查找 git；AC03 子目录运行 | FIX_PROPOSED |
| B1-11 | MINOR | R4 | `--message` 换行可注入 trailer；`--spec` 未校验；路径规范化与重复未定 | C10 校验 --message 单行与 --spec 字符集；C03 规范路径与重复 | FIX_PROPOSED |
| B1-12 | MINOR | R7 | 影响登记漏 EG-S3 | 影响登记加 EG-S3 | FIX_PROPOSED |

## 复盘候选

- RC-09：F-15 探针因错误的原因通过（用未跟踪文件测身份，失败实为 F-16 所致）。探针与测试一样需要对照，证明它是因为所声称的原因通过或失败。
