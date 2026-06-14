---
name: agent-operational-governance
description: Keep AI coding agent work tree-clean and enforce evidence only for high-impact operations such as non-scratch deletion, database writes, production/runtime changes, cross-machine sync, backups, models, services, cron, hook changes, or deployment evidence.
---

# Agent Operational Governance

Use this skill when agent work needs clean Git handoff or high-impact evidence.

## Three Working Rules

1. Temporary outputs only go under `scratch/<session-id>/`.
2. Prefer updating existing docs over creating new docs; if a new doc is needed,
   first identify why no existing slot fits.
3. Final response order: user task result, actual actions, file tree impact,
   validation, then governance evidence.

## Zone Model

Classify work by reversibility and blast radius, not by action words.

- Green: read-only queries, any operation inside `scratch/`, ordinary edits to
  Git-tracked source/docs, and local Git status/diff/add/commit/log work. Green
  work needs no extra journal or manifest because Git is the evidence chain.
- Yellow: new files outside `scratch/`, new Markdown outside the approved
  documentation slots, and remote-affecting but Git-backed actions such as
  `git push`. Yellow work should be visible in the final response but should
  not block ordinary handoff.
- Red: deleting non-scratch files, database writes, production/runtime config,
  service/cron/systemd/docker changes, cross-machine `scp`/`rsync`, protected
  artifacts, model/data artifacts, hook changes, and deployment evidence. Red
  work must close with a Git commit or a manifest.

Path/resource overrides beat the default zone. A Git-tracked production config,
deployment selector, hook, secret, model, dump, or service definition is not
green just because Git can revert it.

## Evidence Policy

Git is the primary evidence. Do not create a second proof file for changes that
are already represented clearly by a commit or a readable diff.

Use a manifest only for:

- large or runtime artifacts kept out of Git
- deletion of non-scratch files
- cross-machine sync, backup/offload, or restore work
- production/runtime work that cannot be fully represented in Git

Daily worklogs are for human continuity, not a universal stop-hook
requirement. Keep entries short and append-only. Do not create per-turn reports
unless the user asks for a report or the work produces an external artifact
that needs a manifest.

## Standard Closeout

Before final response:

1. Run `git status --short` for the touched repo.
2. Summarize changed source/docs/config.
3. Run relevant checks, or name skipped checks and why.
4. Keep large data, logs, models, dumps, and CSVs out of Git.
5. Commit code/docs when appropriate, or explain residual dirty state.
6. For red-zone work, commit or record a manifest with path, size, file or row count,
   checksum, source machine, target machine, and whether external sync is
   required.

Use bundled scripts when possible:

```bash
python3 scripts/agk_journal_update.py --domain ops --item "what changed"
python3 scripts/agk_closeout_check.py --repo .
python3 scripts/agk_closeout_check.py --repo . --allow-dirty
```

## Domain Mapping

- `ops`: governance repo, inventory, audit, hook, backup, machine boundary
- `infra`: SSH, tunnels, tmux, cron, systemd, machine setup
- `prod`: production services and deployment selectors
- `research`: experiments, evaluation, feature engineering, backfills, training outputs

## Protected Artifact Rule

Do not commit runtime artifacts:

- `.env`, `.ssh`, secrets, auth files
- `models/`, `data/`, `logs/`, `tmp/`, `exports/`, `research_eval/`
- large `.csv`, `.gz`, `.jsonl`, `.pt`, `.pkl`, `.bin`, `.npz`, `.parquet`,
  `.dump`, `.sqlite`, `.db`, `.log`

If such files matter, write a manifest and sync them through your approved
backup path.

## Stop Hook Interaction

The Agent Governance Kit Stop hook should block only for missing red-zone
evidence or protected artifacts. It should not block ordinary code work merely
because no journal was written. If the hook continues the turn, complete the
needed commit/manifest or protected-artifact cleanup, then answer.
