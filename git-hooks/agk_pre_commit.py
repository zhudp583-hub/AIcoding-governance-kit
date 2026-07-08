#!/usr/bin/env python3
"""Repository pre-commit guard for Agent Governance Kit."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agk_common import protected_path

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]"), "secret assignment"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)=([^&\s'\"]{12,})"), "secret URL parameter"),
    (re.compile(r"os\.getenv\([^,\n]+,\s*['\"][^'\"]{12,}['\"]\)"), "hard-coded environment fallback"),
]


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def staged_files(repo: str) -> list[str]:
    result = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def staged_blob(repo: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "show", f":{path}"], cwd=repo, capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout


def staged_text(repo: str, path: str, max_bytes: int = 10_000_000) -> str | None:
    data = staged_blob(repo, path)
    if data is None or len(data) > max_bytes:
        return None
    if b"\x00" in data:
        return None
    return data.decode("utf-8", errors="replace")


def file_size(repo: str, path: str) -> int:
    full = Path(repo) / path
    try:
        return full.stat().st_size
    except FileNotFoundError:
        return 0


def should_skip_secret_line(stripped: str, line: str) -> bool:
    if not stripped or stripped.startswith("#"):
        return True
    placeholders = ("${", '"$', "'$")
    return any(item in line for item in placeholders)


def secret_findings(path: str, text: str) -> Iterable[str]:
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if should_skip_secret_line(stripped, line):
            continue
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(line):
                yield f"possible {label} in staged file: {path}:{line_no}"
                break


def smoke_script(repo: str) -> str | None:
    candidates = [
        Path(repo) / "git-hooks/agk_repo_smoke.py",
        Path(repo) / ".git/hooks/agk_repo_smoke.py",
        Path.home() / ".codex/agent-governance-kit/git-hooks/agk_repo_smoke.py",
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--warn-only", action="store_true")
    args = parser.parse_args()

    repo = str(Path(args.repo).resolve())
    files = staged_files(repo)
    problems: list[str] = []

    if not files:
        return 0

    for path in files:
        if protected_path(path):
            problems.append(f"protected artifact path staged: {path}")
        size = file_size(repo, path)
        if size > 10 * 1024 * 1024:
            problems.append(f"large file staged ({size} bytes): {path}")
        text = staged_text(repo, path)
        if text is None:
            continue
        problems.extend(secret_findings(path, text))

    script = smoke_script(repo)
    if script:
        smoke = run(["python3", script, "--repo", repo, "--staged", *files], repo)
        if smoke.returncode != 0:
            problems.extend(line for line in smoke.stderr.splitlines() if line.strip())

    if problems:
        prefix = "WARN" if args.warn_only or os.environ.get("AGK_PRE_COMMIT_WARN_ONLY") == "1" else "FAIL"
        for problem in problems:
            print(f"{prefix}: {problem}", file=sys.stderr)
        if prefix == "WARN":
            return 0
        print(
            "\nUnstage protected artifacts or large runtime files before committing.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
