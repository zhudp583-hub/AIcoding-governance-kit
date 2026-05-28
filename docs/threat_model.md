# Threat Model

Agent Governance Kit is a local governance aid for AI coding workflows. It is
not a sandbox and not a complete security control.

## Helps With

- accidental destructive commands
- missing work journals after material changes
- dirty Git worktrees at handoff time
- large runtime artifacts staged in Git
- obvious secret patterns staged in text files
- lack of local audit events for agent sessions

## Does Not Solve

- malicious local users
- compromised developer machines
- bypasses outside Codex or Git
- secrets already present in repository history
- production authorization and deployment approvals
- remote backup or disaster recovery by itself

## Recommended Layers

- branch protection on shared repositories
- CI checks for tests and secret scanning
- external backups for data and model artifacts
- human approval for production-impacting actions
- documented rollback procedures
- periodic restore drills for important systems
