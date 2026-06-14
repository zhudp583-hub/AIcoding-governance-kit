"""Shared helpers for Agent Governance Kit scripts."""

from __future__ import annotations

import os


DEFAULT_PROTECTED_PATHS = ".env:.ssh/:auth.json:models/:data/:logs/:tmp/:exports/:research_eval/"

PROTECTED_SUFFIXES = (
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


def colon_list(value: str) -> tuple[str, ...]:
    return tuple(item for item in value.split(":") if item)


def protected_path_markers() -> tuple[str, ...]:
    return colon_list(os.environ.get("AGK_PROTECTED_PATHS", DEFAULT_PROTECTED_PATHS))


def normalized_path_parts(path: str) -> tuple[list[str], str]:
    normalized = path.replace("\\", "/").strip()
    parts = [part for part in normalized.split("/") if part not in {"", "."}]
    basename = parts[-1].lower() if parts else ""
    return [part.lower() for part in parts], basename


def protected_path(path: str) -> bool:
    markers = protected_path_markers()
    protected_dir_names = frozenset(
        marker.strip("/").lower()
        for marker in markers
        if marker.endswith("/") and marker.strip("/")
    )
    protected_file_names = frozenset(
        marker.lower()
        for marker in markers
        if marker and not marker.endswith("/") and "/" not in marker and marker != ".env"
    )

    parts, basename = normalized_path_parts(path)
    if not basename:
        return False
    if basename == ".env" or basename.startswith(".env."):
        return True
    if basename in protected_file_names:
        return True
    if any(part in protected_dir_names for part in parts):
        return True
    return basename.endswith(PROTECTED_SUFFIXES)
