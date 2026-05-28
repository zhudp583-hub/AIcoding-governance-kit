# Bugfix Review Fixes

Date: 2026-05-28

Scope:

- fixed destructive command guard bypasses and `rm` option variants
- made protected path checks component-aware to avoid false positives
- blocked protected artifacts in staged and dirty Git states, including under
  docs and reports
- made staged-file secret scanning safe for non-UTF-8 binary files
- changed Codex hook installation to merge existing hook configuration
- changed Git pre-commit installation to preserve and chain existing hooks
- redacted journal host and CWD metadata by default
- added regression tests for the repaired behaviors
- added a Chinese README and linked it from the root README
- aligned the Chinese README project name with `AIcoding Governance Kit`
- added Codex authorship notes to the English and Chinese READMEs

Verification:

- `python3 -m py_compile hooks/agent_governance_hook.py git-hooks/agk_pre_commit.py git-hooks/agk_repo_smoke.py scripts/agk_closeout_check.py scripts/agk_journal_update.py tests/test_agk_behaviors.py`
- `python3 hooks/agent_governance_hook.py --self-test`
- `python3 -m unittest discover -s tests -v`
- `sh -n scripts/install_codex_hooks.sh scripts/install_git_hooks.sh git-hooks/pre-commit`
- temp-index run of `python3 git-hooks/agk_pre_commit.py --repo .`
- `python3 scripts/agk_closeout_check.py --repo . --allow-dirty`

Residual notes:

- repository remote still reports `origin/main: gone`; publish target should be
  repaired before release
- license and final public project naming remain open release decisions
