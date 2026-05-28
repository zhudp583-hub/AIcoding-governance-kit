#!/usr/bin/env python3
"""Optional repository-specific smoke checks for Agent Governance Kit."""

from __future__ import annotations

import argparse
import py_compile
import sys
from pathlib import Path


def compile_python(repo: Path, rel_paths: list[str], problems: list[str]) -> None:
    for rel in rel_paths:
        path = repo / rel
        if not path.exists() or path.suffix != ".py":
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            problems.append(f"python syntax failed for {rel}: {exc.msg}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--staged", nargs="*", default=[])
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    problems: list[str] = []

    compile_python(repo, [p for p in args.staged if p.endswith(".py")], problems)

    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
