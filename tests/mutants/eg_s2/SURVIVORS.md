# EG-S2 错误实现补丁：存活者

基准：候选实现 commit `e20e734`；冻结验收测试 `tests/acceptance/eg_s2/`（与冻结 commit `e09f7df` 无差异）。运行命令：`/usr/bin/python3 -B -m unittest <测试 ID>`，工作目录为 `e20e734` 的临时 worktree 根目录。`/usr/bin/python3` 为 macOS 系统 Python 3.9.6。

## EG-S2-AC20-W2

- 错误实现描述：没有在导入前关闭字节码写入，拆分模块后产生 `__pycache__`。
- 补丁：`EG-S2-AC20-W2.patch`。把 `scripts/eg.py` 中的 `sys.dont_write_bytecode = True` 移到 `from egtrace.engine import ...` 之后，其他不变。
- 带 `eg:ac EG-S2-AC20` 标记的测试只有一个：`tests.acceptance.eg_s2.test_trace_cli.ReadOnlyTests.test_ac20_runs_leave_project_unchanged`。
- 结果：
  - 用 `/usr/bin/python3`（派发规定的解释器）运行，应用补丁后**通过**（`Ran 1 test ... OK`）→ 存活。不带补丁时同样通过。
  - 同一测试改用 Anaconda Python 3.13.5（`python3 -B -m unittest <同一 ID>`）运行，应用补丁后**失败**：两个子测试都报出新增的 `scripts/egtrace/__pycache__/__init__.cpython-313.pyc` 和 `engine.cpython-313.pyc`。不带补丁时通过。
- 原因：macOS 系统 Python 3.9 自带非空的 `sys.pycache_prefix`（`/Users/<用户>/Library/Caches/com.apple.python`），环境里不设 `PYTHONPYCACHEPREFIX` 时也是如此。在这个解释器上，补丁导入 `egtrace` 时写出的字节码落在 `~/Library/Caches/com.apple.python/private/var/.../scripts/egtrace/*.cpython-39.pyc`（已实际找到这些文件），而不是 `--root` 下的 `__pycache__`。测试只比较 `--root` 前后的快照，所以看不到它。`support.clean_env()` 会去掉环境里的 `PYTHONPYCACHEPREFIX`，但去不掉这个内置默认值。
- 判断：这是**测试缺口**，取决于运行环境，不是错误实现描述本身不成立。在没有内置 pycache 前缀的解释器上（实测 Anaconda 3.13），描述中的错误确实会在项目里产生 `__pycache__`，测试也能抓到。在派发规定的 `/usr/bin/python3` 上，同样的错误会写出字节码，但写到项目外，C20/AC20 的断言察觉不到。
- 可能的测试侧修正（仅建议，未修改测试）：在 AC20 中运行复制出的 `scripts/eg.py` 时，显式设置 `PYTHONPYCACHEPREFIX=<夹具根目录下的某个子目录>`（已验证系统 3.9 上 `PYTHONPYCACHEPREFIX` 与 `-X pycache_prefix=` 都能覆盖内置默认值），或用 `-X pycache_prefix=` 把字节码引回被快照覆盖的目录。这样不论解释器默认前缀为何，`sys.dont_write_bytecode` 失效都会表现为快照中的新增文件。
- `manifest.json` 中该项的 `killing_tests` 为空数组，因为在规定解释器下没有测试会失败。

## 更新（协调者，2026-10-14）

上文关于 EG-S2-AC20-W2 的记录基于候选 `e20e734` 与冻结于 `e09f7df` 的测试，已不再成立：AC20 测试在 `0a04a62` 修正（以 `-X pycache_prefix=` 运行被测命令）后，该补丁被杀死；候选修复后补丁按新候选 `22ea31a` 重写，协调者在干净 worktree 中复核 48/48 被杀死。当前没有存活者。上文保留作历史记录。
