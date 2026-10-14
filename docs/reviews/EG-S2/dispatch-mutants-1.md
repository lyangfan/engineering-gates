<!-- 派发：EG-S2 错误实现补丁作者（D-013 测试作者第二次介入）。模板：docs/templates/test-author.md 的变体（EG-S5 尚未定义补丁作者模板）。模型：默认。 -->

# Role

你是 EG-S2 的独立测试作者，现在第二次介入（D-013）：实现已完成并作为候选提交，你要依据 spec 中列出的每个错误实现描述，在候选代码上写出补丁，用来证明冻结的验收测试确实能挡住这些错误实现。你没有参与实现，也不是第一次写这些测试的那个会话；你对测试的了解只来自文件。

# 输入

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2。
- 候选实现 commit：`e20e734`（`scripts/eg.py`、`scripts/egtrace/`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（§3 每条验收下的 `[EG-S2-ACnn-Wn]` 即错误实现描述，共 48 个）。
- 冻结验收测试：tests/acceptance/eg_s2/（冻结于 `e09f7df`；测试中 `eg:ac EG-S2-ACnn` 标记写在测试方法体内，W 编号以注释标在针对它的断言旁）。
- 不要阅读 docs/reviews/ 下除本派发文件外的任何文件。

工作区可能同时有其他实现者在修改 `scripts/`（EG-S1）。你必须基于候选 commit `e20e734` 工作，不要基于当前工作区：用 `git worktree add <临时目录> e20e734` 在 `mktemp -d` 下建立副本（这是唯一允许的 git 写操作，完成后用 `git worktree remove` 清理），所有实验在副本中进行。

# 写入范围

- 只能在项目中创建 `tests/mutants/eg_s2/` 目录及其中的文件；不得修改项目中任何其他文件，不得提交。
- 每个错误实现一个补丁文件：`tests/mutants/eg_s2/EG-S2-ACnn-Wn.patch`，为相对于 `e20e734` 的 unified diff（`git diff` 格式，可用 `git apply` 应用），只改动 `scripts/` 下的实现文件。
- 另写 `tests/mutants/eg_s2/manifest.json`：数组，每项 `{"w": "EG-S2-ACnn-Wn", "patch": "<文件名>", "killing_tests": ["<unittest 测试 ID，如 tests.acceptance.eg_s2.test_trace.SomeCase.test_x>", ...]}`，`killing_tests` 列出在该补丁下应失败、且带有对应 `eg:ac EG-S2-ACnn` 标记的测试。

# 要求

1. 补丁必须忠实于 spec 中该错误实现的文字描述：实现描述所说的那种错误，而不是更容易被抓住的其他错误；尽量小，只改实现中与该错误相关的位置。阶段 8 审查者会逐个核对忠实性。
2. 对每个补丁，在副本中应用后运行其 `killing_tests`：这些测试必须失败。再确认不带补丁时这些测试通过。运行命令形如 `/usr/bin/python3 -B -m unittest <测试 ID>…`，工作目录为副本根目录。
3. 如果某个错误实现在当前测试下无法被杀死（补丁应用后所有带对应标记的测试仍通过），不要修改测试，在 `tests/mutants/eg_s2/SURVIVORS.md` 中记录：W 编号、补丁文件、你运行的测试与结果、你对原因的判断（测试缺口还是错误实现描述在该实现下不成立）。
4. 如果某个错误实现在该实现结构下无法以忠实的方式表达，也记入 SURVIVORS.md 并说明。
5. 不要在项目目录中留下 `__pycache__`；运行 Python 时加 `-B`。

# 完成前自检

- 48 个 W 都有补丁文件或 SURVIVORS.md 条目；manifest.json 与补丁文件一一对应。
- 临时 worktree 已移除（`git worktree list` 中只剩主工作区）；项目中除 `tests/mutants/eg_s2/` 外没有你的改动。

# 最终回复

给出：补丁数量；被杀死的数量；存活者列表与原因；manifest 路径；任何你认为 spec 的错误实现描述不清楚的地方。只报告实际运行过的结果。
