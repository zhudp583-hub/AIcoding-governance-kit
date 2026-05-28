#!/usr/bin/env python3
"""Codex lifecycle hook for agent governance and closeout discipline."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


STATE_ROOT = Path(os.environ.get("AGK_STATE_DIR", "~/.codex/agent-governance-kit/state")).expanduser()
EVENT_LOG = STATE_ROOT.parent / "events.jsonl"
MODE = os.environ.get("AGK_HOOK_MODE", "enforce").lower()
RESEARCH_DIRTY_GRACE_HOURS = float(os.environ.get("AGK_RESEARCH_DIRTY_GRACE_HOURS", "24"))
RESEARCH_GRACE_ROOTS = {item for item in os.environ.get("AGK_RESEARCH_GRACE_ROOTS", "").split(":") if item}
RESEARCH_GRACE_PREFIXES = tuple(
    item
    for item in os.environ.get(
        "AGK_RESEARCH_GRACE_PREFIXES",
        "docs/research/:experiments/:analysis/",
    ).split(":")
    if item
)
JOURNAL_DIRS = tuple(
    item
    for item in os.environ.get(
        "AGK_JOURNAL_DIRS",
        "worklog:docs:manifests",
    ).split(":")
    if item
)
PROTECTED_PATH_MARKERS = tuple(
    item
    for item in os.environ.get(
        "AGK_PROTECTED_PATHS",
        ".env:.ssh/:auth.json:models/:data/:logs/:tmp/:exports/:research_eval/",
    ).split(":")
    if item
)

MATERIAL_COMMAND_PATTERNS = [
    r"\b(apply_patch|cat\s+>|tee\s+|sed\s+-i|perl\s+-pi)\b",
    r"\b(git\s+add|git\s+commit|git\s+push|git\s+rm|git\s+mv)\b",
    r"\b(systemctl\s+(restart|stop|disable|enable|daemon-reload))\b",
    r"\b(crontab\s+|docker\s+(restart|stop|compose\s+down|compose\s+up))\b",
    r"\b(rm\s+|mv\s+|cp\s+|rsync\s+|scp\s+)\b",
    r"\b(psql|pg_dump|VACUUM|DROP\s+TABLE|TRUNCATE|DELETE\s+FROM)\b",
]

PROTECTED_ARTIFACT_SUFFIXES = (
    ".pt",
    ".pkl",
    ".bin",
    ".npz",
    ".parquet",
    ".sqlite",
    ".db",
    ".dump",
    ".csv.gz",
    ".jsonl.gz",
    ".log",
)

PROTECTED_DIR_NAMES = frozenset(
    marker.strip("/").lower()
    for marker in PROTECTED_PATH_MARKERS
    if marker.endswith("/") and marker.strip("/")
)
PROTECTED_FILE_NAMES = frozenset(
    marker.lower()
    for marker in PROTECTED_PATH_MARKERS
    if marker and not marker.endswith("/") and "/" not in marker and marker != ".env"
)

SHELL_SEPARATORS_RE = re.compile(r"(?:&&|\|\||;|\n)")
REDIRECT_RE = re.compile(r"(?:^|[\s;&|])(?:[0-9]?>|[0-9]?>>|&>)\s*(['\"]?)([^'\"\s;&|]+)\1")


def run(cmd: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=10)


def now() -> float:
    return time.time()


def load_input() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def state_path(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", session_id or "unknown")
    return STATE_ROOT / f"{safe}.json"


def load_state(session_id: str) -> dict[str, Any]:
    path = state_path(session_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {"session_id": session_id, "started_at": now(), "material": False, "events": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    state_path(state.get("session_id", "unknown")).write_text(json.dumps(state, indent=2, sort_keys=True))


def append_event(payload: dict[str, Any]) -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    payload = dict(payload)
    payload.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with EVENT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def git_root(cwd: str) -> str | None:
    result = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    return result.stdout.strip() if result.returncode == 0 else None


def git_head(root: str) -> str | None:
    result = run(["git", "rev-parse", "HEAD"], cwd=root)
    return result.stdout.strip() if result.returncode == 0 else None


def git_dirty_paths(root: str) -> list[str]:
    result = run(["git", "status", "--porcelain"], cwd=root)
    if result.returncode != 0:
        return []
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path:
            paths.append(path)
    return paths


def git_last_commit_ts(root: str) -> float:
    result = run(["git", "log", "-1", "--format=%ct"], cwd=root)
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def path_mtime(root: str, relpath: str) -> float | None:
    try:
        return (Path(root) / relpath).stat().st_mtime
    except FileNotFoundError:
        return None


def research_dirty_allowed(root: str | None, paths: list[str]) -> tuple[bool, str]:
    if not root or root not in RESEARCH_GRACE_ROOTS or not paths:
        return False, "not a configured research grace root"
    disallowed = [path for path in paths if not path.startswith(RESEARCH_GRACE_PREFIXES)]
    if disallowed:
        return False, "dirty paths outside research grace: " + ", ".join(disallowed[:5])
    mtimes = [path_mtime(root, path) for path in paths]
    if any(item is None for item in mtimes):
        return False, "dirty path missing on disk; commit or document deletion explicitly"
    oldest_age_hours = (now() - min(item for item in mtimes if item is not None)) / 3600
    if oldest_age_hours > RESEARCH_DIRTY_GRACE_HOURS:
        return False, f"research dirty age {oldest_age_hours:.1f}h exceeds {RESEARCH_DIRTY_GRACE_HOURS:.1f}h grace"
    return True, f"research dirty within {RESEARCH_DIRTY_GRACE_HOURS:.1f}h grace"


def journal_dirs(cwd: str, root: str | None) -> list[Path]:
    candidates: list[Path] = []
    for raw in JOURNAL_DIRS:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            if root:
                candidates.append(Path(root) / path)
            candidates.append(Path(cwd) / path)
        else:
            candidates.append(path)
    seen: set[str] = set()
    out: list[Path] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        try:
            exists = path.exists()
        except PermissionError:
            continue
        if exists:
            seen.add(key)
            out.append(path)
    return out


def mtime_after(path: Path, threshold: float) -> bool:
    try:
        if path.is_file():
            return path.stat().st_mtime >= threshold
    except PermissionError:
        return False
    try:
        children = path.rglob("*")
    except PermissionError:
        return False
    for child in children:
        if child.is_file() and child.suffix.lower() in {".md", ".json", ".jsonl", ".yaml", ".yml", ".toml"}:
            try:
                if child.stat().st_mtime >= threshold:
                    return True
            except (FileNotFoundError, PermissionError):
                continue
    return False


def has_closeout_evidence(cwd: str, started_at: float) -> tuple[bool, str]:
    root = git_root(cwd)
    if root and git_last_commit_ts(root) >= started_at:
        return True, f"git commit after session start in {root}"
    for directory in journal_dirs(cwd, root):
        if mtime_after(directory, started_at):
            return True, f"journal/manifest updated under {directory}"
    return False, "no post-session journal, manifest, or commit evidence found"


def command_text(event: dict[str, Any]) -> str:
    tool_input = event.get("tool_input") or {}
    if isinstance(tool_input, dict):
        return str(tool_input.get("command") or tool_input.get("cmd") or "")
    return str(tool_input)


def is_material_command(command: str) -> bool:
    return any(re.search(pattern, command, re.IGNORECASE) for pattern in MATERIAL_COMMAND_PATTERNS)


def command_segments(command: str) -> list[list[str]]:
    segments: list[list[str]] = []
    for chunk in SHELL_SEPARATORS_RE.split(command):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            words = shlex.split(chunk, posix=True)
        except ValueError:
            continue
        if words:
            segments.append(words)
    return segments


def command_name_and_args(words: list[str]) -> tuple[str, list[str]]:
    index = 0
    while index < len(words) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[index]):
        index += 1
    while index < len(words) and words[index] in {"sudo", "command"}:
        index += 1
    if index < len(words) and words[index] == "env":
        index += 1
        while index < len(words):
            word = words[index]
            if word == "--":
                index += 1
                break
            if word.startswith("-") or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word):
                index += 1
                continue
            break
    if index >= len(words):
        return "", []
    return words[index], words[index + 1 :]


def rm_recursive_force_root(args: list[str]) -> bool:
    recursive = False
    force = False
    targets: list[str] = []
    after_options = False
    for arg in args:
        if not after_options and arg == "--":
            after_options = True
            continue
        if not after_options and arg.startswith("-") and arg != "-":
            opts = arg.lstrip("-")
            recursive = recursive or "r" in opts or "R" in opts or arg == "--recursive"
            force = force or "f" in opts or arg == "--force"
            continue
        targets.append(arg)
    return recursive and force and any(target == "/" or target.startswith("/*") for target in targets)


def docker_prune_all(args: list[str]) -> bool:
    if len(args) < 2 or args[0] != "system" or args[1] != "prune":
        return False
    for arg in args[2:]:
        if arg in {"-a", "--all"}:
            return True
        if arg.startswith("-") and not arg.startswith("--") and "a" in arg.lstrip("-"):
            return True
    return False


def block_reason(command: str) -> str | None:
    if os.environ.get("AGK_APPROVED") == "1":
        return None
    for words in command_segments(command):
        executable, args = command_name_and_args(words)
        executable = Path(executable).name
        if executable == "rm" and rm_recursive_force_root(args):
            return "Refusing recursive force remove of filesystem root"
        if executable == "git" and args[:1] == ["reset"] and "--hard" in args:
            return "git reset --hard requires explicit human-run approval"
        if executable == "git" and args[:1] == ["checkout"] and "--" in args:
            return "git checkout -- can discard user work"
        if executable == "docker" and docker_prune_all(args):
            return "docker system prune --all is too broad for an agent hook"
    return None


def normalized_path_parts(path: str) -> tuple[list[str], str]:
    normalized = path.replace("\\", "/").strip()
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    basename = parts[-1].lower() if parts else ""
    return [part.lower() for part in parts], basename


def protected_path(path: str) -> bool:
    parts, basename = normalized_path_parts(path)
    if not basename:
        return False
    if basename == ".env" or basename.startswith(".env."):
        return True
    if basename in PROTECTED_FILE_NAMES:
        return True
    if any(part in PROTECTED_DIR_NAMES for part in parts):
        return True
    return basename.endswith(PROTECTED_ARTIFACT_SUFFIXES)


def bash_touches_protected(command: str) -> str | None:
    if os.environ.get("AGK_ALLOW_PROTECTED") == "1":
        return None
    for match in REDIRECT_RE.finditer(command):
        path = match.group(2)
        if protected_path(path):
            return f"shell redirection touches protected artifact path: {path}"
    for words in command_segments(command):
        executable, args = command_name_and_args(words)
        executable = Path(executable).name
        if executable in {"tee", "touch", "mkdir", "cp", "mv", "rm", "sed", "perl"}:
            for arg in args:
                if arg.startswith("-"):
                    continue
                if protected_path(arg):
                    return f"shell command touches protected artifact path: {arg}"
    return None


def patch_touches_protected(event: dict[str, Any]) -> str | None:
    if event.get("tool_name") != "apply_patch":
        return None
    if os.environ.get("AGK_ALLOW_PROTECTED") == "1":
        return None
    text = command_text(event)
    for line in text.splitlines():
        if line.startswith(("*** Add File: ", "*** Update File: ", "*** Delete File: ")):
            path = line.split(": ", 1)[1].strip()
            if protected_path(path):
                return f"apply_patch touches protected artifact path: {path}"
    return None


def json_out(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj))


def block_pretool(reason: str) -> None:
    json_out(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def stop_continue(reason: str) -> None:
    if MODE == "warn":
        json_out({"systemMessage": f"Agent Governance Kit closeout warning: {reason}"})
        return
    json_out({"decision": "block", "reason": reason})


def self_test() -> int:
    sample = {
        "session_id": "self-test",
        "cwd": os.getcwd(),
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "git status --short"},
    }
    assert command_text(sample) == "git status --short"
    assert not block_reason("git status --short")
    assert block_reason("git reset --hard")
    assert is_material_command("git commit -m test")
    print("agent_governance_hook.py self-test OK")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    event = load_input()
    hook_event = event.get("hook_event_name", "")
    session_id = event.get("session_id") or "unknown"
    cwd = event.get("cwd") or os.getcwd()
    state = load_state(session_id)
    state.setdefault("started_at", now())
    state.setdefault("events", [])

    append_event(
        {
            "session_id": session_id,
            "event": hook_event,
            "cwd": cwd,
            "tool": event.get("tool_name"),
            "turn_id": event.get("turn_id"),
        }
    )

    if hook_event == "SessionStart":
        root = git_root(cwd)
        state.update(
            {
                "started_at": now(),
                "cwd": cwd,
                "git_root": root,
                "git_head_start": git_head(root) if root else None,
                "material": False,
            }
        )
        save_state(state)
        json_out(
            {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        "Agent Governance Kit is active. For material changes, finish with "
                        "a journal/manifest update or Git commit before final response."
                    ),
                }
            }
        )
        return 0

    if hook_event == "UserPromptSubmit":
        prompt = str(event.get("prompt") or "")
        if re.search(r"(closeout|deploy|remove|delete|commit|push|ops|audit|journal|manifest|cleanup)", prompt, re.IGNORECASE):
            json_out(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": (
                            "If this turn changes files, services, data, or runtime state, "
                            "update the correct work journal/manifest and close Git state before final."
                        ),
                    }
                }
            )
        return 0

    if hook_event == "PreToolUse":
        command = command_text(event)
        reason = block_reason(command) or patch_touches_protected(event)
        if not reason and event.get("tool_name") == "Bash":
            reason = bash_touches_protected(command)
        if reason:
            block_pretool(reason)
            return 0
        return 0

    if hook_event == "PostToolUse":
        command = command_text(event)
        if event.get("tool_name") in {"apply_patch", "Edit", "Write"} or is_material_command(command):
            state["material"] = True
            state["last_material_at"] = now()
            state.setdefault("material_events", []).append(
                {"event": event.get("tool_name"), "command": command[:240], "ts": now()}
            )
        save_state(state)
        return 0

    if hook_event == "Stop":
        if event.get("stop_hook_active"):
            json_out({"continue": True})
            return 0
        if not state.get("material"):
            json_out({"continue": True})
            return 0
        started_at = float(state.get("started_at") or now())
        evidence_ok, evidence = has_closeout_evidence(cwd, started_at)
        root = git_root(cwd)
        dirty_paths = git_dirty_paths(root) if root else []
        dirty = bool(dirty_paths)
        research_dirty_ok, research_dirty_reason = research_dirty_allowed(root, dirty_paths)
        if evidence_ok and (not dirty or research_dirty_ok):
            json_out({"continue": True})
            return 0
        problems = []
        if dirty and not research_dirty_ok:
            problems.append(f"dirty worktree remains in {root}")
        elif dirty:
            problems.append(f"{research_dirty_reason}, but closeout evidence is still required")
        if not evidence_ok:
            problems.append(evidence)
        stop_continue(
            "Material agent work was detected but closeout is incomplete: "
            + "; ".join(problems)
            + ". Update the work journal/manifest and commit or explicitly document residual dirty state."
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
