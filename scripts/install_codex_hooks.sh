#!/bin/sh
set -eu

src_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
dest_root="${AGK_CODEX_HOME:-$HOME/.codex/agent-governance-kit}"

mkdir -p "$dest_root/hooks" "$dest_root/git-hooks"
cp "$src_root/hooks/agent_governance_hook.py" "$dest_root/hooks/agent_governance_hook.py"
cp "$src_root/git-hooks/pre-commit" "$dest_root/git-hooks/pre-commit"
cp "$src_root/git-hooks/agk_pre_commit.py" "$dest_root/git-hooks/agk_pre_commit.py"
cp "$src_root/git-hooks/agk_repo_smoke.py" "$dest_root/git-hooks/agk_repo_smoke.py"
chmod +x "$dest_root/hooks/agent_governance_hook.py"
chmod +x "$dest_root/git-hooks/pre-commit" "$dest_root/git-hooks/agk_pre_commit.py" "$dest_root/git-hooks/agk_repo_smoke.py"

mkdir -p "$HOME/.codex"
if [ -f "$HOME/.codex/hooks.json" ] && [ ! -f "$HOME/.codex/hooks.json.bak-agk" ]; then
  cp "$HOME/.codex/hooks.json" "$HOME/.codex/hooks.json.bak-agk"
fi
cp "$src_root/hooks/hooks.json" "$HOME/.codex/hooks.json"

config="$HOME/.codex/config.toml"
if [ ! -f "$config" ]; then
  printf '[features]\nhooks = true\n' > "$config"
elif grep -q 'hooks = true' "$config"; then
  :
elif grep -q '^\[features\]' "$config"; then
  echo "Codex config already has a [features] table. Add 'hooks = true' there if it is not enabled."
else
  printf '\n[features]\nhooks = true\n' >> "$config"
fi

echo "installed Agent Governance Kit Codex hooks in $dest_root"
