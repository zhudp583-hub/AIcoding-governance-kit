#!/usr/bin/env python3
"""Append a short operations journal entry."""

from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="ops", choices=["ops", "infra", "prod", "research"])
    parser.add_argument("--journal")
    parser.add_argument("--item", action="append", required=True)
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--include-local-metadata", action="store_true")
    args = parser.parse_args()

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
