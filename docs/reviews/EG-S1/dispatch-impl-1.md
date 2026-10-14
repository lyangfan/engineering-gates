<!-- 派发：EG-S1 实现者。模板：docs/templates/implementer.md。模型：按用户会话指示为 Grok 4.7，最高思考档，非 Fast。 -->

# Role

你是 EG-S1（身份与检查点：`checkpoint`、`identity` 子命令）的实现者，处于阶段 7。spec 已冻结，验收测试已由独立测试作者写好并冻结。你的目标是写出实现，使冻结的验收测试全部通过，并且实现真正满足 spec，而不是只满足测试。这是严格档：锁、超时、并发与恢复路径必须按 spec 精确实现。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2。
- 冻结 spec：docs/specs/EG-S1-checkpoint.md（唯一的行为依据；冻结 commit `3955513`，其 sha256 应为 `git show 3955513:docs/specs/EG-S1-checkpoint.md | shasum -a 256` 的结果，请先核对工作区文件与之一致）。文件头的"草稿 v0.4…未冻结"是历史遗留，spec 已冻结。
- 冻结验收测试：tests/acceptance/eg_s1/（冻结于 `63fd6f1`，只读，含 NOTES.md：测试作者对 spec 未定处的读法）。
- 现实核验：docs/specs/probes/EG-S1-git-probes.sh 与 .log.md（F-11—F-21）。
- 已有入口：`scripts/eg.py` 与 `scripts/egtrace/` 是 EG-S2 的已完成实现（候选 commit `e20e734`）。
- 可参考：docs/design/decisions.json、docs/design/design-v2.md。

协调者告知的已知事项：
- `test_ac16_probe_log_records_run_before_implementation_review` 在阶段 8 之前必然失败：该记录由协调者在派发审查前写入。不要为通过它而编辑探针记录或任何 docs 文件。
- C11 要求钩子拒绝时 `result` 为 `refused`，但 git 对 pre-commit 失败只返回 1，spec 未规定识别方法。请设计一种不依赖测试特判、在真实仓库中同样成立的识别方式；若确实无法可靠满足 AC11，按下文提测试异议。
- 另一会话可能同时在临时 worktree 中对 EG-S2 做补丁实验，它不会改动 `scripts/`。

# 写入范围（严格遵守）

- 只能在 `scripts/` 下新建文件（建议新包 `scripts/egcheckpoint/`），并且可以修改 `scripts/eg.py`，但只能在其分发表中增加 `checkpoint`、`identity` 两个子命令分支，不得改变 `trace` 的任何行为（EG-S1 影响登记、EG-S2 冻结）。
- 不得修改 `scripts/egtrace/` 与 scripts/ 下已有的 0.1.0 文件（engineering.py、decision_coverage.py、digest_table.py、snapshots.py、run_tests.py、__init__.py、tests/）。
- 不得修改 tests/、docs/ 下任何文件。唯一例外：认为某个验收测试本身有误时，不要改测试，也不要为了迁就它写违背 spec 的代码；把异议写进新文件 `docs/reviews/EG-S1/disputes.md`，每条写明测试名、对应条款或验收 ID、理由与 spec 原文（D-014）。
- 不得对本仓库执行任何 git 写操作（add、commit、stash、checkout、reset 等）。实验只在 `mktemp -d` 下自建的 git 仓库中进行；实测 post-commit 钩子时必须加防递归保护。

# 实现要求

1. 只用 Python 3.9 标准库与 git 命令行；不使用 3.10 及以上的语法或标准库参数；不依赖第三方 git 库。用 `/usr/bin/python3`（3.9.6）开发和测试。
2. 遵守 spec 全部条款，特别是：检查顺序（C02）；路径规则以仓库根为基准（C03）；身份检查含配置项与环境变量（C05）；暂存内容保护（C06）；"有改动"含可执行位（C07）；只用 `add -- <路径>` 与 `commit --only -F … -- <路径>`，不用 `--no-verify`（C08）；失败后精确恢复与恢复失败的报告（C11）；按 `EG-Run` 找到本次提交并核对改动路径（C12）；非成功输出（C17）；git 在独立进程组中启动、超时先 SIGTERM 后 SIGKILL、`EG_GIT_TIMEOUT_SECONDS` 只能为 1—300（C14）；锁冲突的有界重试、绝不删除锁（C15）。
3. 不得在实现中检测"是否处于测试中"或针对具体测试夹具写特判。
4. 不得 import science-gates 的任何代码。

# 自验

- `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s1 -t . -v`：目标除上述 AC16 那一项外全部通过（AC16 还会在临时 venv 中重跑整套）。
- EG-S2 不得被破坏：`/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t .` 全部通过。
- 0.1.0 测试：`/usr/bin/python3 -B -m unittest discover -s scripts/tests -p 'test_*.py'` 全部通过。
- 运行后仓库中不得出现 `__pycache__`；`git status --short` 中只应出现你在 scripts/ 下的改动（以及可能的 disputes.md）；没有残留进程。

# 最终回复

给出：新建与修改的文件及各自职责；三套测试的结果（通过/失败数，失败的测试名与原因）；钩子拒绝的识别方式；提出的测试异议（如有）；你认为 spec 中仍不明确、你是如何处理的地方。不要声称通过了你没有实际运行过的测试。
