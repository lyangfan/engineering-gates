# Artifact conventions

默认工件根为 runs/<chain>/reviews/{A,B}。每门每轮保存：

    dispatch-<round>.md
    review-<round>.md
    ledger.md
    evidence/<round>/*
    snapshot-*.txt
    subject-<round>/*

subject-<round> 只保存尚未由 Git 保全的候选字节。已由 Git 保全的代码、spec、合同、派发、报告和 ledger 使用 commit 作为身份；大型构建产物、外部数据和外部 CI 产物保存 SHA256、来源 URL 或 CI run ID 以及固定版本。

run 为每个 step 使用独占 attempt 目录，至少包含：

    start.json
    stdout.bin
    stderr.bin
    receipt.json

如果 manifest 声明输出，receipt 还记录每个输出的相对路径、存在性和 SHA256。目录已存在时命令失败，旧 attempt 永不覆盖。失败的原始 stdout/stderr 和非零退出码必须保留，不能用后续绿色重跑替换。

ledger 是候选审查记录。它引用 manifest、contract、review 和 receipt 的 SHA256，记录 finding、owner、状态、预算和 scope。工具生成的是候选片段；项目 reviewer 负责正式登记工程 PASS。
