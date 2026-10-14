<!-- 派发：EG-S2 实现者修复实现审查 C1 的 finding（第 2 周期，用户选择范围受限的新 Baseline）。模板：docs/templates/implementer.md 的修复变体。模型：按用户会话指示为 Grok 4.7，最高思考档，非 Fast。 -->

# Role

你是 EG-S2（静态追溯检查 `trace`）的实现者，处于修复轮。实现审查 C1 发现上一轮修复引入了一条回归。你的目标是修复下列问题，使实现满足冻结 spec，不改变其他行为。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `9b795a0`（其中 `scripts/egtrace/` 为候选 `22ea31a`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（sha256 97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62）。
- 审查报告：docs/reviews/EG-S2/review-impl-C1.md（IC1-01、IC1-02 有原文、依据、可复现反例与最小修复）。
- 冻结验收测试：tests/acceptance/eg_s2/（只读）。另一位测试作者正并行编写回归测试并调整 IC1-03 所指的那条测试，你看不到其产出。

# 要修复的 finding

- IC1-01（MAJOR，实现错误）：覆盖声明 `覆盖 <条款 ID>[、<条款 ID>…]：` 到第一个 `：` 结束（C14）。当前 `COVERAGE_RE` 的 ID 字符类包含全角冒号，会越过第一个 `：`。修复后，审查报告中的 CASE 1、CASE 2 及其对照都必须符合 C14、C15。若你认为 spec ID 含 `：` 时须特殊处理，按报告建议在 spec ID 可用性检查中拒绝，并在最终回复中说明。
- IC1-02（MINOR，实现错误）：C07"在决定分配表中出现了多次"分支的失败项中，`path` 与 `line` 必须指向同一文件中的同一位置（C19）。
- 不得改动其他行为；IB1-01、IB1-02、IB1-03、IB1-05 已关闭，修复不得使其回退。

# 工作方式与写入范围

- 在 `mktemp -d` 下用 `git worktree add --detach <目录> 9b795a0` 建立副本，所有修改与运行在副本中进行。主工作区与另一个临时 worktree 中有其他会话在工作，不要触碰。
- 在副本中只修改 `scripts/egtrace/` 下的文件。
- 完成后在副本中执行 `git diff -- scripts/egtrace > <主工作区>/docs/reviews/EG-S2/impl-fix-2.patch`，然后 `git worktree remove`。不得对主工作区做其他写入，不得提交。认为冻结测试与 spec 冲突时写入主工作区新文件 `docs/reviews/EG-S2/disputes.md`（D-014）。

# 实现要求

只用 Python 3.9 标准库；不使用 3.10 以上语法；不针对测试写特判；不 import science-gates。

# 自验（在副本中）

- 用 C1 报告中 IC1-01 的 CASE 1、CASE 2 与对照、IC1-02 的反例复现：修复前出现问题，修复后符合 spec。
- 用 B1 报告中 IB1-01、IB1-02、IB1-03、IB1-05 的反例复核没有回退。
- `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t .` 全部通过；`/usr/bin/python3 -B scripts/eg.py trace --mode tests` 通过；副本中不出现 `__pycache__`。

# 最终回复

给出：补丁文件路径与改动摘要；每个反例修复前后的实际结果；验收测试结果；提出的测试异议（如有）。只报告实际运行过的结果。
