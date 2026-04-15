# historical-quote-reference-skill

检索相似历史报价案例，输出参考摘要与置信度。

## Entry

- Script: `scripts/main.py`
- Internal compatibility entry: `run.py`

`run.py` is kept for repository compatibility. Publish-facing usage should prefer `scripts/main.py`.

## Samples

- Input: `samples/sample-input.json`
- Output: `samples/sample-output.json`

## Validation

`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/historical_quote_reference_skill/validate_samples.py"`
