<!-- 派发：EG-S2 测试作者为实现审查 B1 的 finding 编写回归测试（D-013、D-014）。模板：docs/templates/test-author.md 的变体。模型：默认。 -->

# Role

你是 EG-S2 的独立测试作者，为实现审查发现、但现有冻结测试未覆盖的缺陷编写回归测试。你没有参与实现；另一位实现者正并行修复这些缺陷，你看不到其修复。你写的测试将重新冻结，实现者只读可见。

# 输入（只读）

仓库 /Users/liuyangfan/Documents/work/engineering-gates，分支 eg/v2，基准 commit `1504751`（其中 `scripts/` 为候选实现 `e20e734`）。
- 冻结 spec：docs/specs/EG-S2-trace.md（唯一的行为依据）。
- 审查报告：docs/reviews/EG-S2/review-impl-B1.md（只为了解缺陷所在；断言必须以 spec 条款为依据，而非以报告的措辞为依据）。
- 冻结验收测试：tests/acceptance/eg_s2/（含 support.py 与 NOTES.md）。

# 要覆盖的 finding（用户已定性为实现错误）

- IB1-01：AUTHOR-CHOICE 标记后紧跟汉字或字母（例如 `[AUTHOR-CHOICE:substantive]需用户决定`）时，仍须被识别：`--freeze` 下残留 substantive 标记须失败（C13），local 标记须出现在 `local_choices` 中且条款不被报 C11（C11）。
- IB1-02：未给 `--spec` 时，测试文件中出现前缀不在地图中（如 `EG-S9-AC01`）或其 spec 文件不存在的验收 ID，tests 模式须报错（C17）；带 `--spec` 时按 C23 收窄的既有行为不变。
- IB1-03：spec ID 不限于 `EG-S<数字>` 形式；以档位表第一列为准（C25）。例如全部 spec ID 为 `APP-S1`、`APP-S2` 的夹具项目，design、spec、tests 三种模式的识别与检查结果应与 `EG-S1`、`EG-S2` 的同构夹具一致（C10、C14、C16、C17、C25）。
- IB1-05：C07"决定未出现在分配表"的失败项中，`path` 与 `line` 必须指向同一文件中的同一位置（C19 要求失败项给出路径和行号）。
- IB1-04 已接受为已知限制，不要编写测试。

# 写入范围与工作方式

- 在 `mktemp -d` 下用 `git worktree add --detach <目录> 1504751` 建立副本，所有修改与运行在副本中进行。
- 在副本中只修改 `tests/acceptance/eg_s2/` 下的文件：新增测试（可放入新文件，如 `test_trace_regress.py`），必要时对 support.py 做最小增补；不得改动既有测试的断言。测试中以 `eg:ac EG-S2-ACnn` 标记所属验收（选择最贴近的既有验收 ID），并在注释中写明对应的 IB1 编号。在 NOTES.md 末尾追加一节说明。
- 完成后在副本中执行 `git diff -- tests/acceptance/eg_s2 > <主工作区>/docs/reviews/EG-S2/tests-regress-1.patch`（新文件须先 `git add -N` 以纳入 diff），写入主工作区的这个唯一文件；然后 `git worktree remove` 移除副本。不得对主工作区做任何其他写入，不得提交。

# 要求

1. 只断言 spec 规定的行为；Python 3.9 标准库 unittest；通过子进程运行 `scripts/eg.py trace`。
2. 新测试在基准候选实现（副本中的 `scripts/`，即 `e20e734`）上必须失败——这证明它们确实测到了这些缺陷；请实际运行确认，并记录每个新测试的失败原因。
3. 既有 81 个测试在副本中仍全部通过。

# 最终回复

给出：补丁文件路径；新增测试列表及各自对应的 IB1 编号与 spec 条款；在候选实现上的运行结果（每个新测试失败、既有测试通过）；spec 中你认为仍不明确的地方（如有）。只报告实际运行过的结果。
