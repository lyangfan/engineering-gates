# engineering-gates

engineering-gates 是一个独立的、面向工程开发流程的 Codex Skill。它把上游需求、设计和决策整理为可执行的工程合同，再用冻结合同审查代码、构建、测试和运行证据。首版为 0.1.0，许可证为 MIT，文档以中文为主，公共 schema 使用英文。

## 两道门

    需求 / 设计 / 决策
            │
            ▼
    门 A：工程合同审查（A1–A9）
            │  spec、上游身份和合同冻结
            ▼
    代码 / 构建 / 测试 / 运行 receipt
            │
            ▼
    门 B：实现验证审查（B1–B7）
            │
            ▼
    候选 ledger → 项目 reviewer 登记正式 Engineering PASS

门 A 固定检查：

- A1 决策和需求逐条落地；
- A2 外部事实、工作区政策和依赖版本有固定锚；
- A3 未决语义和参数明确列出并交 Decision Owner；
- A4 每项行为和禁止事项都有能击败错误实现的验收；
- A5 输入、输出、写入面、no-clobber 和禁写范围完整；
- A6 术语、路径、版本、状态和依赖在全文一致；
- A7 外部事实绑定不可移动的 commit、tag 或精确版本，并声明漂移后的停止动作；
- A8 多份上游、跨文件撤销和审查期间新增决定有唯一状态来源；
- A9 触碰既有 spec、公共 API 或兄弟合同时有影响登记和迁移方式。

门 B 固定检查：

- B1 实现逐条符合冻结 spec；
- B2 测试、构建和验收证据真实覆盖要求，断言能击败错误实现；
- B3 实现行为与代码、日志、测试和 receipt 一致；
- B4 上下游 API、schema、错误词表、状态和兼容语义一致；
- B5 成功、失败、取消、超时、崩溃、恢复、重放、并发、释放、分类和重试路径闭合；
- B6 权限、资源、并发和输出上限在真实执行点读取并强制；
- B7 每次 attempt 独立保存，首次失败不被覆盖，不能靠 rerun-until-green 掩盖 flaky 测试。

BLOCKER / MAJOR 阻止 PASS；MINOR / OPINION 必须登记 owner 但不阻止 PASS。未决语义产生 NEEDS_USER_DECISION。默认每门最多一轮 Baseline 加一轮 Closure；预算耗尽仍有阻塞项时登记 NON_CONVERGENT 并停止。

## 安装和调用

把本目录作为 Skill 放在 /Users/liuyangfan/Documents/work/engineering-gates，或复制到 Codex 的 skills 目录。CLI 只有四个稳定入口：

    python3 scripts/engineering.py render <manifest>
    python3 scripts/engineering.py check <manifest>
    python3 scripts/engineering.py run <manifest> --step <id> --receipt-dir <attempt-dir>
    python3 scripts/engineering.py record <manifest> --review <review> --out <ledger>

render 只生成冻结输入和中性 reviewer 派发材料；check 只做机械身份和边界检查并输出 ENGINEERING_MECHANICAL_OK；run 只执行 manifest 中的本地 argv，使用 shell=False，保存独占 attempt 的 start.json、原始 stdout/stderr 和 receipt.json；record 只写候选 ledger 片段。

## 工件布局

默认项目工件根是：

    runs/<chain>/reviews/{A,B}/
    ├── dispatch-<round>.md
    ├── review-<round>.md
    ├── ledger.md
    ├── evidence/<round>/*
    ├── snapshot-*.txt
    └── subject-<round>/*

已经由 Git 保全的代码、spec、合同、派发、报告和 ledger 使用 commit；大型构建产物、外部数据和外部 CI 产物只记录 SHA256 和不可变来源。每个运行 attempt 必须使用不存在的目录，旧输出不可覆盖。

## Schema 和边界

公共 schema 是：

- agent-gates.eng-contract/v1
- agent-gates.eng-manifest/v1
- agent-gates.eng-review/v1
- agent-gates.eng-receipt/v1

对象角色全集为 authority、candidate、dependency、product、evidence。对象必须记录路径、SHA256、来源、保存策略和作用范围，合同、manifest、review、ledger 和 evidence 的身份可重建。

本 Skill 独立维护机械实现，不 import science-gates/scripts/science.py 或 workflow.py。references/source-provenance.json 记录参考来源和适配边界。当前版本不实现产品发布、部署或生产回滚，也不生成 SCI RPT 报告。

详细规则见：

- references/protocol-eng-v1.md
- references/project-setup.md
- references/workflow-schema-eng.md
- references/artifacts.md
