---
name: quote-review-output-skill
slug: quote-review-output-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于 quote_request、feasibility_result、historical_reference 和 pricing_result 生成最终 quote_document，补齐固定 header、table_schema、footer、review_result 与 trace。当用户提到最终报价 JSON、QuoteDocument 输出、footer 生成、review_result、trace 时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-review-output-skill

## When to Use（何时使用）

- 已有 `pricing_result`
- 需要生成最终 `QuoteDocument`
- 需要补齐 `header`、`table_schema`、`footer`、`review_result`、`trace`

## When NOT to Use（何时不用）

- 还没有完成正文 `quotation_options` 生成
- 还在做可报价判断或历史检索

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

最小输出骨架：

```json
{
  "quote_document": {}
}
```

## Core Behavior（核心行为）

- 负责最终 `quote_document` 组装，不重新定价
- 复用 `pricing_result.quotation_options`
- 必须补齐 `header`、`table_schema`、`footer`、`review_result`、`trace`
- 不得输出任何 Schema 之外的字段

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/OUTPUT_CONTRACT.md`
- 正式 Schema：`references/quote-review-output-input.schema.json`、`references/quote-review-output-output.schema.json`
- 规则说明：`references/FOOTER_RULES.md`
- 详细示例：`references/EXAMPLES.md`
- 详细设计：`设计与规范/quote_review_output_skill 详细设计.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_review_output_skill/scripts/main.py" --input ".opencode/skills/quote_review_output_skill/samples/sample-input.json"`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- 顶层 QuoteDocument 必填字段必须完整
- `header` 固定字段不能缺失
- `footer`、`review_result`、`trace` 必须始终输出

## Security & Privacy（安全说明）

- 当前在本地聚合报价结果
- 最终 `quote_document` 可能包含客户与商业信息，导出前应确认用途与访问范围

## Related Skills（相关技能）

- `quote-pricing-skill`
- `quote-pdf-render-skill`

## Feedback（反馈）

- 修改最终文档契约时优先更新 schema 与 `references/OUTPUT_CONTRACT.md`
