# quote-feasibility-check-skill

根据 `quote_request` 判断哪些项目可报价、待确认或应排除。

## Entry

- Script: `scripts/main.py`
- Internal compatibility entry: `run.py`

`run.py` is kept for repository compatibility. Publish-facing usage should prefer `scripts/main.py`.

## Samples

- Input: `samples/sample-input.json`
- Output: `samples/sample-output.json`

## Validation

`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_feasibility_check_skill/validate_samples.py"`
