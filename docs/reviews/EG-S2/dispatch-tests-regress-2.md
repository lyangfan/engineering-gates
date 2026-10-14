<!-- 派发：EG-S2 测试作者，为实现审查 C1 的 finding 编写回归测试并修正 IC1-03 所指测试（第 2 周期）。模板：docs/templates/test-author.md 的变体。模型：默认（含测试修正，按会话指示的"测试缺口修正"归类）。 -->

# Role

你是 EG-S2 的独立测试作者。你没有参与实现；另一位实现者正并行修复下列缺陷，你看不到其修复。你写的测试将重新冻结，实现者只读可见。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `9b795a0`（其中 `scripts/egtrace/` 为候选 `22ea31a`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（唯一的行为依据）。
- 审查报告：docs/reviews/EG-S2/review-impl-C1.md（只为了解缺陷所在；断言以 spec 条款为依据）。
- 冻结验收测试：tests/acceptance/eg_s2/（含 test_trace_regress.py、support.py、NOTES.md）。

# 任务

1. **IC1-01 回归测试**：覆盖声明到第一个 `：` 结束（C14、C15）。至少包括报告中的 CASE 1（`覆盖 A、B：A：……；B：……`）与 CASE 2（声明后的正文中出现另一个条款 ID 紧跟 `：`）两种写法，期望退出码 0、无 C14/C15 失败；可加入 spec ID 形式为非 `EG-S<数字>` 的同构变体。
2. **IC1-02 回归测试**：同一决定在分配表中出现多次时，C07 失败项的 `path` 与 `line` 指向同一文件中的同一位置（C19）。
3. **IC1-03 修正**：`test_ac07_missing_allocation_failure_points_into_its_path` 当前要求 `line` 所在行提到该决定（`assertIn("D-003", lines[line - 1])`），严于 C19（C19 只要求行号为 1 起始、不对应具体行时为 null）。在不放宽到失去意义的前提下修正该断言，使"`path` 为决策登记、`line` 为该决定所在行""`path` 为 spec 地图、`line` 为分配表中的位置""`line` 为 null"三种修法都能通过，同时仍能挡住 IB1-05 原来的错误（`path` 为 spec 地图而 `line` 为登记中的行号，且该行号超出或不对应分配表）。说明你如何区分。若你认为无法在 C19 范围内区分，写入 NOTES.md 并说明。

# 写入范围与工作方式

- 在 `mktemp -d` 下用 `git worktree add --detach <目录> 9b795a0` 建立副本，所有修改与运行在副本中进行。主工作区与其他 worktree 中有其他会话在工作，不要触碰。
- 在副本中只修改 `tests/acceptance/eg_s2/` 下的文件；不得改动其他测试的断言。新测试以 `eg:ac EG-S2-ACnn` 标记所属验收，并在注释中写明 IC1 编号；在 NOTES.md 末尾追加一节说明。
- 完成后在副本中执行 `git diff -- tests/acceptance/eg_s2 > <主工作区>/docs/reviews/EG-S2/tests-regress-2.patch`（新文件先 `git add -N`），然后 `git worktree remove`。不得对主工作区做其他写入，不得提交。

# 要求

1. 只断言 spec 规定的行为；Python 3.9 标准库 unittest；通过子进程运行 `scripts/eg.py trace`。
2. IC1-01、IC1-02 的新测试在候选实现（副本中的 `scripts/`，即 `22ea31a`）上必须失败；请实际运行确认并记录失败原因。
3. 修正后的 IC1-03 测试在候选实现上仍通过（当前实现把 `path` 指向决策登记）；另用一个临时改动模拟 IB1-05 原错误，确认它仍被挡住，然后还原。
4. 其余既有测试在副本中仍全部通过。

# 最终回复

给出：补丁文件路径；新增与修改的测试及其对应的 IC1 编号与 spec 条款；在候选实现上的运行结果；IC1-03 的区分方式与验证结果。只报告实际运行过的结果。
