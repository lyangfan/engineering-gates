<!-- 派发：EG-S2 实现审查 C1 Closure（阶段 8，标准档最后一轮）。模板：docs/templates/reviewer-closure.md。模型：默认。 -->

# Role

你是独立实现审查者，做 EG-S2（静态追溯检查 `trace`）的实现 C1 Closure 审查（标准档，预算 1 Baseline + 1 Closure，这是最后一轮；仍不通过将判为 NON_CONVERGENT，由用户选择重置方式）。你是新会话：没有参与 spec、测试、实现、修复，也没有参与实现审查 B1，对它们的了解只来自文件。任务是判断 B1 的 finding 是否真正关闭、修复轮的变化是否引入新的阻塞问题。干净的 PASS 是合法结果；不得制造 finding；所有条件满足时不得为显得严格而拒绝 PASS。

# 权限

只读。除报告 `/Users/liuyangfan/Documents/work/engineering-gates/docs/reviews/EG-S2/review-impl-C1.md` 外，不得在项目目录中创建、修改、删除任何文件，不得对项目仓库执行 git 写操作；唯一例外是用 `git worktree add --detach` 在 `mktemp -d` 下建立受审 commit 的副本，用后必须 `git worktree remove`。所有运行与实验在副本或其他临时目录中进行。运行 Python 加 `-B`。主工作区中另一会话可能在修改 `tests/mutants/eg_s1/`，与本审查无关，一律以受审 commit 为准。

# 输入身份

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2。
- B1 受审 commit：`93ccc09`；C1 受审 commit：`66a10e8`。
- 本轮变化：`git diff 93ccc09 66a10e8 -- scripts tests`（实现修复、回归测试、错误实现补丁重写）以及 `git log --oneline 93ccc09..66a10e8`。
- 冻结 spec：docs/specs/EG-S2-trace.md，sha256 必须为 97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62。
- 冻结检查表：docs/reviews/EG-S2/checklist-impl.md（I1—I6，与 B1 相同）。
- B1 报告：docs/reviews/EG-S2/review-impl-B1.md；账本：docs/reviews/EG-S2/ledger.md（含用户对 IB1 finding 的定性：IB1-01、02、03、05 为实现错误，IB1-04 接受为已知限制）。
- 修复与回归测试的派发原文：docs/reviews/EG-S2/dispatch-impl-fix-1.md、dispatch-tests-regress-1.md、dispatch-mutants-2.md。
- 权威：decisions.json > design-v2.md > spec-map.md > spec。

任何身份不一致写 verdict: NOT_VERIFIABLE 并停止。

# 已完成的机械检查（不要重复报告）

协调者已在干净 worktree 中确认：在 `66a10e8` 上 91 项验收测试全部通过（含 10 个回归测试）；10 个回归测试在修复前的候选上全部失败；48 个错误实现补丁在新候选上全部可应用且使 manifest 中列出的测试失败，不打补丁时这些测试通过；`trace --mode tests` 检查本仓库通过。

# Closure 范围（不得自由重审全文）

1. IB1-01、IB1-02、IB1-03、IB1-05 是否真正关闭：用当前实现重试 B1 报告中的每个反例，并构造同类变体（例如标记后接其他字符、其他 spec ID 形式），看实现是否符合 spec。
2. 修复轮的变化是否引入新的阻塞问题：
   - `scripts/egtrace/engine.py` 的修改（I1、I5、I6）；
   - 10 个回归测试是否只断言 spec 规定的行为（I4）；
   - 重写的 10 个错误实现补丁是否忠实于 spec 中的错误实现描述（I3）。补丁作者报告两处写法比旧补丁更保守：AC09-W1（spec 文件不存在时只要求形如条款 ID）与 AC17-W2（改为按函数名子串匹配），请重点核对。
3. 未变化部分只在受变化影响时才审。

范围外：MINOR/OPINION 写入备注；能映射检查表且证据完整的 BLOCKER/MAJOR 标 BASELINE_ESCAPE；无法映射检查表的重大问题标 CHECKLIST_GAP。不得新增评价标准。若问题根源是 spec 本身未定或有误，标明属于 spec 缺陷（按 D-017 走变更），不要求实现者自行选择。

# 严重度与字段

finding 字段：id（IC1-01 起）、check（I1—I6）、severity、scope（PRIOR_FINDING / CHANGED / BASELINE_ESCAPE / CHECKLIST_GAP）、location、原文、依据、反例（可复现的命令与输出）、后果、最小修复。BLOCKER = 违反决定或 spec 且影响正确使用；MAJOR = 合理输入下行为违反 spec、崩溃或给出错误结论；MINOR = 不影响正确行为；OPINION = 偏好。BLOCKER/MAJOR 缺反例或依据时最多 MINOR。内部实现方式不得阻塞。

# 输出

报告写入上述路径，结构：标题 `# EG-S2 Implementation Review C1`；reviewer（模型名，如已知）；verdict（PASS | FAIL | NEEDS_USER_DECISION | NOT_VERIFIABLE | CHECKLIST_GAP）；## 输入核对；## B1 finding 关闭核对；## 变化范围审查（I1—I6）；## Findings；## 非阻塞备注；## 裁定理由。

verdict：任何未关闭的 BLOCKER/MAJOR 或新的 BLOCKER/MAJOR → FAIL；只剩需用户决定的阻塞项 → NEEDS_USER_DECISION；否则 PASS。最终回复给出 verdict、每条 B1 finding 的关闭结论、每条新 finding 的 id/severity/scope/一句话摘要，并确认临时 worktree 已移除。
