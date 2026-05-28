#!/usr/bin/env python3
"""Repository pre-commit guard for Agent Governance Kit."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


PROTECTED_PATH_RE = re.compile(
    r"(^|/)(\.env($|[./])|\.ssh/|auth\.json$|models/|data/|logs/|tmp/|exports/|research_eval/)"
    r"|(\.pt|\.pkl|\.bin|\.npz|\.parquet|\.dump|\.sqlite|\.db|\.log|\.csv\.gz|\.jsonl\.gz)$",
    re.IGNORECASE,
)

JOURNAL_OR_MANIFEST_RE = re.compile(
    r"(^|/)(worklog/|reports/|manifests/|docs/.*changes.*\.md$|.*CHANGELOG.*\.md$)",
    re.IGNORECASE,
)

MATERIAL_PATH_RE = re.compile(
    r"(\.py|\.sh|\.sql|\.toml|\.json|\.yaml|\.yml|\.service|\.timer|Dockerfile|docker-compose.*\.ya?ml)$"
    r"|(^|/)(scripts/|tools/|config/|systemd/|codex/|\.codex/|cron/)",
    re.IGNORECASE,
)

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |PRIVATE )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "OpenAI-style API key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    (re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]"), "secret assignment"),
]


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def staged_files(repo: str) -> list[str]:
    result = run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def staged_text(repo: str, path: str, max_bytes: int = 2_000_000) -> str | None:
    result = run(["git", "show", f":{path}"], repo)
    if result.returncode != 0:
        return None
    data = result.stdout
    if len(data.encode("utf-8", errors="ignore")) > max_bytes:
        return None
    if "\x00" in data:
        return None
    return data


def file_size(repo: str, path: str) -> int:
    full = Path(repo) / path
    try:
        return full.stat().st_size
    except FileNotFoundError:
        return 0


def is_allowed_protected(path: str) -> bool:
    return path.startswith("reports/") or path.startswith("worklog/") or path.startswith("docs/")


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

    has_journal = any(JOURNAL_OR_MANIFEST_RE.search(path) for path in files)
    has_material = any(MATERIAL_PATH_RE.search(path) for path in files)

    for path in files:
        if PROTECTED_PATH_RE.search(path) and not is_allowed_protected(path):
            problems.append(f"protected artifact path staged: {path}")
        size = file_size(repo, path)
        if size > 10 * 1024 * 1024 and not path.startswith("reports/"):
            problems.append(f"large file staged ({size} bytes): {path}")
        text = staged_text(repo, path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if (
                not stripped
                or stripped.startswith("#")
                or "os.environ" in line
                or "os.getenv" in line
                or '"$' in line
                or "'$" in line
                or "${" in line
                or "http://" in line
                or "https://" in line
            ):
                continue
            for pattern, label in SECRET_PATTERNS:
                if pattern.search(line):
                    problems.append(f"possible {label} in staged file: {path}:{line_no}")
                    break
            else:
                continue
            break

    if has_material and not has_journal:
        problems.append("material code/config/hook change is staged without a journal, report, or manifest file")

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
            "\nAdd/update a worklog, report, or manifest, or unstage protected artifacts before committing.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
