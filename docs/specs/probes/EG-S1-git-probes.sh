#!/bin/sh
# EG-S1 现实核验探针：在临时仓库中实测 git 行为。只写 mktemp 创建的目录。
# 每个探针输出一行 "F-xx PASS|FAIL <说明>"；任一 FAIL 时退出码为 1。
set -u
git --version
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
cd "$T" || exit 2
fail=0
check() { if [ "$2" = "$3" ]; then echo "$1 PASS $4"; else echo "$1 FAIL $4 (got [$2], want [$3])"; fail=1; fi; }
g() { git -c user.name=probe -c user.email=probe@example.invalid -c commit.gpgsign=false "$@"; }

g init -q -b main repo && cd repo
echo base > a.txt && echo base > b.txt && g add . && g commit -q -m base

# F-11: worktree on a new branch leaves the main worktree's branch and files untouched
g worktree add -q -b eg/flow ../flow
check F-11 "$(git branch --show-current):$(cat a.txt)" "main:base" "worktree add -b 不改变主工作区的分支与文件"

# F-12: add + commit --only <path> commits only those paths, even when other changes are staged
cd ../flow
echo spec > spec.md && echo user-wip >> a.txt && g add a.txt
g add -- spec.md && g commit -q -m checkpoint --only -- spec.md
check F-12 "$(git show --name-only --format= HEAD)" "spec.md" "add 后 commit --only -- <path> 只提交指定路径"
check F-12b "$(git diff --cached --name-only)" "a.txt" "其他已暂存改动仍留在暂存区"

# F-13: bytes read back from a commit equal the working file bytes
check F-13 "$(git show HEAD:spec.md | shasum -a 256 | cut -d' ' -f1)" "$(shasum -a 256 spec.md | cut -d' ' -f1)" "git show <commit>:<path> 字节与文件一致"

# F-14: a pre-commit hook can abort the commit; --no-verify skips it
mkdir -p "$(git rev-parse --git-common-dir)/hooks"
printf '#!/bin/sh\nexit 1\n' > "$(git rev-parse --git-common-dir)/hooks/pre-commit" && chmod +x "$(git rev-parse --git-common-dir)/hooks/pre-commit"
echo r1 > review.md && g add -- review.md
if g commit -q -m r --only -- review.md 2>/dev/null; then r=committed; else r=aborted; fi
check F-14 "$r" "aborted" "pre-commit 钩子可中止提交"
if g commit -q --no-verify -m r --only -- review.md 2>/dev/null; then r=committed; else r=aborted; fi
check F-14b "$r" "committed" "--no-verify 跳过钩子"
rm "$(git rev-parse --git-common-dir)/hooks/pre-commit"

# F-15: without user identity, commit fails (simulates CI); -c user.* fixes it
echo x > c.md
if env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null HOME="$T" git -c commit.gpgsign=false commit -q -m c -- c.md 2>/dev/null; then r=ok; else r=failed; fi
check F-15 "$r" "failed" "无 user.name/email 时提交失败"

# F-16: committing an untracked path via pathspec requires it to be added first
echo y > d.md
if g commit -q -m d -- d.md 2>/dev/null; then r=ok; else r=failed; fi
check F-16 "$r" "failed" "未跟踪文件不能直接用 commit -- <path> 提交，须先 add"

exit $fail
