# AIcoding Governance Kit

[中文说明](README.zh-CN.md)

This is for AI coders who do not come from a coding background. A simple test:
if you already know what it means to "Git-ify" your code, you probably do not
need this. If you do not, then you are who I had in mind. I was that person.

When a project gets complicated enough, an agent can suddenly grab code from
twenty versions ago and start using it. Things do not behave the way you expect,
so you keep iterating. I once spent a whole week doing that, only to realize I
was just going in circles. The bugs I was chasing had already been fixed three
months earlier, and I already had a much cleaner solution.

This tool is what helped me get out of that loop. It helps you leave a journal
before and after every important change, keep the main line of your code
separate from side branches, and avoid running the wrong version, committing the
wrong files, or losing the thread halfway through an idea.

So I am sharing it in the hope that it helps you too. Wishing you all the best.

*Everything above is the only part of this project written by a human.*

##

AIcoding Governance Kit is a small governance toolkit for people building real
projects with AI coding agents. It adds lightweight checks around Codex, Git,
project journals, and handoff routines so the agent can move quickly without
quietly losing the thread of the work.

The kit is intentionally local and plain-file based. It does not require a
server, SaaS account, database, or private infrastructure. Install the hooks,
keep the scripts in your project, and adapt the rules to your own repository.

## What It Does

AIcoding Governance Kit focuses on a practical problem: agent-driven projects
need memory, boundaries, and evidence.

It helps you:

- load governance context when a Codex session starts
- detect material tool use such as edits, commits, service commands, data
  commands, and cross-machine sync
- block a small set of commands that commonly destroy user work
- keep protected artifacts such as secrets, model files, databases, logs, and
  exports out of Git
- record hook events locally for audit and debugging
- use Git status, diff, and commits as the default evidence for ordinary work
- require stronger evidence for high-impact operations
- provide a reusable Codex skill that tells the agent how to close work cleanly

It is not a replacement for engineering judgment, CI, backups, branch
protection, or human review. It is a guardrail for the everyday failure modes
that appear when a coding agent can change more than the project can explain.

## How It Works

The kit has four layers:

1. **Codex lifecycle hooks**

   The hook runs on `SessionStart`, `UserPromptSubmit`, `PreToolUse`,
   `PostToolUse`, and `Stop`. It adds operating context, tracks material work,
   blocks selected destructive commands, detects protected artifact paths, and
   asks for closeout evidence only when the work crosses into high-impact
   territory.

2. **Git pre-commit guard**

   The pre-commit hook checks staged files before they are committed. It blocks
   protected artifact paths, large files, common secret patterns, and material
   source/config/hook changes that have no journal, report, or manifest. During
   adoption it can be switched to warning mode.

3. **Closeout scripts**

   `agk_closeout_check.py` verifies that a repository is ready for handoff and
   has no protected artifacts dirty or staged. `agk_journal_update.py` appends
   short, timestamped work notes when a journal or manifest is the right form of
   evidence.

4. **Agent operating skill**

   `skills/agent-operational-governance/SKILL.md` gives the agent a compact
   working model: use `scratch/` for temporary output, prefer Git evidence for
   ordinary work, keep runtime artifacts out of commits, and require a commit or
   manifest for high-impact operations.

## Repository Contents

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

## Installation

Clone the repository, then run the installers from the repository root.

Install Codex hooks:

```bash
./scripts/install_codex_hooks.sh
```

The installer merges AIcoding Governance Kit hook groups into an existing
`hooks.json` instead of replacing unrelated hooks. Set `CODEX_HOME` to choose
the Codex config directory, or `AGK_INSTALL_ROOT` to choose where this kit is
installed.

Install the Git pre-commit guard in a repository:

```bash
./scripts/install_git_hooks.sh /path/to/your/repo
```

If the repository already has a `pre-commit` hook, the installer keeps it as
`pre-commit.bak-agk` and the AGK wrapper chains to it after AGK checks pass.

## Usage

Run a closeout check:

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo
```

Allow ordinary dirty work while still checking protected artifacts:

```bash
python3 scripts/agk_closeout_check.py --repo /path/to/your/repo --allow-dirty
```

Append a journal entry:

```bash
python3 scripts/agk_journal_update.py --domain ops --item "Updated deployment config and verified service health"
```

Available journal domains are `ops`, `infra`, `prod`, and `research`.

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
- `AGK_PRE_COMMIT_WARN_ONLY`: set to `1` to warn instead of blocking at
  pre-commit time.
- `AGK_DEFAULT_JOURNAL`: optional default journal path for the journal helper.
- `AGK_JOURNAL_INCLUDE_LOCAL`: set to `1` to include hostnames and absolute
  CWDs in journal entries. The default redacts local machine metadata.

## Closeout Model

The current default is Git-first. Ordinary source and documentation edits do
not need an extra journal entry when `git status` and `git diff` already explain
the work. Use manifests for high-impact work: non-scratch deletions, service or
cron changes, database writes, cross-machine sync, protected artifacts, models,
backups, deployment evidence, and other runtime changes that Git alone cannot
fully describe.

The skill uses this zone model:

- **Green**: read-only queries, work under `scratch/`, ordinary source and
  documentation edits, and local Git status/diff/add/commit/log work.
- **Yellow**: new files outside `scratch/`, new Markdown outside normal
  documentation slots, and remote-affecting but Git-backed operations such as
  `git push`.
- **Red**: non-scratch deletion, database writes, runtime or production config,
  service/cron/systemd/docker changes, cross-machine sync, protected artifacts,
  models, backups, hook changes, and deployment evidence.

Red work should end with a Git commit or a manifest. Green work should not need
extra paperwork when the diff already explains it.

## Safety Model

AIcoding Governance Kit is a local guardrail. It is designed to reduce
avoidable mistakes, not to be a security boundary.

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

## Project Status

This is an early community toolkit extracted from a real AI-assisted operations
workflow. The defaults are conservative, but every team should audit them before
using `enforce` mode on important repositories.

Useful first contributions are small and concrete:

- clearer install docs for different Codex setups
- additional tests for hook edge cases
- more examples of safe project-specific configuration
- documentation for common adoption paths

## Status

This project is 100% written by Codex.
