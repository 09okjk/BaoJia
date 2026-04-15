---
name: quote-request-prepare-skill
slug: quote-request-prepare-skill
version: 1.0.0
author: "BaoJia Team"
description: 将智能评估单、客户补充信息、业务补充信息标准化为统一的 quote_request。当用户提到评估单转报价请求、标准化报价输入、提取待确认项、整理报价上下文、准备后续报价链路输入时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-request-prepare-skill

## When to Use（何时使用）

- 需要把 `assessment_report` 转成统一 `quote_request`
- 需要提取报价相关事实并标准化上下文
- 需要为可报价判断、历史检索和定价准备稳定输入

## When NOT to Use（何时不用）

- 已进入可报价范围判断
- 已进入历史检索或金额计算
- 已进入最终 `QuoteDocument` 组装

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {}
}
```

最小输出骨架：

```json
{
  "quote_request": {},
  "normalization_flags": [],
  "missing_fields": []
}
```

## Core Behavior（核心行为）

- 只做标准化，不做可报价判断、定价或最终报价文档组装
- 输出稳定的 `quote_request`、`normalization_flags`、`missing_fields`
- 缺失事实必须显式保留为 `null`、空数组或 `missing_fields`
- 禁止把待确认事实伪装成已确认事实

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/QUOTE_REQUEST_CONTRACT.md`
- 正式 Schema：`references/quote-request-prepare-input.schema.json`、`references/quote-request-prepare-output.schema.json`
- 规则说明：`references/NORMALIZATION_RULES.md`
- 详细示例：`references/EXAMPLES.md`
- 详细设计：`设计与规范/quote_request_prepare_skill 详细设计.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_request_prepare_skill/scripts/main.py" --input ".opencode/skills/quote_request_prepare_skill/samples/sample-input.json"`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过输入输出 schema 校验，可选

## Core Rules（核心规则）

- 缺失事实必须进入 `missing_fields`
- 标准化动作必须进入 `normalization_flags`
- 只输出下游可直接消费的统一结构

## Security & Privacy（安全说明）

- 当前处理在本地完成，不依赖外部云端服务
- 输入可能包含客户和船舶信息，输出与日志应避免泄露无关敏感数据

## Related Skills（相关技能）

- `quote-template-select-skill`
- `quote-feasibility-check-skill`
- `quote-pricing-skill`

## Feedback（反馈）

- 修改契约前先同步 schema 与 samples
- 新增字段时同步更新 `validate_samples.py`、`samples/` 与 `references/*.schema.json`
