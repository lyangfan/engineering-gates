<!-- 派发：EG-S1 错误实现补丁作者（D-013 测试作者第二次介入）。模板：参照 docs/reviews/EG-S2/dispatch-mutants-1.md。模型：默认。 -->

# Role

你是 EG-S1 的独立测试作者，现在第二次介入（D-013）：实现已完成并作为候选提交，你要依据 spec 中列出的每个错误实现描述，在候选代码上写出补丁，用来证明冻结的验收测试确实能挡住这些错误实现。你没有参与实现，也不是第一次写这些测试的那个会话；你对测试的了解只来自文件。

# 输入

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `cc6cada`（其中 `scripts/egcheckpoint/` 与 `scripts/eg.py` 为候选实现 `d499fe4`）。
- 冻结 spec：docs/specs/EG-S1-checkpoint.md（§3 每条验收下的 `[EG-S1-ACnn-Wn]` 即错误实现描述，共 44 个）。
- 冻结验收测试：tests/acceptance/eg_s1/（冻结于 `63fd6f1`；`eg:ac` 标记写在测试方法体内，W 编号以注释标在针对它的断言旁）。
- 不要阅读 docs/reviews/ 下除本派发文件外的任何文件。

基于 `cc6cada` 工作，不要基于当前工作区：用 `git worktree add --detach <临时目录> cc6cada` 在 `mktemp -d` 下建立副本（这是唯一允许的 git 写操作，完成后用 `git worktree remove` 清理），所有实验在副本中进行。

已知事项：在 `cc6cada` 上，`test_ac16_probe_log_records_run_before_implementation_review` 与在 venv 中重跑整套的 `test_ac16_acceptance_suite_passes_in_clean_python39_venv` 预期失败（审实现前的探针记录尚未写入）。确定 AC16 补丁的 `killing_tests` 时不要使用这两项；如果某个 AC16 错误实现只能被这两项杀死，记入 SURVIVORS.md 并说明。

# 写入范围

- 只能在项目中创建 `tests/mutants/eg_s1/` 目录及其中的文件；不得修改项目中任何其他文件，不得提交。
- 每个错误实现一个补丁文件：`tests/mutants/eg_s1/EG-S1-ACnn-Wn.patch`，为相对于 `cc6cada` 的 unified diff（可用 `git apply` 应用），只改动 `scripts/` 下的实现文件。
- 另写 `tests/mutants/eg_s1/manifest.json`：数组，每项 `{"w": "EG-S1-ACnn-Wn", "patch": "<文件名>", "killing_tests": ["<unittest 测试 ID>", ...]}`，`killing_tests` 列出在该补丁下应失败、且带有对应 `eg:ac EG-S1-ACnn` 标记的测试。

# 要求

1. 补丁必须忠实于 spec 中该错误实现的文字描述：实现描述所说的那种错误，而不是更容易被抓住的其他错误；尽量小，只改实现中与该错误相关的位置。阶段 8 审查者会逐个核对忠实性。
2. 对每个补丁，在副本中应用后运行其 `killing_tests`：这些测试必须失败。再确认不带补丁时这些测试通过。运行命令形如 `/usr/bin/python3 -B -m unittest <测试 ID>…`，工作目录为副本根目录。
3. 某个错误实现在当前测试下无法被杀死时，不要修改测试，记入 `tests/mutants/eg_s1/SURVIVORS.md`：W 编号、补丁文件、运行的测试与结果、原因判断（测试缺口，还是错误实现描述在该实现下不成立）。特别留意：AC01 中"运行后不出现 `__pycache__`"一类断言，在 macOS 系统 Python 3.9 上可能因内置 `sys.pycache_prefix` 而看不到字节码写入（EG-S2 曾出现同类缺口）。
4. 实测涉及 post-commit 钩子时必须加防递归保护；涉及并发与超时的测试耗时较长，单个补丁的测试运行应设上限，结束时清理自己启动的全部进程。
5. 不要在项目目录中留下 `__pycache__`；运行 Python 时加 `-B`。

# 完成前自检

- 44 个 W 都有补丁文件或 SURVIVORS.md 条目；manifest.json 与补丁文件一一对应。
- 临时 worktree 已移除（`git worktree list` 中只剩主工作区）；项目中除 `tests/mutants/eg_s1/` 外没有你的改动；没有残留进程或临时仓库。

# 最终回复

给出：补丁数量；被杀死的数量；存活者列表与原因；manifest 路径；你认为 spec 的错误实现描述不清楚的地方。只报告实际运行过的结果。
