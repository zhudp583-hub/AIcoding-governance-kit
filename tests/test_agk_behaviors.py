from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load_module("agent_governance_hook", "hooks/agent_governance_hook.py")
pre_commit = load_module("agk_pre_commit", "git-hooks/agk_pre_commit.py")


def run(args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(args, cwd=cwd, env=merged_env, text=True, capture_output=True)


class HookGuardTests(unittest.TestCase):
    def test_command_text_cannot_self_approve_destructive_git(self) -> None:
        command = "echo AGK_APPROVED=1; git reset --hard"

        self.assertEqual(
            hook.block_reason(command),
            "git reset --hard requires explicit human-run approval",
        )
        with patch.dict(os.environ, {"AGK_APPROVED": "1"}):
            self.assertIsNone(hook.block_reason(command))

    def test_rm_root_variants_are_blocked(self) -> None:
        commands = ["rm -fr /", "rm -rf -- /", "sudo rm -rf /", "env X=1 rm -rf /"]

        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(
                    hook.block_reason(command),
                    "Refusing recursive force remove of filesystem root",
                )

    def test_protected_path_matching_is_precise(self) -> None:
        safe_paths = ["examples/config.example.env", "metadata/schema.md", "docs/report.md"]
        protected_paths = [".env", ".env.local", "data/input.csv", "docs/secrets.db", "logs/app.log"]

        for path in safe_paths:
            with self.subTest(path=path):
                self.assertFalse(hook.protected_path(path))
                self.assertFalse(pre_commit.protected_path(path))

        for path in protected_paths:
            with self.subTest(path=path):
                self.assertTrue(hook.protected_path(path))
                self.assertTrue(pre_commit.protected_path(path))

    def test_patch_and_shell_protected_detection(self) -> None:
        event = {
            "tool_name": "apply_patch",
            "tool_input": {
                "command": (
                    "*** Begin Patch\n"
                    "*** Update File: examples/config.example.env\n"
                    "@@\n"
                    "-export AGK_HOOK_MODE=enforce\n"
                    "+export AGK_HOOK_MODE=warn\n"
                    "*** End Patch\n"
                )
            },
        }

        self.assertIsNone(hook.patch_touches_protected(event))
        self.assertEqual(
            hook.bash_touches_protected("printf SECRET > .env"),
            "shell redirection touches protected artifact path: .env",
        )


class GitHookTests(unittest.TestCase):
    def test_pre_commit_handles_non_utf8_staged_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init", "-q"], repo).check_returncode()
            (repo / "image.png").write_bytes(b"\xff\xfe\xfd")
            run(["git", "add", "image.png"], repo).check_returncode()

            result = run(
                ["python3", str(ROOT / "git-hooks/agk_pre_commit.py"), "--repo", str(repo), "--warn-only"],
                repo,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_pre_commit_warns_for_protected_artifact_under_docs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init", "-q"], repo).check_returncode()
            (repo / "docs").mkdir()
            (repo / "docs/secrets.db").write_bytes(b"binary\x00data")
            run(["git", "add", "docs/secrets.db"], repo).check_returncode()

            result = run(
                ["python3", str(ROOT / "git-hooks/agk_pre_commit.py"), "--repo", str(repo), "--warn-only"],
                repo,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("WARN: protected artifact path staged: docs/secrets.db", result.stderr)

    def test_closeout_blocks_protected_dirty_even_when_dirty_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init", "-q"], repo).check_returncode()
            run(["git", "config", "user.email", "review@example.invalid"], repo).check_returncode()
            run(["git", "config", "user.name", "review"], repo).check_returncode()
            (repo / "README.md").write_text("test\n", encoding="utf-8")
            run(["git", "add", "README.md"], repo).check_returncode()
            run(["git", "commit", "-q", "-m", "init"], repo).check_returncode()
            (repo / ".env").write_text("SECRET=value\n", encoding="utf-8")

            result = run(
                ["python3", str(ROOT / "scripts/agk_closeout_check.py"), "--repo", str(repo), "--allow-dirty"],
                repo,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("protected artifact dirty or staged: .env", result.stderr)


class InstallerTests(unittest.TestCase):
    def test_codex_installer_merges_existing_hooks_and_custom_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            codex_home = base / "codex"
            install_root = base / "custom-agk"
            codex_home.mkdir()
            (codex_home / "hooks.json").write_text(
                json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}),
                encoding="utf-8",
            )

            env = {"CODEX_HOME": str(codex_home), "AGK_INSTALL_ROOT": str(install_root)}
            first = run(["sh", str(ROOT / "scripts/install_codex_hooks.sh")], ROOT, env=env)
            second = run(["sh", str(ROOT / "scripts/install_codex_hooks.sh")], ROOT, env=env)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            data = json.loads((codex_home / "hooks.json").read_text(encoding="utf-8"))
            stop_commands = [
                hook_item["command"]
                for group in data["hooks"]["Stop"]
                for hook_item in group.get("hooks", [])
                if "command" in hook_item
            ]
            agk_commands = [item for item in stop_commands if "agent_governance_hook.py" in item]

            self.assertIn("echo keep", stop_commands)
            self.assertEqual(len(agk_commands), 1)
            self.assertIn(str(install_root), agk_commands[0])

    def test_git_installer_chains_existing_pre_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(["git", "init", "-q"], repo).check_returncode()
            hooks_dir = repo / ".git/hooks"
            existing = hooks_dir / "pre-commit"
            marker = repo / "existing-hook-ran"
            existing.write_text(f"#!/bin/sh\ntouch \"{marker}\"\n", encoding="utf-8")
            existing.chmod(0o755)

            install = run(["sh", str(ROOT / "scripts/install_git_hooks.sh"), str(repo)], ROOT)
            self.assertEqual(install.returncode, 0, install.stderr)

            result = run([str(hooks_dir / "pre-commit")], repo)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())


if __name__ == "__main__":
    unittest.main()
