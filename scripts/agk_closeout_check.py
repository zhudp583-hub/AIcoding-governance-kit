#!/usr/bin/env python3
"""Check closeout state for a Git repo."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROTECTED_PATH_MARKERS = tuple(
    item
    for item in os.environ.get(
        "AGK_PROTECTED_PATHS",
        ".env:.ssh/:auth.json:models/:data/:logs/:tmp/:exports/:research_eval/",
    ).split(":")
    if item
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
PROTECTED_SUFFIXES = (
    ".pt",
    ".pkl",
    ".bin",
    ".npz",
    ".parquet",
    ".dump",
    ".sqlite",
    ".db",
    ".log",
    ".csv.gz",
    ".jsonl.gz",
)


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


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
    return basename.endswith(PROTECTED_SUFFIXES)


def status_path(line: str) -> str:
    path = line[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    if len(path) >= 2 and path[0] == path[-1] == '"':
        path = path[1:-1]
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    repo = str(Path(args.repo).resolve())
    status = run(["git", "status", "--porcelain"], repo)
    if status.returncode != 0:
        print(status.stderr.strip() or "not a git repo", file=sys.stderr)
        return 2

    problems: list[str] = []
    dirty_lines = [line for line in status.stdout.splitlines() if line.strip()]
    if dirty_lines and not args.allow_dirty:
        problems.append("dirty worktree remains")
    protected_seen: set[str] = set()
    for path in [status_path(line) for line in dirty_lines]:
        if protected_path(path) and path not in protected_seen:
            problems.append(f"protected artifact dirty or staged: {path}")
            protected_seen.add(path)

    staged = run(["git", "diff", "--cached", "--name-only"], repo)
    staged_files = staged.stdout.splitlines() if staged.returncode == 0 else []
    for path in staged_files:
        if protected_path(path) and path not in protected_seen:
            problems.append(f"protected artifact staged: {path}")
            protected_seen.add(path)

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        if dirty_lines:
            print("Dirty files:", file=sys.stderr)
            for line in dirty_lines[:80]:
                print(line, file=sys.stderr)
        return 1

    print("Agent Governance Kit closeout check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
