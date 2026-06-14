#!/usr/bin/env python3
"""Append a short operations journal entry."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from pathlib import Path


def git_value(args: list[str], cwd: str) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=cwd, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "n/a"


def default_journal(domain: str, cwd: str) -> Path:
    today = time.strftime("%Y-%m-%d", time.gmtime())
    configured = os.environ.get("AGK_DEFAULT_JOURNAL")
    if configured:
        return Path(configured).expanduser()
    return Path(cwd) / "worklog" / f"{today}-{domain}.md"


def closeout_marker(session_id: str) -> str:
    return f"AGK-Session: {session_id or 'unknown'}"


def discover_session_id() -> str:
    configured = os.environ.get("AGK_SESSION_ID")
    if configured:
        return configured
    state_dir = Path(os.environ.get("AGK_STATE_DIR", "~/.codex/agent-governance-kit/state")).expanduser()
    try:
        candidates = [path for path in state_dir.glob("*.json") if path.is_file()]
    except OSError:
        return "unknown"
    if not candidates:
        return "unknown"
    latest = max(candidates, key=lambda path: path.stat().st_mtime)
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "unknown"
    return str(data.get("session_id") or "unknown")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="ops", choices=["ops", "infra", "prod", "research"])
    parser.add_argument("--journal")
    parser.add_argument("--item", action="append", required=True)
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--session-id")
    parser.add_argument("--include-local-metadata", action="store_true")
    args = parser.parse_args()

    session_id = args.session_id or discover_session_id()
    path = Path(args.journal).expanduser() if args.journal else default_journal(args.domain, args.cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    root = git_value(["rev-parse", "--show-toplevel"], args.cwd)
    branch = git_value(["branch", "--show-current"], args.cwd)
    head = git_value(["rev-parse", "--short", "HEAD"], args.cwd)
    include_local = args.include_local_metadata or os.environ.get("AGK_JOURNAL_INCLUDE_LOCAL") == "1"
    host = socket.gethostname() if include_local else "redacted"
    cwd = args.cwd if include_local else "redacted"

    lines = [
        f"\n## {ts} - Agent Closeout",
        "",
        f"- Host: `{host}`",
        f"- CWD: `{cwd}`",
        f"- Domain: `{args.domain}`",
        f"- Git root: `{root}`",
        f"- Branch: `{branch}`",
        f"- HEAD: `{head}`",
        f"- {closeout_marker(session_id)}",
        "- Items:",
    ]
    lines.extend(f"  - {item}" for item in args.item)
    lines.append("")
    with path.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
