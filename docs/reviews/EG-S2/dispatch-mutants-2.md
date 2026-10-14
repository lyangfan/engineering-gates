<!-- 派发：EG-S2 错误实现补丁重写（候选实现修复后有 10 个补丁无法应用）。模板：参照 dispatch-mutants-1.md。模型：默认。 -->

# Role

你是 EG-S2 的独立测试作者（D-013 补丁作者）。候选实现在实现审查 B1 后被修复，`scripts/egtrace/engine.py` 改动，原有 48 个错误实现补丁中有 10 个已无法应用到新的候选实现上。你要在新候选上重写这 10 个补丁，使其仍忠实于 spec 中的错误实现描述，并证明冻结测试能杀死它们。你没有参与实现与修复。

# 输入

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `c01ec78`（新候选实现 `22ea31a`；测试最新冻结 `ef8e915`，含新增的 `test_trace_regress.py`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（错误实现描述在 §3）。
- 现有补丁与清单：tests/mutants/eg_s2/（原补丁基于 `e20e734`）。
- 不要阅读 docs/reviews/ 下除本派发文件外的任何文件。

需要重写的 10 个：EG-S2-AC02-W3、EG-S2-AC07-W1、EG-S2-AC09-W1、EG-S2-AC09-W2、EG-S2-AC14-W1、EG-S2-AC17-W1、EG-S2-AC17-W2、EG-S2-AC18-W1、EG-S2-AC20-W2、EG-S2-AC22-W2。其余 38 个协调者已在新候选上验证可应用且被杀死，不要修改。

# 工作方式与写入范围

- 用 `git worktree add --detach <临时目录> c01ec78` 在 `mktemp -d` 下建立副本，实验只在副本中进行，完成后 `git worktree remove`。
- 只能覆盖写这 10 个补丁文件，并相应更新 tests/mutants/eg_s2/manifest.json 中这 10 项（`killing_tests` 可以包括新测试文件中带对应 `eg:ac` 标记的测试）；补丁为相对于 `c01ec78` 的 unified diff，只改 `scripts/` 下实现文件。不得修改项目中其他文件，不得提交。
- 无法以忠实方式表达或无法被杀死的，写入 tests/mutants/eg_s2/SURVIVORS.md 并说明（不要改测试）。

# 自验

对每个重写的补丁：在副本中 `git apply --check` 通过；不打补丁时其 `killing_tests` 通过；打补丁后这些测试失败。运行用 `/usr/bin/python3 -B -m unittest <测试 ID>…`。项目中不留 `__pycache__`。

# 最终回复

给出：重写的补丁数；被杀死的数量；存活者与原因；对错误实现描述的理解有变化之处（如有）。只报告实际运行过的结果。
