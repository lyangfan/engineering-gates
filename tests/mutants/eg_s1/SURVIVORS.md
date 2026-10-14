# EG-S1 错误实现补丁：存活者

基准 `cc6cada`（候选实现 `d499fe4`），冻结验收测试 `tests/acceptance/eg_s1/`（`63fd6f1`）。环境：macOS，`/usr/bin/python3` 3.9.6，git 2.50.1 (Apple Git-155)。

## 结论

44 个错误实现全部有补丁，全部被杀死，没有存活者。

## 运行方式与结果

- 每个补丁都在 `cc6cada` 的独立副本中用 `git apply` 应用，测试命令为 `/usr/bin/python3 -B -m unittest <测试 ID>…`，工作目录为副本根目录，单个补丁的运行上限为 600 或 900 秒，超时会杀掉整个进程组。
- 第一轮：每个补丁运行带有对应 `eg:ac EG-S1-ACnn` 标记的全部测试（AC16 的两项除外，见下文），失败的测试即记入 `manifest.json` 的 `killing_tests`。AC14、AC15 的补丁串行运行，其余补丁 4 个并行。
- 第二轮：每个补丁重新应用到新副本，只运行它的 `killing_tests`，44 个补丁的全部 `killing_tests` 都失败。
- 不带补丁的对照：`cc6cada` 上运行全部 69 项测试，只有 `test_ac16_probe_log_records_run_before_implementation_review` 与 `test_ac16_acceptance_suite_passes_in_clean_python39_venv` 失败（派发时已说明这两项预期失败）。另外把 manifest 中出现的 48 个不同的 `killing_tests` 在未打补丁的副本上合并运行一次：48 项全部通过。
- 失败原因逐项核对过，均为补丁所描述的那种错误造成（例如 AC03-W1 只在 `directory` 子用例失败，AC03-W2 只在 `symlink` 子用例失败，AC14-W2 为 `index.lock left behind`，AC15-W1 在并发测试中由审计钩子记录到 `os.remove` 删除锁文件）。

## AC16 的两项排除

按派发要求，AC16 补丁的 `killing_tests` 中没有使用上述两项。AC16-W1（3.10 才有的 `match` 语法）被 `test_ac16_sources_compile_with_python39` 杀死，另外两项源码检查测试因 `ast.parse` 抛出 `SyntaxError` 而报错，也一并列入。AC16-W2（`import git`，即 GitPython）被 `test_ac16_sources_import_only_stdlib_and_local_modules` 杀死。两者都不依赖被排除的两项。

## 附注：AC01 的 `__pycache__` 断言存在测试缺口（不对应任何 W）

AC01 下只有 W1 一个错误实现，所以这一条不是存活者，只是额外实验的记录。

- 实验：在副本中把 `scripts/eg.py` 的 `sys.dont_write_bytecode = True` 换成 `pass`，运行 `test_ac01_no_pycache_after_running`：测试通过。
- 原因：macOS 系统 Python 3.9 内置 `sys.pycache_prefix = $HOME/Library/Caches/com.apple.python`，字节码不写进源码旁的 `__pycache__`，而是写到该前缀下。测试夹具把子进程的 `HOME` 设为夹具目录下的 `home/`，所以字节码落在 `<夹具>/home/Library/Caches/com.apple.python/…`；测试只检查项目副本与夹具仓库 `repo/`，看不到这些文件。另外直接运行了同一个修改后的 `eg.py`（`HOME` 指向临时目录），确认 `.pyc` 写到了 `$HOME/Library/Caches/com.apple.python/…` 下。
- 判断：属于测试缺口。在这台机器上，"运行后不出现 `__pycache__`"无法证明入口关闭了字节码写入。可行的补法是在子进程环境中设置 `PYTHONPYCACHEPREFIX` 指向被检查的目录，或者同时检查夹具的 `HOME` 下有没有 `.pyc`。
