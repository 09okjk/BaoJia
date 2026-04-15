# quote-orchestration-skill

统一封装完整智能报价流程，面向 Agent 提供单一 workflow 入口。

## Entry

- Script: `scripts/main.py`
- Internal compatibility entry: `run.py`

`run.py` is kept for repository compatibility. Publish-facing usage should prefer `scripts/main.py`.

## Samples

- Input: `samples/sample-input.json`
- Output: `samples/sample-output.json`

## Validation

`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_orchestration_skill/validate_samples.py"`
