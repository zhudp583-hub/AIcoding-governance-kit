#!/bin/sh
set -eu

repo="${1:-.}"
repo="$(cd "$repo" && git rev-parse --show-toplevel)"
hook_dir="$repo/.git/hooks"
mkdir -p "$hook_dir"

src_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
source_hook="${AGK_PRE_COMMIT_TEMPLATE:-$src_root/git-hooks/pre-commit}"

if [ -f "$hook_dir/pre-commit" ] \
  && [ ! -f "$hook_dir/pre-commit.bak-agk" ] \
  && ! grep -q 'Agent Governance Kit' "$hook_dir/pre-commit" 2>/dev/null; then
  cp "$hook_dir/pre-commit" "$hook_dir/pre-commit.bak-agk"
fi

cp "$source_hook" "$hook_dir/pre-commit"
cp "$src_root/agk_common.py" "$hook_dir/agk_common.py"
cp "$src_root/git-hooks/agk_pre_commit.py" "$hook_dir/agk_pre_commit.py"
cp "$src_root/git-hooks/agk_repo_smoke.py" "$hook_dir/agk_repo_smoke.py"
chmod +x "$hook_dir/pre-commit" "$hook_dir/agk_pre_commit.py" "$hook_dir/agk_repo_smoke.py"

echo "installed Agent Governance Kit pre-commit hook in $hook_dir/pre-commit"
