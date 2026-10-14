# EG-S1 验收测试：spec 问题与解释记录

依据：`docs/specs/EG-S1-checkpoint.md`（基准 commit `26f2e0c`）。本文件列出无法写出确定断言、需要解释或无法直接构造的地方，以及测试采取的处理。测试未自行发明 spec 之外的行为；凡是下面写明"按字面解释"的，都是对 spec 原文的最窄读法。

## 一、需要裁决或澄清的 spec 问题

### N-01 钩子拒绝如何与其他 git 失败区分（EG-S1-C11、C02、AC11）

- spec 原文：C11"恢复成功时，输出 `result: error`（钩子拒绝时为 `refused`）"；C02"`error`：git 执行失败、超时、锁冲突"。
- 问题：pre-commit 钩子拒绝时 git 本身不输出可识别的信息，退出码为 1，与其他提交失败（例如没有可提交内容）的退出码相同。spec 没有规定实现如何判定"钩子拒绝"。AC11 明确要求钩子失败时为 `refused`，测试照此断言（`test_ac11_failing_pre_commit_hook_refused_and_restored`、`test_ac09_unrelated_state_preserved`、`test_ac17_hook_failure_output`），但判定依据留给实现。建议在 spec 中写明判定方法。

### N-02 运行标识不在输出中，AC15 的"本次运行的 `EG-Run`"无法从对外接口直接核对（AC15、C10、C12）

- spec 原文：AC15"退出码为 0 的进程报告的提交带本次运行的 `EG-Run`"。
- 问题：C12 的输出 JSON 不含运行标识，从标准输出无法得知"本次运行"的标识。
- 处理：并发测试在 PATH 前放置 git 包装脚本，记录每次 `commit -F <文件>` 时提交信息文件的内容，并按父进程号（即 eg 进程）归属到各进程，再断言报告的提交的 `EG-Run` 属于该进程。这要求 eg 直接以子进程方式启动 git（C14 的"以参数列表方式执行"自然满足）。

### N-03 "没有锁文件被删除"的观测手段（AC15、C15）

- spec 原文：AC15"没有锁文件被删除"。
- 问题：并发场景中的锁由 git 自己创建与删除，外部无法区分"git 正常释放"与"实现删除"。
- 处理：通过 `PYTHONPATH` 注入一个只装审计钩子（`sys.addaudithook`）的 `sitecustomize`，记录 eg 进程内对 `.git/*.lock` 的 `os.remove`/`os.rename`/`os.truncate`/`shutil.rmtree`，以及以 `rm`/`unlink`/`mv`/`find` 处理锁文件的子进程；并断言审计钩子在两个 eg 进程中都已生效。通过其他途径删除（如 ctypes）观测不到。单进程场景（`test_ac15_held_lock_bounded_retries`、`test_ac11_lock_held_after_add_reports_staged_paths`）直接核对锁文件存在且内容不变。

### N-04 探针运行记录是过程证据（AC16、C16）

- spec 原文：AC16"实现开始前与审实现前各有一份探针运行记录"；C16"运行环境的 git 版本不是 2.50.1 时，在运行记录中单列"。
- 问题：（1）"审实现前"的记录在实现者跑测试时按流程尚不应存在，因此 `test_ac16_probe_log_records_run_before_implementation_review` 在审查阶段之前必然失败，实现者也无法通过改代码使其通过；（2）记录格式未规定。
- 处理：按任务说明字面检查 `docs/specs/probes/EG-S1-git-probes.log.md` 中出现"实现开始前"与"审实现前"字样（两个独立测试，当前均失败）。git 版本单列一项未检查（无法从记录格式中确定断言）。建议把这一项移出自动化验收，改由审查清单核对。

### N-05 已暂存锁冲突时是否执行恢复（AC15、C11）

- spec 原文：C11"若 C08 的 `add` 已执行，对本次全部有改动的路径执行一次 `git reset`"；AC15"总耗时不超过 6 秒（提交与恢复各 2 秒的等待预算…）"。
- 问题：预先持有 `index.lock` 时失败的是 `add` 本身，"`add` 已执行"是否包含"执行了但失败"不明确，因此是否还要消耗恢复的 2 秒预算不确定。
- 处理：测试只断言 6 秒总上限与结果，不断言是否尝试了恢复。

### N-06 参数错误时 `paths` 的内容（C17、AC17）

- spec 原文：C17"`paths` 列出命令行给出的每个路径，`status` 取 `not_committed`"，且同样适用于退出码 2。
- 问题：遇到未知参数等解析错误时，"命令行给出的路径"需要实现在解析失败后仍能提取 `--path` 的值。spec 没有对此做例外，测试按字面要求（`test_ac10_invalid_arguments_exit_2`、`test_ac17_argument_error_output` 中的 `unknown-option` 等情况）。若这不是本意，需要在 spec 中写明例外。

### N-07 spec 文件状态行

- `docs/specs/EG-S1-checkpoint.md` 第 3 行仍写"草稿 v0.4…未冻结"，而提交 `9fdd94a` 的说明是冻结于 `3955513`。测试以 `26f2e0c` 中的内容为准。

## 二、测试对 spec 的解释（未发明新行为，但读法需要说明）

- C01：只断言成功时标准错误非空（"可读摘要写到标准错误"）；失败时是否有摘要未断言。
- C01/AC01 `__pycache__`：把项目复制到临时目录（排除 `.git`、`__pycache__`、`*.pyc`）后运行副本的 `scripts/eg.py`，子进程环境去掉 `PYTHONDONTWRITEBYTECODE`、`PYTHONPYCACHEPREFIX`，运行后副本与夹具仓库中都不得出现 `__pycache__`。这样不受仓库中历史残留的字节码影响，也不写入真实仓库。
- C03/C13：消息"指出该路径"按包含命令行原样给出的路径字符串断言；"违反的规则"无法确定文字，不断言。
- C05：两项都缺时只断言消息含 `user.name` 或 `user.email` 之一；只缺一项时断言含该项名称。环境变量只测试设置为非空值的情况。
- C10/AC10：提交信息按 spec 模板逐行断言（首行、空行、三行 trailer）。AC10-W4 的"可预测"无法完全证明，测试以"同一仓库中连续两次运行"和"两个相同仓库中相同输入"四个标识互不相同来检测。
- C11：恢复失败时的恢复命令只在单一路径的场景中断言为 `git reset -q -- <路径>`；多个路径时是一条命令还是逐路径给出，未断言；含空格等特殊字符的路径如何引用未规定，也未断言。
- C12：`message`"给出找到的提交号"按包含提交号的前 7 位断言（允许完整或缩写）。
- C13：工作区文件缺失时按 spec 断言 `result` 为 `mismatch`。
- C14：`EG_GIT_TIMEOUT_SECONDS` 为空字符串时 spec 未明确，未测试；测试了 `abc`、`301`、`0`、`-5`、`1.5`（退出码 2）与 `300`、`30`（接受）。超时场景断言 `result` 为 `error`（C02 把超时列为 `error`）。"钩子及其子进程在命令结束时都已不存在"：命令结束后允许 2 秒供系统回收，僵尸进程视为已不存在。另以包装脚本核对每次 git 调用的进程组与 eg 不同（C14"在独立的进程组中启动"）。
- C14"不经过 shell"：静态检查实现源码（`scripts/` 下基准 commit 中不存在的 `.py` 文件）中没有 `shell=` 非 False、`os.system`、`os.popen`、`getoutput`，以及以字符串作为命令传给 `subprocess` 的调用。
- C17：在 `main` 上被拒绝时断言 `branch` 为 `main`（可确定时不为 null）；参数错误时 `branch` 是否可确定不明确，未断言。
- AC08"写操作"的判定：`git status` 与只带刷新参数的 `git update-index --refresh` 不改变暂存区内容，不计为写操作；未知子命令一律计为写操作。
- AC11 的"人为终止进程"：包装脚本在 `git add` 返回后立即向 eg 发 SIGKILL，保证实现来不及恢复。
- AC16"干净虚拟环境"：用 Python 3.9 `-m venv --without-pip` 建立虚拟环境（不含系统与用户 site-packages），在其中运行本目录全部测试；内层运行通过环境变量跳过这一个测试本身以免递归，因此全套耗时约为两倍。venv 创建失败时 skip。

## 三、运行环境问题（不是 spec 问题）

- 本机 `/usr/bin/python3` 的用户 site-packages（`~/Library/Python/3.9/lib/python/site-packages/tests/`，由 `ppdiffusers` 安装）中有一个普通包 `tests`。普通包优先于命名空间包，所以在基准 commit `26f2e0c`（仓库中没有 `tests/__init__.py`）上，按任务给出的命令运行会报 `ModuleNotFoundError: No module named 'tests.acceptance'`；当时只能以 `PYTHONNOUSERSITE=1` 运行。
- 编写期间分支上新增了提交 `e09f7df`（EG-S2 测试冻结），其中带有 `tests/__init__.py` 与 `tests/acceptance/__init__.py`。此后原命令可以直接运行。若在没有这两个文件的检出上运行，需要设置 `PYTHONNOUSERSITE=1`。AC16 的干净虚拟环境不含用户 site，不受影响。
