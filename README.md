# AIcoding Governance Kit

[中文说明](README.zh-CN.md)

## Why It Exists

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

*The personal note above is the only part of this project written by a human.*

---

AIcoding Governance Kit helps AI coding agents stop creating accidental chaos:
duplicate scripts, stale versions, unclear handoffs, risky file changes, and
unexplained production-impacting work.

It does this with local hooks, Git guards, closeout helpers, and an agent skill.
The goal is simple: let the agent move quickly, but make it search, reuse,
explain, and leave evidence before the work becomes hard to trust.

## Key Capabilities

| Capability | Problem it prevents |
| --- | --- |
| 🔎 **Search before adding scripts** | Lifecycle hooks warn the agent before it creates task-style scripts such as `train_*`, `build_*`, `run_*`, or `audit_*` when similar scripts already exist. This reduces version explosion, duplicate work, and "which script is the real one?" confusion. |
| 🧭 **Keep session risk state across resumes** | If a session is interrupted and resumed, high-impact work stays marked high-impact until it is closed out. |
| 📋 **Bring script ownership into the session** | When `scripts/MANIFEST.md` exists, AGK copies it into the session scratch area so the agent sees existing script purpose and do-not-duplicate notes early. |
| 🚦 **Separate normal edits from high-impact operations** | Ordinary source and docs work can stay Git-first; database writes, service changes, deployments, protected artifacts, backups, and cross-machine sync require stronger evidence. |
| 🛡️ **Block common commit mistakes** | The Git pre-commit guard stops protected artifacts, large runtime files, suspicious secrets, and project smoke-check failures before they enter history. |
| 🤝 **Make handoff explicit** | Closeout helpers and the reusable skill give the agent a small, repeatable way to summarize what changed, what was checked, and what still needs human attention. |

## Overview

AIcoding Governance Kit is a local governance kit for projects built with AI
coding agents. It gives Codex and Git a small amount of structure so fast agent
work still leaves a trustworthy trail.

It is not a SaaS product, a security boundary, or a heavy process framework. It
is a hook + script + skill pack you can keep in a repository, audit, and adapt.

The design is deliberately balanced:

- Not docs-only. Notes drift when they are not tied to Git state.
- Not heavy-by-default. If every edit requires ceremony, the agent starts
  optimizing for governance instead of the product.
- Git-first for normal work. Source and docs are usually explained by
  `git status`, `git diff`, and commits.
- Stronger evidence for high-impact work. Runtime changes, data writes,
  protected artifacts, model files, backups, cross-machine sync, and deployment
  evidence need a commit or session-marked journal/manifest.

## What You Get

- **Codex lifecycle hooks**: add context on session start, inspect prompt/tool
  events, block selected destructive actions, track material work, and enforce
  closeout only when the work is high-impact.
- **Git pre-commit guard**: stops protected artifacts, large files, common
  secret patterns, and optional project smoke-check failures before they enter
  a commit.
- **Closeout helpers**: check whether a repo is ready for handoff and write
  short session-marked journal entries when Git alone is not enough.
- **Reusable agent skill**: tells the agent how to use `scratch/`, Git evidence,
  protected artifact rules, and the green/yellow/red closeout model.

## Field-Tested Behaviors

AGK includes a few small behaviors that came from real long-running agent
workspaces:

- **Resume-safe state**: if a session resumes, the hook keeps previously
  recorded high-impact state instead of resetting it.
- **Script discovery warning**: when an agent writes a task-style Python script
  such as `train_*`, `build_*`, `run_*`, or `audit_*`, AGK warns if similar
  scripts already exist nearby.
- **Script manifest handoff**: if a repository has `scripts/MANIFEST.md`, AGK
  copies it into the session scratch area so the agent can see script ownership
  and do-not-duplicate notes early.
- **Balanced pre-commit checks**: pre-commit blocks protected artifacts,
  suspicious secrets, large runtime files, and failed smoke checks. Ordinary
  material edits are left to Git status, diff, review, and optional closeout
  policy instead of being blocked by default.

## Evidence Model

AGK uses zones instead of treating every change the same:

- **Green**: read-only work, `scratch/` output, ordinary source/doc edits, and
  local Git status/diff/add/commit/log. Git is enough.
- **Yellow**: new files outside `scratch/`, new Markdown outside normal docs
  slots, and remote-affecting but Git-backed work such as `git push`. These
  should be visible, but do not block ordinary handoff.
- **Red**: non-scratch deletion, database writes, runtime/production config,
  service/cron/systemd/docker changes, cross-machine sync, protected artifacts,
  models, backups, hook changes, and deployment evidence. These require a
  post-session commit or a journal/manifest containing `AGK-Session:
  <session-id>`.

Material but non-red work defaults to warning mode. Set
`AGK_MATERIAL_CLOSEOUT_MODE=enforce` if you want every material session to end
with evidence.

## Installation

Install Codex hooks:

```bash
./scripts/install_codex_hooks.sh
```

The installer merges AGK hook groups into an existing `hooks.json` instead of
replacing unrelated hooks. Set `CODEX_HOME` to choose the Codex config
directory, or `AGK_INSTALL_ROOT` to choose where the kit is installed.

Install the Git pre-commit guard in a repository:

```bash
./scripts/install_git_hooks.sh /path/to/your/repo
```

If the repository already has a `pre-commit` hook, AGK keeps it as
`pre-commit.bak-agk` and chains to it after AGK checks pass.

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

Journal domains are `ops`, `infra`, `prod`, and `research`. The helper embeds
an `AGK-Session` marker from `AGK_SESSION_ID` or the most recent AGK state file;
pass `--session-id` to override it.

## Configuration

See `examples/config.example.env` for all supported environment variables.

| Variable | Purpose |
| --- | --- |
| `AGK_HOOK_MODE` | `enforce` or `warn` for Stop-hook blocking behavior. |
| `AGK_MATERIAL_CLOSEOUT_MODE` | `off`, `warn`, or `enforce` for material but non-red work. Default: `warn`. |
| `AGK_PROTECTED_PATHS` | Colon-separated protected path markers. |
| `AGK_JOURNAL_DIRS` | Colon-separated journal/manifest directories searched for evidence. |
| `AGK_PRE_COMMIT_WARN_ONLY` | Set to `1` while adopting the pre-commit guard. |
| `AGK_STATE_DIR` | Hook state directory. |
| `AGK_INSTALL_ROOT` | Installed hook implementation path. |
| `AGK_DEFAULT_JOURNAL` | Optional default journal path. |
| `AGK_SESSION_ID` | Optional journal session marker override. |
| `AGK_JOURNAL_INCLUDE_LOCAL` | Set to `1` only for private journals where hostnames and absolute paths are OK. |

## Files

- `agk_common.py`: shared protected-path matching.
- `hooks/hooks.json`: Codex lifecycle hook registration.
- `hooks/agent_governance_hook.py`: Codex hook implementation.
- `git-hooks/pre-commit`: portable pre-commit wrapper.
- `git-hooks/agk_pre_commit.py`: staged-file guard.
- `git-hooks/agk_repo_smoke.py`: optional repo-specific smoke-check hook.
- `scripts/install_codex_hooks.sh`: installs Codex hooks.
- `scripts/install_git_hooks.sh`: installs the Git pre-commit guard.
- `scripts/agk_closeout_check.py`: handoff check.
- `scripts/agk_journal_update.py`: session-marked journal helper.
- `skills/agent-operational-governance/SKILL.md`: reusable operating skill.

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
- no hostnames, IP addresses, or access paths from the private workspace that
  shaped the field-tested behaviors above

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
