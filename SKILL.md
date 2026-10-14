---
name: engineering-gates
description: "工程 spec、实现验证与可追溯证据 gates；用于把需求和设计冻结为可验证工程合同，并审查代码、构建、测试及工程证据是否符合合同。"
---

# Engineering Gates

当任务需要把工程需求、设计决定或上游约束变成可审查的工程合同，或需要根据冻结合同审查实现时，使用本 Skill。它只覆盖工程语义，不产生 SCI 的 RPT 报告，也不使用 scientific_pass。

首版有两道门：

- 门 A：工程合同审查。把需求、设计和决定逐条落到 agent-gates.eng-contract/v1，固定输入、输出、写入面、错误语义、验收和未决决定。
- 门 B：实现验证审查。以冻结合同为输入，核对代码、构建、测试、运行 receipt 和其他工程证据，使用 agent-gates.eng-manifest/v1、agent-gates.eng-review/v1 和 agent-gates.eng-receipt/v1。

机械检查成功时，CLI 输出 ENGINEERING_MECHANICAL_OK。审查工具最多产生候选 ledger 片段（ENGINEERING_CANDIDATE_PASS 或候选阻塞状态）；正式 Engineering PASS 必须由项目规定的 reviewer 根据实际证据登记，不能由 CLI 自动宣布。

默认通过以下入口使用：

    python3 scripts/engineering.py render <manifest.json> --out runs/demo/reviews/A/dispatch-001.md
    python3 scripts/engineering.py check <manifest.json>
    python3 scripts/engineering.py run <manifest.json> --step build --receipt-dir runs/demo/reviews/B/evidence/001/build
    python3 scripts/engineering.py record <manifest.json> --review runs/demo/reviews/B/review-001.json --out runs/demo/reviews/B/ledger.md

先阅读 references/protocol-eng-v1.md 和 references/workflow-schema-eng.md，再根据项目的 project-setup.md 生成或审核 manifest。除非项目显式扩展，默认工件根为 runs/<chain>/reviews/{A,B}，运行只执行 manifest 明确列出的本地 argv，且不会覆盖已有 attempt。

## 交付边界

本 Skill 不默认 SSH、远程作业、发布、部署、生产回滚或产品 Release gate。它为后续 Release/Recovery gates 预留协议扩展位置，但 v1 只实现核心两门。
