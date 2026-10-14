<!-- 派发：EG-S2 错误实现补丁重写（第 2 周期修复后 1 个补丁无法应用）。模板：参照 dispatch-mutants-2.md。模型：默认（补丁作者）。 -->

# Role

你是 EG-S2 的独立测试作者（D-013 补丁作者）。候选实现在第 2 周期再次修复，`scripts/egtrace/engine.py` 改动后，错误实现补丁 EG-S2-AC07-W1 已无法应用到新候选。你要在新候选上重写这一个补丁，使其仍忠实于 spec 中的错误实现描述，并证明冻结测试能杀死它。你没有参与实现与修复。

# 输入

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `ae4371c`（新候选实现 `1aff70f`；测试最新冻结 `97aabf1`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（AC07-W1 的描述在 §3：把"全局约束"或"不进 spec"当作未分配而误报）。
- 现有补丁与清单：tests/mutants/eg_s2/（其余 47 个协调者已在新候选上验证可应用且被杀死，不要修改）。
- 不要阅读 docs/reviews/ 下除本派发文件外的任何文件。

# 工作方式与写入范围

- 用 `git worktree add --detach <临时目录> ae4371c` 在 `mktemp -d` 下建立副本，实验只在副本中进行，完成后 `git worktree remove`。主工作区与其他 worktree 中有其他会话在工作，不要触碰。
- 只能覆盖写 tests/mutants/eg_s2/EG-S2-AC07-W1.patch，并相应更新 manifest.json 中这一项；补丁为相对于 `ae4371c` 的 unified diff，只改 `scripts/` 下实现文件。不得修改其他文件，不得提交。无法以忠实方式表达或无法被杀死的，写入 SURVIVORS.md 并说明。

# 自验

在副本中：`git apply --check` 通过；不打补丁时 `killing_tests` 通过；打补丁后这些测试失败。运行用 `/usr/bin/python3 -B -m unittest <测试 ID>…`。项目中不留 `__pycache__`。

# 最终回复

给出：补丁改法；`killing_tests`；实际运行结果。只报告实际运行过的结果。
