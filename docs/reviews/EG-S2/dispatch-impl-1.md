<!-- 事后补存：2026-10-14 派发 EG-S2 实现者时发送的提示词原文（D-035 生效前派发）。执行模型：按用户会话指示为 Grok 4.7，最高思考档，非 Fast。 -->

# Role

你是 EG-S2（静态追溯检查 `trace`）的实现者，处于阶段 7。规格已冻结，验收测试已由独立测试作者写好并冻结。你的目标是写出实现，使冻结的验收测试全部通过，并且实现真正满足 spec，而不是只满足测试。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，HEAD 应为 `cf440ec`。
- 冻结 spec：docs/specs/EG-S2-trace.md（唯一的行为依据；其 sha256 应为 97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62，请先核对）。文件头的“草稿”字样是历史遗留，spec 已冻结。
- 冻结验收测试：tests/acceptance/eg_s2/（只读，含 NOTES.md：测试作者对 spec 未定处的读法）
- 可参考：docs/design/decisions.json、docs/design/design-v2.md

# 写入范围（严格遵守）

- 只能在 `scripts/` 下新建文件：`scripts/eg.py`（统一入口）以及你需要的新模块或新子目录。
- 不得修改或删除 scripts/ 下已有的 0.1.0 文件（engineering.py、decision_coverage.py、digest_table.py、snapshots.py、run_tests.py、__init__.py、tests/）。
- 不得修改 tests/、docs/ 下任何文件。唯一例外：如果你认为某个验收测试本身有误（违背 spec、或依赖 spec 未规定的细节），不要改测试，也不要为了迁就它写违背 spec 的代码；把异议写进新文件 `docs/reviews/EG-S2/disputes.md`，每条写明测试名、对应条款或验收 ID、理由与 spec 原文（D-014）。
- 不得执行任何 git 写操作（add、commit、stash、checkout、reset 等）。

# 实现要求

1. 只用 Python 3.9 标准库；不使用 3.10 及以上的语法或标准库参数（如 `match`、`X | Y` 类型注解在运行时求值、`glob` 的 `root_dir`）。用 `/usr/bin/python3`（3.9.6）开发和测试。
2. 遵守 spec 的全部条款，特别是：只读（C20：`scripts/eg.py` 在导入任何其他本地模块之前设置 `sys.dont_write_bytecode = True`）、标准输出只写一个 JSON 报告、可读摘要写标准错误（C19）、退出码 0/1/2 的边界（C19、C24）、代码排除规则（C22）、块边界（C26）、`--spec` 范围（C23）、匹配语义使用 `glob.glob(os.path.join(root, pattern), recursive=True)`（C01、F-04）。
3. `scripts/eg.py` 只实现分发到 `trace` 子命令所需的最小部分（spec §1 非目标）；之后 EG-S1 会在同一入口增加 `checkpoint`、`identity` 子命令，请把分发写得便于增加子命令，但不要预先实现它们。
4. 不得在实现中检测“是否处于测试中”或针对具体测试夹具写特判。
5. 不得 import science-gates 的任何代码。

# 自验

- `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v`：目标全部通过（注意 AC21 会在临时 venv 中重跑）。
- 0.1.0 原有测试不得被破坏：`/usr/bin/python3 -B -m unittest discover -s scripts/tests -p 'test_*.py'`。
- 运行后仓库中不得出现 `__pycache__`；`git status --short` 中只应出现你在 scripts/ 下新建的文件（以及可能的 disputes.md）。

# 最终回复

给出：新建文件列表与各自职责；验收测试结果（通过/失败数，失败的测试名与原因）；0.1.0 测试结果；提出的测试异议（如有）；你认为 spec 中仍不明确、你是如何处理的地方。不要声称通过了你没有实际运行过的测试。
