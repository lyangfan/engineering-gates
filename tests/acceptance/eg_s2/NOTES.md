# EG-S2 验收测试说明

测试依据：`docs/specs/EG-S2-trace.md`（基准 commit `26f2e0c`）。本文件记录运行环境问题、spec 中无法写出确定断言之处，以及测试对含糊处采取的处理。凡下文写“不断言”的，测试都没有针对该点做断言。

## 0. 运行环境：入口命令在本机被用户站点包遮蔽

- 现象：`/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v` 在本机报 `ModuleNotFoundError: No module named 'tests.acceptance'`，一个测试都不运行。
- 原因：`~/Library/Python/3.9/lib/python/site-packages/tests/__init__.py` 是一个普通包，它遮蔽了仓库根目录下没有 `__init__.py` 的 `tests/` 命名空间包。测试作者只能在 `tests/acceptance/eg_s2/` 下写文件，无法添加 `tests/__init__.py` 或 `tests/acceptance/__init__.py`。
- 已验证可用的等价命令（结果相同）：
  - `PYTHONNOUSERSITE=1 /usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v`
  - `/usr/bin/python3 -s -B -m unittest discover -s tests/acceptance/eg_s2 -t . -v`
  - `/usr/bin/python3 -B -m unittest discover -s tests/acceptance/eg_s2 -v`（不带 `-t .`；测试文件对此有回退导入）
- 建议由流程维护者决定：在 `tests/`、`tests/acceptance/` 下补 `__init__.py`，或把入口命令改为上面某一种。

## 1. spec 未规定、测试按最弱可判定的方式处理的点

| 验收 | spec 原文 | 问题 | 测试的处理 |
|---|---|---|---|
| EG-S2-AC01 | “各自退出码为 2 并指出问题字段” | spec 没有说明用 `failures` 的哪个字段“指出”问题字段，而 message 文字不规定 | 断言退出码 2、`result` 为 `error`，并断言问题字段名（如 `tests`、`bogus_key`、`design`、`decisions`、`spec_map`、`specs`、`schema`）出现在 `failures` 序列化后的文本中（通常即 message）。若审查认为这超出 spec，可删去 `assertMentions` 一行 |
| EG-S2-AC01、C19 | C01：“均为配置错误（退出码 2）”；C19：“输入错误只有以下情形：`eg.json` … 不符合 C01” | `eg.json` 配置错误时 `failures[].check` 应为 `EG-S2-C01` 还是 `EG-S2-C19`，spec 未定 | 只断言 check ∈ {`EG-S2-C01`, `EG-S2-C19`} |
| EG-S2-AC02 | “各自报告对应条目且退出码为 1” | 未规定如何在报告中标识“对应条目”（message、line 还是 path） | 每个夹具只含一个缺陷，断言退出码 1 且出现 `EG-S2-C02`；不断言条目如何被标识 |
| EG-S2-AC25 | “档位表中没有的 spec ID 出现在清单列头时报错” | 未规定该失败归属 `EG-S2-C25` 还是 `EG-S2-C09` | 断言退出码 1，且失败中含 `EG-S2-C25` 或 `EG-S2-C09` 之一 |
| EG-S2-AC13 | `local_choices` 示例 `"line": 40` | 未规定 line 指条款标记所在行还是 AUTHOR-CHOICE 标记所在行 | 夹具把两者写在同一行，断言 line 等于该行 |
| EG-S2-AC19 | “path 为相对于 `--root` 的路径，使用 `/` 分隔” | 用法错误时 path 取值未规定；输入错误（如 `eg.json` 中的绝对路径）时出问题的文件可能不在 `--root` 下 | 只在退出码为 1 的报告中断言 path 为 null 或不含 `\` 的相对路径；不断言 line 的具体取值，只断言为 null 或 ≥1 的整数 |
| EG-S2-AC19 | C19：“决策登记 … 顶层不符合 C02”为输入错误；C02 只列举了“顶层不是对象、`decisions` 不是数组、`schema` 值不符” | 顶层多出第三个键是否属于“顶层不符合 C02”（C02 写的是“恰好含”） | 按 C19 的概括规定处理：顶层多键断言退出码 2 |
| EG-S2-AC18 | “`mode` 在无法解析时为 `null`” | `--mode bogus`、`--mode tests --freeze` 等能解析出值但非法的组合，`mode` 是否为 null 未定 | 只对缺少 `--mode` 断言 `mode` 为 null；所有用法错误都断言 `specs` 为 `[]`，且 check 只出现 `EG-S2-C18`（`--spec` 取值问题为 `EG-S2-C23`） |
| EG-S2-AC23、C19 | 报告字段 `"specs": ["EG-S2"]` | spec 只规定用法错误时为空数组，没有明文规定正常运行时 `specs` 的含义（是否为选中的 spec 列表） | 正常运行时只断言 `specs` 是数组 |
| EG-S2-AC19 | “可读摘要写到标准错误” | 未规定通过时是否也必须输出摘要 | 只在存在失败的运行中断言标准错误非空 |

## 2. spec 未覆盖、测试未涉及的情形

- EG-S2-C17 与 EG-S2-C23：未给 `--spec` 时，测试文件中出现前缀为地图外 spec（如 `EG-S9`）或文件不存在的 spec（如 `EG-S3`）的验收 ID。C17 说“不存在于任何已存在的 spec 文件即报错”，C23 又说“C10—C17 只作用于选中的 spec”，两条结合后结论不确定。测试只使用前缀为已存在 spec 的不存在 ID（`EG-S2-AC99`）。
- EG-S2-C24：design 模式下 `specs` 零匹配是否报错没有明文（C24 只写了 spec 与 tests 模式），不测。
- EG-S2-C10：`nn` 少于两位（如 `**[EG-S2-C1]**`）是报错还是不识别为标记，未定，不测。
- EG-S2-C07：去向中出现地图档位表以外的 spec ID、或非 active 决定出现在分配表中，未定，不测（夹具不含这两种情况）。
- EG-S2-C14：验收标记后缺少覆盖声明时归哪条 check，未定，不测。
- EG-S2-C19：spec 文件或测试文件（由模式匹配得到，而非 `eg.json` 直接列出）无法按 UTF-8 解码时，属于“`eg.json` 所列文件”的输入错误还是检查失败，未定，不测（AC24 只要求 GBK 设计稿退出码为 2）。

## 3. 关于 AC20 / AC21 的夹具说明

- EG-S2-AC20：按任务说明，把仓库 `scripts/`（排除 `__pycache__`、`*.pyc`）复制到夹具根目录，再运行复制品的 `scripts/eg.py`，此时不设 `PYTHONDONTWRITEBYTECODE`、不加 `-B`。对夹具根目录下全部目录与文件内容做运行前后比对，覆盖通过、失败、`--freeze`、缺省 `--root`（cwd 为夹具根）与用法错误几种运行。其余测试运行仓库内的 `scripts/eg.py` 时设置 `PYTHONDONTWRITEBYTECODE=1`，避免在仓库中留下 `__pycache__`。
- EG-S2-AC21：在临时目录中用 Python 3.9 创建 `--without-pip` 虚拟环境（优先 `sys.executable`，否则 `/usr/bin/python3`），先确认其中 `yaml` 不可导入，再运行命令。找不到 3.9 解释器或 venv 创建失败时 skip；本机自测中 venv 创建成功，未 skip。“源码不 import science-gates”通过扫描 `scripts/**/*.py` 中的 import 语句、`import_module` / `__import__` 调用与 `sys.path` 操作实现，并要求 `scripts/eg.py` 存在。

## 4. 测试文件中的标记

- 测试文件中的 `eg:ac EG-S2-ACnn` 字面量只用于本 spec 的真实验收。夹具里的测试标记在运行时由 `support.ac_marker()` 拼接生成，因此将来对本仓库运行 `trace --mode tests` 时，夹具中的 `EG-S2-AC99`、`EG-S1-AC99` 等不会被误认为本仓库的测试标记。
