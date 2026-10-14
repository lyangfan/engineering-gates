# Validation record

本目录保存公开仓库发布前的本地验证摘要。它是发布证据索引，不是工程 PASS，也不替代项目 reviewer 的 Gate A/B 审查。

验证入口：

    python3 /Users/liuyangfan/.codex/skills/.system/skill-creator/scripts/quick_validate.py /Users/liuyangfan/Documents/work/engineering-gates
    python3 -B -m unittest discover -s /Users/liuyangfan/Documents/work/engineering-gates/scripts/tests -p 'test_*.py' -v

summary.json 由维护者在一次验证运行后更新，包含命令、解释器、测试计数、时间和 Git HEAD。CI 使用同样的 validator 和 unittest 入口。
