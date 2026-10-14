# 更正：dispatch-impl-review-B1.md

`dispatch-impl-review-B1.md` 把受审 commit 写为 `fcf871a`，但冻结检查表 `checklist-impl.md` 与该派发文件本身提交于其后的 `93ccc09`，`fcf871a` 中不存在检查表。

更正：受审 commit 为 `93ccc09`。`fcf871a` 与 `93ccc09` 之间 `scripts/` 与 `tests/` 无差异（`git diff --stat fcf871a 93ccc09 -- scripts tests` 为空），只新增了检查表与派发文件。派发文件中其余内容不变；所有"在副本中"的操作改为基于 `93ccc09` 建立副本。
