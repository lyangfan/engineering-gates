# Project setup

项目接入时创建一个 project profile，并把它作为 Gate A 的 authority。下面是最小字段和默认值：

    schema: agent-gates.eng-project/v1
    project_root: /absolute/path/to/project
    chain: product-change-001
    artifact_root: runs/product-change-001/reviews
    allowed_hosts: [local]
    write_roots:
      - runs/product-change-001/reviews
    forbidden_paths:
      - .git
      - production
    decision_owner: team-lead
    reviewer: reviewer-id

artifact_root 默认等于 runs/<chain>/reviews，门 A 和门 B 分别写入其 A、B 子目录。项目可以声明额外的 required_paths，但必须使用项目 root 下的相对路径。

steps 中每个执行项必须写出完整 argv、相对 cwd、本地 host、输入对象和预期输出对象。不要把 shell pipeline、重定向或远程命令塞进一个字符串；需要多个动作时声明多个 step。run 不会使用项目外的环境变量来隐式补齐命令，也不会根据最新分支自动替换依赖版本。

项目 profile 可以登记构建工具、测试入口、CI workflow 和固定依赖 commit。外部事实变化或 profile 行为变化时新建 contract 版本并重新走 Gate A。发布、部署和生产回滚不属于本版 profile。
