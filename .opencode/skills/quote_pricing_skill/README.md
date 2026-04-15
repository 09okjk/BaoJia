# quote-pricing-skill

根据请求、可报价范围和历史参考生成 `quotation_options`。

## Entry

- Script: `scripts/main.py`
- Internal compatibility entry: `run.py`

`run.py` is kept for repository compatibility. Publish-facing usage should prefer `scripts/main.py`.

## Samples

- Input: `samples/sample-input.json`
- Output: `samples/sample-output.json`

## Validation

`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pricing_skill/validate_samples.py"`
