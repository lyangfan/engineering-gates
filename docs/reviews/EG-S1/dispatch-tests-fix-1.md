<!-- 派发：EG-S1 测试作者修正补丁检查中发现的两处测试问题（D-013、D-014）。模板：参照 docs/reviews/EG-S2/dispatch-tests-fix-1.md。模型：默认。 -->

# Role

你是 EG-S1 的独立测试作者，负责修正两处测试问题。你没有参与实现；你对既有测试的了解只来自文件。修正后的测试将重新冻结，实现者只读可见。修正不得改变任何测试所断言的行为含义，也不得放宽断言。

# 输入

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `997ba8e`（候选实现 `d499fe4`；冻结测试 `63fd6f1`；错误实现补丁集 tests/mutants/eg_s1/，44/44 被杀死）。
- 冻结 spec：docs/specs/EG-S1-checkpoint.md。
- 冻结测试：tests/acceptance/eg_s1/（含 support.py 与 NOTES.md）。
- 补丁作者的记录：tests/mutants/eg_s1/SURVIVORS.md（含下述 AC01 实验）。
- 不要阅读 docs/reviews/ 下除本派发文件外的任何文件。

# 要修正的问题

1. **AC01 字节码检查的盲区。** `test_ac01_no_pycache_after_running` 断言运行后不出现 `__pycache__`（EG-S1-C01 共用 EG-S2-C20 的入口行为）。补丁作者实测：把 `scripts/eg.py` 中的 `sys.dont_write_bytecode = True` 换成 `pass`，该测试仍通过。原因：macOS 系统 Python 3.9 内置 `sys.pycache_prefix` 指向 `$HOME/Library/Caches/com.apple.python`，测试把子进程的 `HOME` 设到夹具的 `home/` 下，字节码写到测试不检查的位置。EG-S2 的同类问题已通过以 `-X pycache_prefix=` 运行被测命令并加前置检查解决（见 tests/acceptance/eg_s2/test_trace_cli.py 中 AC20 部分与 eg_s2/NOTES.md 第 5 节），可参考，但须在本套件中自行实测其有效性。
2. **AC14 超时测试可能不稳定。** 补丁作者在干净 venv 中重跑整套时，`test_ac14_timeout_terminates_hook_process_group` 出现过一次"hook did not start"失败，其他多次运行通过。请找出原因（例如等待钩子启动的同步方式依赖时序，在负载下 1 秒超时可能早于钩子启动），在不改变断言含义、不放宽"超时后不残留 index.lock、暂存区恢复、钩子及其子进程已结束"等断言的前提下，使测试在负载下稳定。若你认为问题在实现而非测试，不要改测试，写入 NOTES.md 并说明证据。

# 工作方式与写入范围

- 在 `mktemp -d` 下用 `git worktree add --detach <目录> 997ba8e` 建立副本，所有修改与运行在副本中进行。
- 在副本中只修改 `tests/acceptance/eg_s1/` 下与上述两处相关的代码（及 support.py 中为此必须的最小改动）；在 NOTES.md 末尾追加一节说明原因与做法。
- 完成后在副本中执行 `git diff -- tests/acceptance/eg_s1 > <主工作区>/docs/reviews/EG-S1/tests-fix-1.patch`，写入主工作区的这个唯一文件；然后 `git worktree remove` 移除副本。不得对主工作区做其他写入，不得提交。实测 post-commit 钩子时必须加防递归保护；清理自己启动的全部进程。

# 自验（在副本中）

1. 不打任何补丁：`/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s1 -t .` 中，除两项 AC16"审实现前探针记录"相关测试外全部通过。
2. 把 `scripts/eg.py` 中的 `sys.dont_write_bytecode = True` 换成 `pass`：修正后的 AC01 测试失败；恢复后通过。
3. 应用 tests/mutants/eg_s1/EG-S1-AC01-W1.patch：AC01 仍被杀死。
4. AC14 稳定性：修正后的 AC14 测试连续运行至少 10 次全部通过；并在另有 4 个并行 CPU 负载进程（例如 `yes > /dev/null`，用后结束）时再运行至少 5 次全部通过。应用 tests/mutants/eg_s1/EG-S1-AC14-W1.patch、W2.patch 各一次，AC14 仍被杀死。
5. 项目目录中除补丁文件外没有变化，没有 `__pycache__`，临时 worktree 已移除，没有残留进程。

# 最终回复

给出：修改的文件与改动摘要；AC14 不稳定的原因判断与证据；上述 5 项自验的实际结果（含次数）。只报告实际运行过的结果。
