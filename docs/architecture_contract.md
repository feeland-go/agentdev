# Architecture Contract (Canonical Source of Truth)

This file is the authoritative contract for the `sst-research` system. If any document or script conflicts with this file, this file wins.

## Contract A — Environment Ownership

- Global secrets are stored in `~/.hermes/.env`:
  - `TELEGRAM_BOT_TOKEN`
  - `JINA_API_KEY`
- Runtime project chat routing is stored in each project `.env`:
  - `TELEGRAM_CHAT_ID`
- Optional master `.env` may be used as a template seed and copied into new projects.

## Contract B — Path Convention

- Master repository path:
  - `~/projects/sst-research-master`
- Runtime project paths:
  - `~/projects/project-rx-*`
- Active project pointer:
  - `~/.hermes/sst_active_project`

## Contract C — Queue Granularity

- Per-document tasks:
  - `fetch`
  - `extract`
- Per-topic tasks:
  - `synthesize`
- Final report generation runs after topic synthesis completion criteria are met.

## Contract D — Memory Cadence

- `vault/memory/working.md`:
  - append per task/stage events (zero AI call)
- `vault/memory/research.md`:
  - update at stage-batch checkpoints (after Extract stage completion), not per task
- `vault/memory/meta.md`:
  - write once at project completion

## Contract E — Vault Ownership Boundaries

- `vault/sources/` is written by Pipeline 1
- `vault/extracted/`, `vault/synthesis/`, `vault/output/` are written by Pipeline 2
- `vault/memory/` is written by Pipeline 4
- Components outside an owned area are read-only.

## Contract F — Operational Reliability

- Queue state transitions must be explicit and auditable:
  - `pending/ -> active/ -> done/ | failed/ -> dead/`
- Watchdog must recover stale active tasks based on timeout policy.
- Retry policy is bounded and deterministic by config.

## Contract G — Conflict Resolution Rule

When updating docs or scripts:
1. Update this contract first (if contract changes).
2. Update all dependent docs/scripts in the same phase.
3. Do not leave partial contract alignment between files.
