# Engineering Gates Protocol v1

## 1. 范围和状态

本协议定义工程开发流程的核心两门。门 A 冻结工程合同；门 B 在冻结合同上审查实现和可观察证据。两门都可有 baseline 和 closure 两轮。默认预算是一轮 Baseline 加一轮 Closure；预算内仍存在 BLOCKER 或 MAJOR 时，状态为 NON_CONVERGENT，停止继续自动推进。

PASS 只表示项目 reviewer 根据实际证据作出的工程审查结论。CLI 的 check 是机械检查，输出 ENGINEERING_MECHANICAL_OK；record 只生成候选 ledger 片段，输出 ENGINEERING_CANDIDATE_PASS 或候选阻塞状态。任何工程状态都不能转写成 SCI RPT 报告或 scientific_pass。

## 2. Gate A：工程合同审查

Gate A 输入是上游需求、设计、决策、工作区政策、依赖身份和项目 profile。输出是带固定身份的 agent-gates.eng-contract/v1 合同、可重建对象清单和中性派发材料。

| ID | 必须回答 |
| --- | --- |
| A1 | 每条决策和需求落到了哪个行为、接口或验收？ |
| A2 | 外部事实、工作区政策和依赖版本的固定锚是什么？ |
| A3 | 哪些语义或参数仍未决，Decision Owner 是谁？ |
| A4 | 每项行为和禁止事项的验收能否击败一个错误实现？ |
| A5 | 输入、输出、写入面、no-clobber 和禁写范围是否完整？ |
| A6 | 术语、路径、版本、状态和依赖是否一致？ |
| A7 | 外部事实是否绑定不可移动的 commit、tag 或精确版本，漂移后的停止动作是否写明？ |
| A8 | 多份上游、跨文件撤销和审查期新增决定是否有唯一状态来源？ |
| A9 | 对既有 spec、公共 API 或兄弟合同的触碰是否登记影响和迁移方式？ |

A3 未决语义必须进入 Decision Owner 队列，不得由 Agent 或 CLI 静默填补。A7 的锚点漂移时停止并重新核验，不得默认更新到最新版本。A8 的唯一状态来源必须能重建冲突解决顺序。A9 的兼容边界必须在合同和迁移说明中同时出现。

Gate A PASS 后，合同、上游对象和合同身份冻结。影响行为的修改必须创建新版本并重新进入 Gate A。

## 3. Gate B：实现验证审查

Gate B 输入是冻结合同、manifest、代码、构建和测试输出。实现行为使用“可观察证据”语义：代码、日志、测试结果、receipt 和保存的输出必须能共同支持文字声明。

| ID | 必须回答 |
| --- | --- |
| B1 | 实现是否逐条符合冻结合同？ |
| B2 | 测试、构建和验收证据是否真实覆盖要求，断言是否能击败错误实现？ |
| B3 | 实现行为文字声明是否与代码、日志、测试和 receipt 一致？ |
| B4 | 上下游 API、schema、错误词表、状态和兼容语义是否一致？ |
| B5 | 成功、失败、取消、超时、崩溃、恢复、重放、并发、释放、分类和重试路径是否闭合？ |
| B6 | 已声明的权限、资源、并发和输出上限是否在真实执行点读取并强制？ |
| B7 | 证据是否确定：attempt 独立保存、首次失败不被覆盖、没有 rerun-until-green 掩盖 flaky 测试？ |

B7 要求每一次执行都有独占 attempt 目录；run 不能覆盖既有 stdout、stderr、start 或 receipt。非零退出、信号退出和缺失产物都必须进入 receipt，并阻止候选 PASS。

## 4. 角色、对象和证据

对象角色只允许：authority、candidate、dependency、product、evidence。对象至少有 id、role、path、sha256、source、preservation 和 scope。authority 提供冻结约束；candidate 是待审代码或 spec；dependency 是固定外部版本；product 是实现或生成物；evidence 是测试、receipt、日志、snapshot 或外部 CI 记录。

路径必须落在项目 root 和声明的写入面内。符号链接不得逃逸到 root；.git、..、绝对路径和 forbidden path 不得作为项目输入或输出。大型外部产物不强制入库，但要保存 SHA256 和不可变来源。

## 5. Findings 和预算

Finding 至少包含 id、severity、status、owner 和 message。严重度为 BLOCKER、MAJOR、MINOR、OPINION。BLOCKER / MAJOR 阻止 PASS；MINOR / OPINION 需要 owner 和后续计划，但不阻止 PASS。NEEDS_USER_DECISION 是独立的阻塞状态，必须保留问题和 Decision Owner。

Closure 只复核上一轮 finding、实际修改和必要直接依赖。不能在 Closure 随意扩展为完整 Baseline。若预算用尽仍有阻塞项，候选状态为 NON_CONVERGENT，停止并把剩余 finding 保存为可重建证据。

## 6. 失败与恢复

所有写入动作必须先进行身份和路径检查；目标已经存在时失败，不清空、不覆盖、不合并。run 只能执行 manifest 中的本地 argv，禁止隐式 shell、远程主机和未列出的命令。进程终止、超时或崩溃仍保存开始时间、原始输出和 receipt；恢复通过新的 attempt 完成，旧 attempt 保留。

协议预留 release 和 recovery gate 的 schema 扩展位，但 v1 不定义产品发布、部署、回滚和生产操作。
