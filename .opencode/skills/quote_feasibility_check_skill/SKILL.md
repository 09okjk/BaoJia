---
name: quote-feasibility-check-skill
slug: quote-feasibility-check-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于标准化后的 quote_request 判断哪些项目可以报价、哪些必须待确认、哪些应排除，并输出 quote_scope、questions_for_user 和 review_flags。当用户提到可报价判断、待确认项识别、报价范围划分、排除项识别、审核提示时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-feasibility-check-skill

## When to Use（何时使用）

- 已有 `quote_request`
- 需要判断当前是否可以进入正式报价
- 需要区分可报价项、待确认项、排除项

## When NOT to Use（何时不用）

- 还没有完成 `assessment_report -> quote_request` 标准化
- 已进入历史报价检索、定价或最终文档组装

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "quote_request": {}
}
```

最小输出骨架：

```json
{
  "can_quote": true,
  "quote_scope": "full | partial | not_ready",
  "quotable_items": [],
  "tbc_items": [],
  "exclusions": [],
  "missing_fields": [],
  "questions_for_user": [],
  "review_flags": []
}
```

## Core Behavior（核心行为）

- 只做可报价范围判断，不做历史检索、定价或最终文档组装
- 将候选项拆分为 `quotable_items`、`tbc_items`、`exclusions`
- 输出 `quote_scope`、`questions_for_user`、`review_flags`
- 所有不确定项都必须结构化表达，不能伪装成可直接报价项

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/FEASIBILITY_CONTRACT.md`
- 正式 Schema：`references/quote-feasibility-check-input.schema.json`、`references/quote-feasibility-check-output.schema.json`
- 规则说明：`references/DECISION_RULES.md`
- 详细示例：`references/EXAMPLES.md`
- 详细设计：`设计与规范/quote_feasibility_check_skill 详细设计.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_feasibility_check_skill/scripts/main.py" --input ".opencode/skills/quote_feasibility_check_skill/samples/sample-input.json"`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- `quote_scope` 只能是 `full`、`partial`、`not_ready`
- 不得把待确认项伪装成可报价项
- 问题统一汇总到 `questions_for_user`

## Security & Privacy（安全说明）

- 当前处理在本地完成
- 仅消费结构化报价请求，不直接访问外部系统

## Related Skills（相关技能）

- `quote-request-prepare-skill`
- `historical-quote-reference-skill`
- `quote-pricing-skill`

## Feedback（反馈）

- 如决策规则变更，需同步更新 `references/DECISION_RULES.md` 与样例
