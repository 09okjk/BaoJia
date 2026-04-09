# AGENTS.md

## Repo Shape
- This repo's executable source of truth lives under `.opencode/`, not the repository root.
- The final QuoteDocument contract is `.opencode/quote-document-v1.1.schema.json`; `.opencode/quote-document-v1.1-example.json` is the canonical full example.
- Business and architecture context lives in `设计与规范/`, with the highest-value overview in `设计与规范/智能报价 Agent Skill 设计说明书.md`.

## Real Workflow
- Do not invent repo-wide commands like `pytest`, `ruff`, `mypy`, `npm`, `make`, or CI steps from the repo root. There is no verified root manifest, task runner, or workflow config.
- The implemented pipeline is five local skills in `.opencode/skills/`: `quote_request_prepare_skill` -> `quote_feasibility_check_skill` -> `historical_quote_reference_skill` -> `quote_pricing_skill` -> `quote_review_output_skill`.
- When changing one skill, read that skill's `SKILL.md`, `schemas/`, `examples/`, and `run.py` before editing code. Those files define the contract and the exact CLI entrypoint.

## Verified Commands
- Use the bundled interpreter: `& ".opencode/.venv/Scripts/python.exe" ...`.
- Focused sample-contract check for one skill: `& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/validate_samples.py"`
- Focused manual run for one skill: `& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/run.py" --input ".opencode/skills/<skill_name>/examples/input.sample.json"`
- `run.py` validates input and output schemas by default; `--skip-schema-validation` exists, so do not assume a run without that flag is schema-free.
- `quote_pricing_skill` output validation also resolves refs against `.opencode/quote-document-v1.1.schema.json`; if pricing output changes, validate that skill, not just its local schema files.

## QuoteDocument Rules That Bite
- Top-level required keys are fixed: `document_type`, `document_version`, `header`, `table_schema`, `quotation_options`, `footer`, `review_result`, `trace`.
- `document_type` is a schema `const` and must stay `quotation`.
- `header` is a fixed 13-field object with `additionalProperties: false`; missing keys break the contract.
- `table_schema.columns` is fixed-length and ordered. Keep exactly 7 columns in this order: `item`, `description`, `unit_price`, `unit`, `qty`, `discount`, `amount`.
- `quotation_options[*]` must include `option_id`, `title`, `sections`, `summary`, `remarks`.
- `section.section_type` only allows `service`, `spare_parts`, `other`.
- Group-level summary is intentionally unsupported. Keep summaries only at option level and footer level.
- Every line must carry the full schema shape, including display fields like `unit_price_display`, `qty_display`, and `amount_display`, even for text-only rows.
- Use structured `discount`; do not hide discount text in `description`.
- `line_type`, `pricing_mode`, and `status` are enum-constrained and are how this repo represents pending / extra / as-actual / owner-supplied cases. Do not replace them with free-text conventions.
- `footer` is required and must contain `summary`, `remark`, and `service_payment_terms`.
- `remark.title` is a schema `const` equal to `Remark`; `service_payment_terms.title` is a schema `const` equal to `Service Payment Terms`.
- `summary` values are structured objects, not plain numbers. In multi-option quotes, never sum option summaries into one footer total.
- `review_result` and `trace` are required final output, not optional metadata.

## Repo-Specific Gotchas
- Docs are secondary to executable contracts. If prose, examples, and schema disagree, trust `.opencode/quote-document-v1.1.schema.json` and the skill schemas/run scripts.
- The skill `SKILL.md` files still point to detailed design docs using simplified names; the actual files in `设计与规范/` are `S1-...` through `S5-...`.
- `.opencode/.env` is a local sensitive file and is not ignored by `.gitignore`; do not commit it.
- Avoid searching or editing `.opencode/.venv/` and `.ruff_cache/` unless the task is specifically about the local environment.
