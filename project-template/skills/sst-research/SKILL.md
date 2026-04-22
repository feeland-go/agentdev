---
name: sst-research
description: Operator command contract for Telegram-driven SST research workflow.
version: 1.0.0
platforms: [macos]
---

# SST Research Operator Commands

Active project pointer:
```bash
PROJECT=$(cat ~/.hermes/sst_active_project 2>/dev/null)
PROJECT_DIR="$HOME/projects/$PROJECT"
```

## /sst-rx-new [name]
- Create project from template
- Collect setup answers via Hermes
- Write `research_config.yaml` via `orchestrator/setup.py`
- Initialize memory files via `memory/memory.py`
- Generate query candidates and populate queue

## /sst-rx-start
- Start/resume worker:
```bash
bash "$PROJECT_DIR/run_research.sh" worker
```

## /sst-rx-stop
- Stop worker by PID file in `logs/worker.pid`

## /sst-rx-status
- Report queue counters from `queue/*`

## /sst-rx-memory
- Summarize `vault/memory/working.md` + `vault/memory/research.md`

## /sst-rx-memory-gaps
- Show only open gaps from `vault/memory/research.md`

## /sst-rx-report
- Summarize `vault/output/final-report.md` when available

## /sst-rx-list
- Enumerate `~/projects/project-rx-*/research_config.yaml`

## /sst-rx-archive
- Archive project output and optionally remove runtime folder after confirmation
