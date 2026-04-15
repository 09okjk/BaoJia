# Deprecated Notice

`quote_orchestrator` is now a compatibility-only directory.

## Maintained implementation

Use and maintain:

- `.opencode/skills/quote_orchestration_skill/workflow/`

## Compatibility-only files

The following paths remain only to avoid breaking previously verified commands:

- `run.py`
- `state.py`
- `planner.py`
- `policy.py`
- `skill_registry.py`
- `schemas/`

## Maintenance rule

- Do not add new workflow logic here.
- Do not change planner rules here.
- Do not evolve schemas here except as compatibility forwarding.

All future workflow changes must be made under:

- `.opencode/skills/quote_orchestration_skill/workflow/`
