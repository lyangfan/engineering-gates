# EG-S2 审查账本

> 协调者维护；审查报告不可变，本账本是其动态投影（D-016）。预算：标准档 1 Baseline + 1 Closure。

## 轮次

| 轮次 | 报告 | sha256 | 受审 spec sha256 | 裁定 |
|---|---|---|---|---|
| B1 | review-B1.md | 2e5b5e2ee7c014d8921696b3d3ced0a1bb6562514ebbe93f21fc5eb482ed37e4 | 4cc564afca8e343689c7b2a60d46a6264c8756587b0076b568621a9e59367163 | FAIL（1 BLOCKER、10 MAJOR、4 MINOR） |
| C1 | review-C1.md | 03d1449ac4c88c390d261ae3809a60e75705e72f4f84d27f5a9a8b6a0ee9526d | 53c017ca25d016a1e9f895af40aec1c14f30ddcf32c68633798ddfda2d35d280 | PASS（6 MINOR） |

| R1 | review-R1.md | 56bb9184ec60…（全值见 freeze.json） | 97c744d7200ee358f9eb73c708cc870db5f22e02de1a3138e79497c08005fe62 | PASS（1 MINOR） |

预算 B1 + C1 已用完；R1 是用户在 C1 PASS 后决定的冻结前轻量复核，范围只限 v0.4→v0.5 diff（RC-05）。

**状态：FROZEN（2026-10-14）**，冻结字节 sha256 `97c744d7…fe62`，冻结记录见 `freeze.json`。冻结后的变更按 D-017 处理。冻结字节已随提交 `f5f112a`（分支 `eg/v2`）进入本地 git，git 中的字节与冻结记录的 sha256 一致；此后的身份以 commit 为准（D-015）。

## Findings

| ID | 严重度 | 检查项 | 摘要 | 处置 | 状态 |
|---|---|---|---|---|---|
| B1-01 | BLOCKER | R2 | 登记字段集、AUTHOR-CHOICE 标记写法、反引号排除规则是实质选择，却被标为已由 D-006/D-007/D-022 决定 | v0.3 改标 substantive，列入格式包 F1—F3 | VERIFIED_CLOSED（C1） |
| B1-02 | MAJOR | R4 | eg.json 键与匹配语义、spec 地图表格结构、JSON 报告结构、输出流未定义；glob 在 3.9 与 3.13 行为不同 | v0.3 起草 C01、C07、C09、C19、C25，列入格式包 F4、F6、F8；F-04 已核验 | VERIFIED_CLOSED（C1） |
| B1-03 | MAJOR | R4 | spec 文件与 spec ID 的对应、未起草 spec 是否执行 C12 未定义 | v0.3：C10 文件名规则（格式包 F5）；C12 只作用于文件已存在的 spec；C09 要求条款 ID 实际存在 | VERIFIED_CLOSED（C1） |
| B1-04 | MAJOR | R6 | 反引号排除规则适用范围不明 | v0.3：提为独立条款 C22 并列明范围（格式包 F3） | VERIFIED_CLOSED（C1） |
| B1-05 | MAJOR | R4 | 条款/验收边界、覆盖声明语法、错误实现归属未定义 | v0.3：C26、C14、C16（格式包 F7） | VERIFIED_CLOSED（C1） |
| B1-06 | MAJOR | R4 | 验收 ID 与错误实现 ID 唯一性未要求 | v0.3：C14、C16 加唯一性；AC14、AC16 补错误实现 | VERIFIED_CLOSED（C1） |
| B1-07 | MAJOR | R1 | C08 对上调也要求理由，超出 D-008；未检查规则结果与清单一致 | v0.3：C08 改写；AC08-W2 | VERIFIED_CLOSED（C1） |
| B1-08 | MAJOR | R4 | 被 supersedes 引用的决定仍可保持 active | v0.3：C04 双向约束；AC04-W3 | VERIFIED_CLOSED（C1） |
| B1-09 | MAJOR | R4 | 退出码 1 与 2 的边界未定义 | v0.3：C19 列出输入错误情形，C24 定 BOM 与零匹配（格式包 F8） | VERIFIED_CLOSED（C1） |
| B1-10 | MAJOR | R3 | AC20 目录比对会因 `__pycache__` 误判 | v0.3：C20 要求导入前关闭字节码写入（local）；AC20 只保留目录比对 | VERIFIED_CLOSED（C1） |
| B1-11 | MAJOR | R4 | CLI 无法选择单份 spec，并行草稿使 --freeze 与 tests 必然失败 | 用户选 `--spec` → D-023；v0.3：C23、AC23 | VERIFIED_CLOSED（C1） |
| B1-12 | MINOR | R1 | C20 引用 D-015、C07 引用 D-010 不支持条款内容 | v0.3：C20 改引 D-022，C07 改引 D-007 | VERIFIED_CLOSED（C1） |
| B1-13 | MINOR | R3 | AC21 缺"使用 3.10+ 语法"的错误实现 | v0.3：AC21-W2 | VERIFIED_CLOSED（C1） |
| B1-14 | MINOR | R5 | F 引用存在性交 EG-S3 未记入地图；eg.py 归属不清 | v0.3 非目标写明；spec 地图 EG-S3 目标待格式包决定后一并更新 | VERIFIED_CLOSED（C1） |
| B1-15 | MINOR | R6 | C18 重复列 C13；--freeze 与模式组合未定义 | v0.3：C18 改写并规定非法组合返回 2 | VERIFIED_CLOSED（C1） |

| C1-01 | MINOR | R6 | 带 `--spec` 时，C10 文件名规则与 C17 未知验收 ID 的作用范围未写明 | v0.5：C23 写明 `--spec` 对 C10、C17 的收窄（按 D-023 原文） | VERIFIED_CLOSED（R1） |
| C1-02 | MINOR | R3 | AC01 的模式区分不出 AC01-W2；F-04 结果写法不准确（pathlib 只在以 `**` 结尾的模式上不同） | v0.5：AC01 加以 `**` 结尾的模式；F-04 结果改写 | VERIFIED_CLOSED（R1） |
| C1-03 | MINOR | R1 | `--root` 不在 D-022、D-023、D-024 中，是未经决定的 CLI 选择 | 用户保留 `--root` → D-025 | VERIFIED_CLOSED（R1） |
| C1-04 | MINOR | R1 | C12 写"分配给它的每条决定"，D-010 只要求 active 决定 | v0.5：C12 改为"每条 active 决定" | VERIFIED_CLOSED（R1） |
| C1-05 | MINOR | R6 | 报告示例 `freeze:false` 而 `local_choices` 非空；用法错误时是否输出 JSON；`path` 的基准目录 | v0.5：C19 写明 path 基准、local_choices、用法错误时的报告 | VERIFIED_CLOSED（R1） |
| C1-06 | MINOR | R4 | C26 未写明围栏代码中以 `#` 开头的行不算标题 | v0.5：C26 写明围栏代码中的行不是标题；AC26-W2 | VERIFIED_CLOSED（R1） |

| R1-01 | MINOR | R6 | 用法错误时报告中 `failures[].path`、`freeze`、`result` 的取值未写明 | 接受为已知限制，下次编辑性修订时补一句（D-017 编辑性） | ACCEPTED_LIMITATION |

## 冻结后待办（编辑性，不改 EG-S2 字节）

- 决策登记：D-025 补 `amends: ["D-022"]`，D-022 的 `amended_by` 加 D-025（R1 备注）。
- spec 地图 §1：EG-S2 主要决定列补 D-025（R1 备注）。

## 阶段 6：测试冻结

- 独立测试作者（只读 spec 与 F-01—F-04，不读审查记录）交付 81 个测试，覆盖 AC01—AC26 与全部 48 个错误实现；在实现前的代码上全部失败（143 处失败，0 报错、0 skip）。
- 测试冻结于 `e09f7df`（`EG-Kind: tests-freeze`），测试只读给实现者（D-013、D-014）。
- 实现开始前重跑 F-01—F-04（D-012，2026-10-14）：3.9.6 与 3.13.5 上 glob 均得 19 个相同文件；pathlib `docs/**` 在 3.9 不含文件、3.13 含文件；3.9 无 `tomllib`。全部与 spec §4 一致。
- 协调者补 `tests/__init__.py`、`tests/acceptance/__init__.py`，使仓库内 `tests` 成为普通包，不被用户 site-packages 中同名包遮蔽（局部选择，属测试基础设施）。

### 测试作者记录的 spec 未定处（冻结后变更候选，待按 D-017 判级）

见 `tests/acceptance/eg_s2/NOTES.md`。测试对这些点只做最弱可判定的断言或不测：

- 未给 `--spec` 时，测试标记中出现地图外或文件不存在的 spec 前缀（C17 与 C23 结合后不确定）；
- design 模式下 `specs` 零匹配；一位数字的条款编号；分配表去向中出现档位表外的 spec ID 或非 active 决定；验收标记后缺少覆盖声明；模式匹配到的文件无法按 UTF-8 解码；
- `eg.json` 配置错误的 `check` 归 C01 还是 C19；`local_choices` 的 `line` 指条款行还是标记行。

## 阶段 7：实现与补丁检查

- 实现者（按用户会话指示为 Grok 4.7，派发原文 `dispatch-impl-1.md`）交付候选实现 `e20e734`；协调者复核：81 项验收通过、0.1.0 测试通过、写入范围合规、无测试特判、无 `__pycache__`；无测试异议。实现者对 spec 未定处的取舍见其报告（记于本账本下文"实现者对未定处的取舍"），交阶段 8 审查。
- 补丁检查（D-013，派发 `dispatch-mutants-1.md`）：48 个错误实现补丁，首轮 47 个被杀死；协调者在干净 worktree 中独立重跑，结论一致。存活者 EG-S2-AC20-W2：macOS 系统 Python 3.9 内置 `sys.pycache_prefix`，字节码写到项目外，测试快照看不到（测试缺口，非 spec 问题）。
- 测试修正（D-014 参照，派发 `dispatch-tests-fix-1.md`）：测试作者改为以 `-X pycache_prefix=` 运行被测命令并加前置检查（协调者建议的 `PYTHONPYCACHEPREFIX` 方案经其实测会使正确实现失败，未采用）。协调者复核：改动只涉及 AC20；修正后 48/48 补丁被杀死；修正后的完整套件在 `e20e734` 上 81 项通过。测试重新冻结（见下一个 tests-freeze 提交）。
- 审实现前重跑 F-01—F-04（D-012）：3.9.6 29 False; 3.13.5 29 True; ModuleNotFoundError: No module named 'tomllib'——与 spec §4 一致。

### 实现者对未定处的取舍（交阶段 8 审查）

`..` 按路径分量判断；设计稿中决定编号按登记格式（至少三位）识别，条款分类接受一位以上数字；未给 `--spec` 时 C17 只检查前缀属于已有文件的 spec 的测试标记；`local_choices[].line` 取标记所在行；清单列头有、档位表无的 spec ID 报 C25；`eg.json` 配置错误的 check 用 C01；少于两位数字的标记不识别；分配表中不存在的决定编号或档位表外的 spec ID 报 C07，非 active 决定的多余行不报；覆盖声明只认同一行紧接标记的部分，缺失报 C14；匹配到的 spec 或测试文件无法按 UTF-8 解码时退出码 2；design 模式下 `specs` 零匹配不报 C24；`specs` 为本次选中的 spec，错误时为空数组；`--spec` 不合法时只返回 C23。

## 阶段 8：实现审查

预算：标准档 1 Baseline + 1 Closure。

| 轮次 | 报告 | sha256 | 受审 commit | 裁定 |
|---|---|---|---|---|
| IB1 | review-impl-B1.md | 9a9697be04fdd395aa13e9d53d94d98c07df9f81a339a8c44b43a8837f56b6dc | 93ccc09（scripts 同 e20e734） | FAIL（3 MAJOR、2 MINOR） |

| ID | 严重度 | 检查项 | 摘要 | 处置 | 状态 |
|---|---|---|---|---|---|
| IB1-01 | MAJOR | I1 | AUTHOR-CHOICE 标记后紧跟汉字或字母时不被识别（`isalnum()` 对汉字为真），`--freeze` 下未决实质选择被放行 | 待定 | OPEN |
| IB1-02 | MAJOR | I2 | 不带 `--spec` 时忽略前缀不属于已有 spec 的测试标记，与 C17、D-010 冲突 | 待定 | OPEN |
| IB1-03 | MAJOR | I1/I2 | spec ID 写死为 `EG-S<数字>`，与 C25"以档位表第一列为准"冲突 | 待定 | OPEN |
| IB1-04 | MINOR | I5 | supersedes 链长约 1000 以上递归崩溃 | 待定 | OPEN |
| IB1-05 | MINOR | I5 | C07"未出现在分配表"的 `line` 取自登记文件而 `path` 为 spec 地图 | 待定 | OPEN |

## 复盘候选

- RC-03：作者把未经决定的格式标为"已由 D-022 决定"——引用存在但不支持条款内容，机械检查无法发现，由 R1/R2 审查抓到。
- RC-04：标准档 spec 若未定义全部对外格式，D-013 的"测试作者先写测试"无法开始；可考虑在阶段 4 增加"每个对外输入输出都有格式定义"的机械检查。
- RC-05：D-017 只规定冻结后的变更；审查 PASS 之后、冻结之前的 MINOR 修订该怎样处理，流程没有定义。
- RC-06：v0.2 原文被覆盖，C1 只能依据手写变更清单（RC-02 的直接后果）；D-015 落地前，每轮受审字节至少应复制留存。
- RC-13：D-013 只规定补丁必须使测试失败，没有规定存活者由谁修测试、是否重新冻结；本次参照 D-014 由新的测试作者修正并重新冻结。应在 EG-S4 中写明。
- RC-14：协调者建议的测试修法（PYTHONPYCACHEPREFIX）经测试作者实测会使正确实现失败；派发中的"建议做法"须标为可替换，并要求执行者实测。
- RC-15：三条 MAJOR 均未被 81 项验收测试与 48 个补丁发现：测试与补丁只覆盖 spec 中列出的错误实现，覆盖不到"实现者自己引入的另一种错误"（如 `isalnum()` 对汉字为真、写死 spec ID 格式）。阶段 8 审查是唯一能发现这类问题的环节。
