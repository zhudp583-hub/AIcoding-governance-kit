---
name: agent-operational-governance
description: Enforce operational closeout for AI coding agent work. Use when doing audits, Git closeout, work journals, deployment checks, backup records, service changes, hook changes, or any task that changes code, docs, runtime state, data, cron, services, or deployment evidence.
---

# Agent Operational Governance

Use this skill when agent work needs an evidence chain.

## Core Rule

Every material change should end with evidence:

1. journal or manifest updated
2. Git state closed, or dirty state explicitly explained
3. checks run or skipped checks named
4. residual risk and rollback/recovery note included

Material changes include code edits, docs edits, service changes, cron changes,
database exports or destructive operations, model or training artifacts, backup
work, deployment selector changes, and cleanup of runtime files.

## Standard Closeout

Before final response:

1. Run `git status --short` for the touched repo.
2. Update the correct journal or manifest.
3. Commit code/docs when appropriate.
4. Keep large data, logs, models, dumps, and CSVs out of Git.
5. Record large artifacts in a manifest with path, size, file or row count,
   checksum, source machine, target machine, and whether external sync is
   required.
6. Say which checks ran and what remains unresolved.

Use bundled scripts when possible:

```bash
python3 scripts/agk_journal_update.py --domain ops --item "what changed"
python3 scripts/agk_closeout_check.py --repo .
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

The Agent Governance Kit Stop hook can continue the turn when it detects
material work without evidence. If that happens, complete the journal/manifest
and Git closeout, then answer.
