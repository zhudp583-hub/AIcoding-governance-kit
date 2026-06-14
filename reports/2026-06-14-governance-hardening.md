# Governance Hardening - 2026-06-14

## Scope

Implemented the review-driven hardening pass for Agent Governance Kit:

- moved protected artifact path matching into shared `agk_common.py`
- updated hook, pre-commit, and closeout checker to use the shared matcher
- tightened journal/manifest closeout evidence to require an `AGK-Session`
  marker instead of accepting mtime-only document changes
- added `AGK_MATERIAL_CLOSEOUT_MODE=off|warn|enforce`, defaulting to `warn`
  for material but non-red-zone work
- taught the journal helper to discover the latest AGK session state and embed
  the matching session marker

## Validation

- `python3 -m unittest -q tests.test_agk_behaviors`
- `python3 hooks/agent_governance_hook.py --self-test`
- `python3 -m py_compile agk_common.py hooks/agent_governance_hook.py git-hooks/agk_pre_commit.py git-hooks/agk_repo_smoke.py scripts/agk_closeout_check.py scripts/agk_journal_update.py tests/test_agk_behaviors.py`
- `git diff --check`
- `python3 scripts/agk_closeout_check.py --repo . --allow-dirty`
