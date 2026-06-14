#!/bin/sh
set -eu

src_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
dest_root="${AGK_INSTALL_ROOT:-${AGK_CODEX_HOME:-$codex_home/agent-governance-kit}}"

mkdir -p "$dest_root/hooks" "$dest_root/git-hooks"
cp "$src_root/agk_common.py" "$dest_root/agk_common.py"
cp "$src_root/hooks/agent_governance_hook.py" "$dest_root/hooks/agent_governance_hook.py"
cp "$src_root/git-hooks/pre-commit" "$dest_root/git-hooks/pre-commit"
cp "$src_root/git-hooks/agk_pre_commit.py" "$dest_root/git-hooks/agk_pre_commit.py"
cp "$src_root/git-hooks/agk_repo_smoke.py" "$dest_root/git-hooks/agk_repo_smoke.py"
chmod +x "$dest_root/hooks/agent_governance_hook.py"
chmod +x "$dest_root/git-hooks/pre-commit" "$dest_root/git-hooks/agk_pre_commit.py" "$dest_root/git-hooks/agk_repo_smoke.py"

mkdir -p "$codex_home"
hooks_file="$codex_home/hooks.json"
if [ -f "$hooks_file" ] && [ ! -f "$hooks_file.bak-agk" ]; then
  cp "$hooks_file" "$hooks_file.bak-agk"
fi

python3 - "$hooks_file" "$src_root/hooks/hooks.json" "$dest_root" <<'PY'
import json
import sys
from pathlib import Path

hooks_file = Path(sys.argv[1])
template_file = Path(sys.argv[2])
install_root = sys.argv[3]
placeholder = "${AGK_INSTALL_ROOT:-$HOME/.codex/agent-governance-kit}"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid existing hooks JSON at {path}: {exc}") from exc


def replace_install_root(value):
    if isinstance(value, str):
        return value.replace(placeholder, install_root)
    if isinstance(value, list):
        return [replace_install_root(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_install_root(item) for key, item in value.items()}
    return value


def is_agk_group(group: dict) -> bool:
    return any(
        "agent_governance_hook.py" in str(hook.get("command", ""))
        for hook in group.get("hooks", [])
        if isinstance(hook, dict)
    )


existing = load_json(hooks_file)
incoming = replace_install_root(load_json(template_file))
existing_hooks = existing.setdefault("hooks", {})
for event, groups in incoming.get("hooks", {}).items():
    current = existing_hooks.setdefault(event, [])
    current[:] = [group for group in current if not (isinstance(group, dict) and is_agk_group(group))]
    current.extend(groups)

hooks_file.write_text(json.dumps(existing, indent=2, sort_keys=False) + "\n", encoding="utf-8")
PY

config="$codex_home/config.toml"
if [ ! -f "$config" ]; then
  printf '[features]\nhooks = true\n' > "$config"
else
  python3 - "$config" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
features_start = None
features_end = len(lines)
for index, line in enumerate(lines):
    if re.match(r"^\s*\[features\]\s*$", line):
        features_start = index
        continue
    if features_start is not None and index > features_start and re.match(r"^\s*\[.*\]\s*$", line):
        features_end = index
        break

if features_start is None:
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend(["[features]", "hooks = true"])
else:
    replaced = False
    for index in range(features_start + 1, features_end):
        if re.match(r"^\s*hooks\s*=", lines[index]):
            lines[index] = "hooks = true"
            replaced = True
            break
    if not replaced:
        lines.insert(features_start + 1, "hooks = true")

path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi

echo "installed Agent Governance Kit Codex hooks in $dest_root and merged $hooks_file"
