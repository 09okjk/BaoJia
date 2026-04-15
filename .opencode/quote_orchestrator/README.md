# quote_orchestrator

Deprecated compatibility directory.

## Status

- This directory is no longer the maintained source of workflow logic.
- The maintained implementation now lives in:
  - `.opencode/skills/quote_orchestration_skill/workflow/`

## What remains here

- `run.py` compatibility shell
- module-level compatibility wrappers for `state.py`, `planner.py`, `policy.py`, `skill_registry.py`
- legacy examples and compatibility schemas for old paths

## Maintenance rule

- Do not add new workflow logic here.
- Do not update business rules here.
- Any new workflow capability must be implemented under:
  - `.opencode/skills/quote_orchestration_skill/workflow/`

## Why this still exists

- To avoid breaking previously verified commands and old import paths during migration.
