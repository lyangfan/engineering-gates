<!-- 派发：EG-S2 实现者修复实现审查 B1 的 finding。模板：docs/templates/implementer.md 的修复变体。模型：按用户会话指示为 Grok 4.7，最高思考档，非 Fast。 -->

# Role

你是 EG-S2（静态追溯检查 `trace`）的实现者，处于阶段 7 的修复轮。独立实现审查 B1 裁定 FAIL，用户已确认以下 finding 均为实现错误、spec 不变。你的目标是修复它们，使实现满足冻结 spec，不改变其他行为。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `1504751`（其中 `scripts/` 与候选 `e20e734` 相同）。
- 冻结 spec：docs/specs/EG-S2-trace.md（sha256 97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62）。
- 审查报告：docs/reviews/EG-S2/review-impl-B1.md（每条 finding 有原文、依据、可复现反例与最小修复）。
- 冻结验收测试：tests/acceptance/eg_s2/（只读）。另一位测试作者正并行为这些 finding 编写回归测试，你看不到它们。

# 要修复的 finding（用户已定性）

- IB1-01（实现错误）：AUTHOR-CHOICE 标记后紧跟汉字或字母时未被识别。按 spec C11、C13、C22 识别标记，不得以标记后的字符类别作为判断条件。
- IB1-02（实现错误）：未给 `--spec` 时，C17 的"测试文件中出现的验收 ID 若不存在于任何已存在的 spec 文件，即报错"适用于全部测试标记，包括前缀不在地图中或其 spec 文件不存在的标记；只有带 `--spec` 时才按 C23 收窄。
- IB1-03（实现错误）：spec ID 不得写死为特定形式；spec ID 集合以档位表第一列为准（C25），条款、验收、错误实现、文件名前缀与测试标记的识别都以该集合为准（C10、C14、C16、C17）。
- IB1-05（实现错误）：C07"决定未出现在分配表"的报告中，`path` 与 `line` 必须指向同一文件中的同一位置（例如 `path` 为决策登记、`line` 为该决定所在行，或 `path` 为 spec 地图、`line` 为分配表位置），不得混用。
- IB1-04 已接受为已知限制，不要修改。

# 工作方式与写入范围

- 在 `mktemp -d` 下用 `git worktree add --detach <目录> 1504751` 建立副本，所有修改与运行都在副本中进行。主工作区中另一会话正在修改 `scripts/eg.py`（EG-S1），不要触碰主工作区的 `scripts/`。
- 在副本中只修改 `scripts/egtrace/` 下的文件；不得修改 `scripts/eg.py`、0.1.0 文件、tests/、docs/。
- 完成后在副本中执行 `git diff -- scripts/egtrace > <主工作区>/docs/reviews/EG-S2/impl-fix-1.patch`，把补丁写入主工作区的这个唯一文件；然后 `git worktree remove` 移除副本。不得对主工作区做任何其他写入，不得提交。
- 认为某个冻结测试与 spec 冲突时，不要改测试，写入主工作区新文件 `docs/reviews/EG-S2/disputes.md`（D-014）。

# 实现要求

只用 Python 3.9 标准库；不使用 3.10 以上语法；不针对测试写特判；不 import science-gates。

# 自验（在副本中）

- 用审查报告中每条 finding 的反例复现：修复前出现问题，修复后不再出现。
- `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t .` 全部通过。
- `/usr/bin/python3 -B scripts/eg.py trace --mode tests` 在副本根目录运行通过（副本中有 eg.json）。
- 副本中不出现 `__pycache__`。

# 最终回复

给出：补丁文件路径与改动摘要（按 finding 分）；每条 finding 反例的修复前后实际结果；验收测试结果；提出的测试异议（如有）。只报告实际运行过的结果。
