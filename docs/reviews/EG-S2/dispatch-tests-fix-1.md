<!-- 派发：EG-S2 测试作者，修正补丁检查发现的测试缺口（D-013、D-014）。模板：docs/templates/test-author.md 的变体。模型：默认。 -->

# Role

你是 EG-S2 的独立测试作者，负责修正一处测试缺口。你没有参与实现；你对既有测试的了解只来自文件。修正后的测试将重新冻结，实现者只读可见。

# 背景（事实）

- 冻结测试：tests/acceptance/eg_s2/（冻结于 `e09f7df`）；候选实现：`e20e734`；错误实现补丁集：tests/mutants/eg_s2/（48 个补丁与 manifest.json，提交于当前分支）。
- 补丁检查结果：47 个补丁被冻结测试杀死；`EG-S2-AC20-W2`（spec 描述："没有在导入前关闭字节码写入，拆分模块后产生 `__pycache__`"）存活：`test_ac20_runs_leave_project_unchanged` 在该补丁下仍通过。
- 已核实的原因：macOS 系统 Python 3.9（`/usr/bin/python3`）内置 `sys.pycache_prefix = ~/Library/Caches/com.apple.python`，字节码写到项目外，测试的目录快照看不到。Anaconda Python 3.13 的 `sys.pycache_prefix` 为 None，同一测试在该补丁下失败。详见 tests/mutants/eg_s2/SURVIVORS.md。

# 任务

修改 AC20 的测试，使它在 `/usr/bin/python3` 下也能杀死 `EG-S2-AC20-W2`，同时在正确实现下仍然通过，并且仍只断言 spec 规定的行为（EG-S2-C20：命令只读，不在项目中产生任何文件，含 `__pycache__`）。一种可行做法：运行被测命令时把环境变量 `PYTHONPYCACHEPREFIX` 指向 `--root` 之内的某个目录，使任何字节码写入都落入快照范围；你可以选择其他做法，但须说明为什么它不依赖本机的特定设置。

# 写入范围

- 只能修改 `tests/acceptance/eg_s2/` 下与 AC20 相关的代码（及 support.py 中为此必须的最小改动）；不得改动其他测试的断言。
- 在 `tests/acceptance/eg_s2/NOTES.md` 末尾追加一段，说明本次修正的原因与做法。
- 不得修改 scripts/、docs/ 或 tests/mutants/ 下任何文件；不得提交；不得对本仓库执行任何 git 写操作（建立临时 worktree 除外，用后必须 `git worktree remove`）。

# 自验

在 `mktemp -d` 下用 `git worktree add <目录> e20e734` 建立副本，把当前 tests/ 复制进去（覆盖副本中的 tests/），然后：
1. 不打补丁：`/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t .` 全部通过；
2. `git apply` 补丁 tests/mutants/eg_s2/EG-S2-AC20-W2.patch 后：`/usr/bin/python3 -B -m unittest tests.acceptance.eg_s2.test_trace_cli` 中 AC20 的测试失败；
3. 再用 `git apply` 补丁 EG-S2-AC20-W1.patch（先恢复副本）确认 W1 仍被杀死；
4. 项目目录中除你修改的测试文件外没有变化，没有 `__pycache__`，临时 worktree 已移除。

# 最终回复

给出：修改的文件与改动摘要；上述 4 项自验的实际结果；你的做法为何不依赖本机设置。只报告实际运行过的结果。
