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

# F-15 (v2): with no configured identity, git may still commit using an auto-detected identity.
# Uses an already-tracked file so the outcome cannot be caused by F-16; the control run with -c user.* must succeed.
echo x >> b.txt
if env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -c commit.gpgsign=false commit -q -m c -- b.txt 2>/dev/null; then r=committed; else r=failed; fi
echo "F-15 INFO 作者：$(git log -1 --format='%an <%ae>')"
check F-15a "$r" "committed" "本机 git 在未配置身份时以自动推断的身份提交已跟踪文件"
cfg_name=$(env GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git config user.name || true)
check F-15 "$cfg_name" "" "未配置身份时 git config user.name 为空，须由命令自行检查，不能依赖 git 报错"
echo y >> b.txt
if g commit -q -m c2 -- b.txt 2>/dev/null; then r=committed; else r=failed; fi
check F-15c "$r" "committed" "对照：配置身份后同一操作成功"

# F-16: committing an untracked path via pathspec requires it to be added first
echo y > d.md
if g commit -q -m d -- d.md 2>/dev/null; then r=ok; else r=failed; fi
check F-16 "$r" "failed" "未跟踪文件不能直接用 commit -- <path> 提交，须先 add"

# F-17: git reset on a path fails while index.lock exists; control: succeeds after the lock is gone
cd "$T/repo"
echo n > n.txt && g add -- n.txt && touch .git/index.lock
if git reset -q -- n.txt 2>/dev/null; then r=ok; else r=failed; fi
check F-17 "$r" "failed" "index.lock 存在时 git reset -- <path> 失败"
rm .git/index.lock
if git reset -q -- n.txt 2>/dev/null; then r=ok; else r=failed; fi
check F-17c "$r" "ok" "对照：锁移除后 git reset 成功"

# F-18: GIT_AUTHOR_NAME overrides configured user.name; control: without it the configured name is used
echo m >> a.txt
env GIT_AUTHOR_NAME=envname git -c user.name=probe -c user.email=probe@example.invalid -c commit.gpgsign=false commit -q -m m -- a.txt
check F-18 "$(git log -1 --format=%an)" "envname" "GIT_AUTHOR_NAME 覆盖已配置的 user.name"
echo m2 >> a.txt
g commit -q -m m2 -- a.txt
check F-18c "$(git log -1 --format=%an)" "probe" "对照：不设环境变量时使用配置的身份"

# F-19: terminating a commit blocked in a slow pre-commit hook. SIGTERM to the process group leaves no index.lock;
# SIGKILL to git alone leaves index.lock behind. Requires python3 for process-group control.
H="$(git rev-parse --git-common-dir)/hooks"; mkdir -p "$H"
printf '#!/bin/sh\nsleep 6\n' > "$H/pre-commit"; chmod +x "$H/pre-commit"
for sig in TERM KILL; do
  echo "$sig" >> a.txt && g add -- a.txt
  python3 - "$sig" <<'PY'
import os, signal, subprocess, sys, time
sig = sys.argv[1]
p = subprocess.Popen(['git', '-c', 'user.name=probe', '-c', 'user.email=probe@example.invalid', '-c', 'commit.gpgsign=false',
                      'commit', '-q', '-m', 'slow', '--only', '--', 'a.txt'], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
if sig == 'TERM':
    os.killpg(p.pid, signal.SIGTERM)
else:
    p.send_signal(signal.SIGKILL)
p.wait()
time.sleep(0.5)
PY
  if [ -e .git/index.lock ]; then lock=left; else lock=clean; fi
  if [ "$sig" = TERM ]; then check F-19 "$lock" "clean" "超时后向进程组发 SIGTERM，不残留 index.lock"; else check F-19c "$lock" "left" "对照：只对 git 发 SIGKILL，残留 index.lock"; fi
  rm -f .git/index.lock .git/next-index-*.lock; git reset -q -- a.txt 2>/dev/null
done
rm -f "$H/pre-commit"

# F-20: author.name in config overrides user.name; control: without it user.name is used
cd "$T/repo"
echo z >> a.txt
g -c author.name=cfgauthor commit -q -m z -- a.txt
check F-20 "$(git log -1 --format=%an)" "cfgauthor" "author.name 配置覆盖 user.name"
echo z2 >> a.txt
g commit -q -m z2 -- a.txt
check F-20c "$(git log -1 --format=%an)" "probe" "对照：不设 author.name 时使用 user.name"

# F-21: a custom trailer is readable via git log trailers; control: absent trailer reads as empty
echo t >> a.txt
printf 'eg(record): - t\n\nEG-Kind: record\nEG-Spec: -\nEG-Run: 0123456789abcdef0123456789abcdef\n' > "$T/msg"
g commit -q -F "$T/msg" -- a.txt
check F-21 "$(git log -1 --format='%(trailers:key=EG-Run,valueonly)' | tr -d '\n')" "0123456789abcdef0123456789abcdef" "EG-Run trailer 可由 git log 读出"
check F-21c "$(git log -1 --skip=1 --format='%(trailers:key=EG-Run,valueonly)' | tr -d '\n')" "" "对照：不带该 trailer 的提交读出为空"

exit $fail
