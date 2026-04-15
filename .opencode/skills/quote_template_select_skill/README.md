# quote-template-select-skill

在报价链路开始前识别模板类型并输出 `template_selection_result`。

## Entry

- Script: `scripts/main.py`
- Internal compatibility entry: `run.py`

`run.py` is kept for repository compatibility. Publish-facing usage should prefer `scripts/main.py`.

## Samples

- Input: `samples/sample-input.json`
- Output: `samples/sample-output.json`

## Validation

`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_template_select_skill/validate_samples.py"`
