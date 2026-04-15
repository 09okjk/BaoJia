---
name: quote-pricing-skill
slug: quote-pricing-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于 quote_request、feasibility_result、historical_reference 和 pricing_rules 生成符合固定模板中间结构的 quotation_options，并输出 section、group、line 与 option summary。当用户提到报价正文建模、单方案/多方案输出、报价项金额结构、option summary 时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-pricing-skill

## When to Use（何时使用）

- 已有 `quote_request`
- 已有 `feasibility_result`
- 已有 `historical_reference`
- 需要生成 `quotation_options`

## When NOT to Use（何时不用）

- 还没有完成可报价判断或历史参考整理
- 需要直接生成最终 `QuoteDocument`

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

最小输出骨架：

```json
{
  "quotation_options": []
}
```

## Core Behavior（核心行为）

- 生成 `quotation_options`，但不组装最终 `QuoteDocument`
- 将结果映射为 `section / group / line / summary`
- 不确定项必须用结构化状态字段表达
- 每条 `line` 都必须带齐完整字段，且不允许 group 级 summary

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/PRICING_CONTRACT.md`
- 正式 Schema：`references/quote-pricing-input.schema.json`、`references/quote-pricing-output.schema.json`
- 映射规则：`references/LINE_MAPPING_RULES.md`
- 详细示例：`references/EXAMPLES.md`
- 详细设计：`设计与规范/quote_pricing_skill 详细设计.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pricing_skill/scripts/main.py" --input ".opencode/skills/quote_pricing_skill/samples/sample-input.json"`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- 输出必须满足 QuoteDocument 子结构契约
- group 级 summary 不允许输出
- 不确定项必须用结构化字段表达，而不是自由文本约定

## Security & Privacy（安全说明）

- 当前定价在本地执行
- `pricing_rules` 可能含商业敏感规则，日志与样例应避免泄露真实生产规则

## Related Skills（相关技能）

- `quote-feasibility-check-skill`
- `historical-quote-reference-skill`
- `quote-review-output-skill`

## Feedback（反馈）

- 修改 line/summary 结构时同步更新 output schema 与样例
