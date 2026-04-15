---
name: quote-template-select-skill
slug: quote-template-select-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于智能评估单判断报价类型并选择对应模板类型，输出 template_selection_result 供后续报价链路和 PDF 渲染链路使用。当用户提到模板选择、报价类型识别、评估单判断模板、S0 模板分类时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-template-select-skill

## When to Use（何时使用）

- 需要在报价链路开始前判断评估单属于哪种报价模板
- 需要为后续 skill 提供统一 `template_type`
- 需要在低置信度时给出候选模板和人工确认提示

## When NOT to Use（何时不用）

- 已进入金额计算或报价明细生成
- 已有明确人工指定模板且无需自动判断
- 只是渲染现有 `quote_document`

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {
    "force_template_type": null
  }
}
```

最小输出骨架：

```json
{
  "template_selection_result": {
    "template_type": "engineering-service",
    "confidence": 0.88,
    "candidate_templates": [],
    "rule_scores": {},
    "reasons": [],
    "matched_signals": [],
    "needs_manual_confirmation": false,
    "questions_for_user": [],
    "review_flags": []
  }
}
```

## Core Behavior（核心行为）

- 只判断 `template_type`，不生成 `quote_request`、`quotation_options` 或 `quote_document`
- 输出 `confidence`、`candidate_templates`、`reasons`、`matched_signals`
- 低置信度时必须显式要求人工确认
- 默认兜底模板是 `engineering-service`，但不能静默兜底

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 正式 Schema：`references/quote-template-select-input.schema.json`、`references/quote-template-select-output.schema.json`
- 详细设计：`设计与规范/S0-quote_template_select_skill 设计草案.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_template_select_skill/scripts/main.py" --input ".opencode/skills/quote_template_select_skill/samples/sample-input.json"`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- 模板选择必须来自固定 7 类枚举
- 低置信度时必须保留人工确认信号
- 兜底模板是 `engineering-service`，但必须显式说明原因

## Security & Privacy（安全说明）

- 当前判断在本地完成
- 只消费评估单与上下文，不访问外部 API

## Related Skills（相关技能）

- `quote-request-prepare-skill`
- `historical-quote-reference-skill`
- `quote-pdf-render-skill`

## Feedback（反馈）

- 若模板枚举变更，需同步更新 schema、打分规则和 PDF 渲染分发逻辑
