# AIcoding Governance Kit

[中文说明](README.zh-CN.md)

Agent Governance Kit is a lightweight governance layer for AI coding agents.
It combines Codex lifecycle hooks, Git pre-commit checks, work journals, and
closeout checks so agent-driven projects do not lose their operational memory as
they grow.

## Why This Exists

We are now in the AI coding era. Many people without a traditional software
engineering background are using coding agents to build real products, automate
workflows, and pursue ideas that used to be out of reach.

That is powerful, but it also creates a new failure mode. A project can move
fast at first, then become hard to trust: repositories drift, versions get
confused, deployment steps are forgotten, operational changes are not recorded,
and technical debt accumulates quietly. Builders who are new to code often get
pulled into avoidable loops because the agent can make changes faster than the
project can explain them.

Agent Governance Kit is for those builders. It gives an AI coding workflow a
small amount of discipline:

- detect material code, config, service, data, and Git operations
- block obviously dangerous commands before they run
- record agent activity into a local audit log
- require a journal, manifest, or commit before a material session finishes
- stop large runtime artifacts and secrets from entering Git
- provide reusable scripts for project closeout

It does not replace engineering judgment. It gives builders and agents a
repeatable way to leave evidence after meaningful work.

## What Is Included

- `hooks/hooks.json`: Codex hook registration for session, prompt, tool, and
  stop events.
- `hooks/agent_governance_hook.py`: lifecycle hook implementation.
- `git-hooks/pre-commit`: portable pre-commit wrapper.
- `git-hooks/agk_pre_commit.py`: staged-file guard for journals, secrets, and
  protected artifacts.
- `git-hooks/agk_repo_smoke.py`: optional repository-specific smoke-check
  extension point.
- `scripts/install_codex_hooks.sh`: installs Codex hook files into
  `~/.codex/agent-governance-kit`.
- `scripts/install_git_hooks.sh`: installs the Git pre-commit guard into a
  repository.
- `scripts/agk_journal_update.py`: appends closeout notes to a journal.
- `scripts/agk_closeout_check.py`: checks a repository before handoff.
- `skills/agent-operational-governance/SKILL.md`: a Codex skill describing the
  operating discipline.

## Quick Start

Install Codex hooks:

```bash
./scripts/install_codex_hooks.sh
```

The installer merges Agent Governance Kit hook groups into an existing
`hooks.json` instead of replacing unrelated hooks. Set `CODEX_HOME` to choose
the Codex config directory, or `AGK_INSTALL_ROOT` to choose where this kit is
installed.

Install the Git pre-commit guard in a repository:

```bash
./scripts/install_git_hooks.sh /path/to/your/repo
```

If the repository already has a `pre-commit` hook, the installer keeps it as
`pre-commit.bak-agk` and the AGK wrapper chains to it after AGK checks pass.

Run a closeout check:

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo
```

Append a journal entry:

```bash
python3 scripts/agk_journal_update.py --domain ops --item "Updated deployment config and verified service health"
```

## Configuration

The default configuration is intentionally generic. Customize it through
environment variables instead of editing the hook code.

See `examples/config.example.env` for the full list.

Common variables:

- `AGK_STATE_DIR`: where hook state is stored.
- `AGK_INSTALL_ROOT`: where the installed hook implementation lives.
- `AGK_HOOK_MODE`: `enforce` or `warn`.
- `AGK_JOURNAL_DIRS`: colon-separated journal or manifest directories.
- `AGK_PROTECTED_PATHS`: colon-separated path markers that should not be
  committed.
- `AGK_RESEARCH_GRACE_ROOTS`: optional colon-separated roots that may keep
  temporary research files dirty for a limited time.
- `AGK_RESEARCH_GRACE_PREFIXES`: optional dirty-path prefixes allowed under
  those roots.
- `AGK_RESEARCH_DIRTY_GRACE_HOURS`: grace period for those research paths.
- `AGK_JOURNAL_INCLUDE_LOCAL`: set to `1` to include hostnames and absolute
  CWDs in journal entries. The default redacts local machine metadata.

## Safety Model

Agent Governance Kit is a local guardrail. It is designed to reduce avoidable
mistakes, not to be a security boundary.

Use it together with:

- GitHub branch protection
- CI checks
- secret scanning
- backups
- human review for production operations
- clear rollback procedures

## Public-Safe Defaults

This repository is intentionally sanitized:

- no private hostnames
- no IP addresses
- no internal repository names
- no personal machine paths
- no secrets
- no business-specific deployment logic

Project-specific policies belong in local configuration, private forks, or
private deployment scripts.

## Status

This is an early toolkit extracted from a real AI-assisted operations workflow.
Audit the defaults before enabling `enforce` mode on important repositories.

This project is 100% written by Codex.
