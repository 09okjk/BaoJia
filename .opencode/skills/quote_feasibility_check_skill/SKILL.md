---
name: quote_feasibility_check_skill
description: 基于标准化后的 quote_request 判断哪些项目可以报价、哪些必须待确认、哪些应排除，并输出 quote_scope、questions_for_user 和 review_flags。当用户提到可报价判断、待确认项识别、报价范围划分、排除项识别、审核提示时使用。
---

# quote_feasibility_check_skill

## 何时使用此 Skill

在以下场景使用：

- 已经有 `quote_request`
- 需要判断当前是否可以进入正式报价
- 需要区分可报价项、待确认项、排除项
- 需要输出 `quote_scope`
- 需要生成 `questions_for_user` 和 `review_flags`

不要在以下场景使用：

- 还没有完成 `assessment_report -> quote_request` 标准化
- 已经进入历史报价检索
- 已经进入金额计算和正文结构生成
- 已经进入最终 `QuoteDocument` 组装

## 前提条件

- 必须存在 `quote_request`
- 输入输出统一使用 JSON 对象
- 不得把待确认项伪装成可直接报价项
- 详细设计见：`设计与规范/quote_feasibility_check_skill 详细设计.md`

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_feasibility_check_skill/run.py" --input ".opencode/skills/quote_feasibility_check_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_feasibility_check_skill/run.py" --input ".opencode/skills/quote_feasibility_check_skill/examples/input.sample.json" --skip-schema-validation`

## 输入

```json
{
  "quote_request": {}
}
```

## 输出

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

## 指令

1. 检查输入是否包含 `quote_request`，并确认其为 JSON 对象。
2. 先做全局判断：是否存在候选项、是否存在关键阻断缺失、是否具备进入报价的最低条件。
3. 遍历 `candidate_items`，逐项判断属于 `quotable_items`、`tbc_items` 还是 `exclusions`。
4. 对每个待确认或排除项，输出明确原因，不要只给笼统结论。
5. 汇总判断结果，生成 `can_quote` 与 `quote_scope`。
6. 输出影响判断的 `missing_fields`。
7. 把可以直接转化为后续提问的问题写入 `questions_for_user`。
8. 把审核方需要关注的范围风险写入 `review_flags`。
9. 返回结构化结果，不输出金额、不输出 `quotation_options`、不输出最终报价文档。

## 输出要求

- `quotable_items`、`tbc_items`、`exclusions` 应使用统一结构
- `quote_scope` 必须只取 `full`、`partial`、`not_ready`
- `questions_for_user` 应可直接转为后续澄清动作
- `review_flags` 应聚焦审核风险，而不是重复普通缺失项

推荐结构见：`references/FEASIBILITY_CONTRACT.md`

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`

## 错误处理

### 缺少 quote_request

- 不要继续做伪判断
- 返回保守结果：`can_quote = false`，`quote_scope = not_ready`
- 同时输出高严重度 `missing_fields`

### quote_request 缺少 candidate_items

- 通常不能进入稳定报价
- 应输出 `not_ready` 或极保守的 `partial`

### 存在大量待确认项

- 不要强行归到 `quotable_items`
- 应输出 `partial` 或 `not_ready`
- 同时生成 `review_flags`

## 示例

### 输入

```json
{
  "quote_request": {
    "service_context": {
      "service_mode": "voyage_repair",
      "location_type": "port"
    },
    "candidate_items": [
      {
        "item_id": "svc-1",
        "item_type": "service",
        "title": "AE-1 crankshaft trueness checks in place",
        "description": "Working time abt 15 hours",
        "work_scope": [
          "2pcs M/B lower bearing remove"
        ]
      },
      {
        "item_id": "spr-1",
        "item_type": "spare_parts",
        "title": "Main bearing spare parts",
        "description": "",
        "work_scope": []
      }
    ],
    "spare_parts_context": {
      "spare_parts_supply_mode": null
    }
  }
}
```

### 输出

```json
{
  "can_quote": true,
  "quote_scope": "partial",
  "quotable_items": [
    {
      "item_id": "svc-1",
      "item_type": "service",
      "title": "AE-1 crankshaft trueness checks in place",
      "decision": "quotable",
      "reason": "服务项标题和范围已基本明确，可进入报价。",
      "blocking_fields": [],
      "suggested_status": "chargeable",
      "source": "quote_request.candidate_items"
    }
  ],
  "tbc_items": [
    {
      "item_id": "spr-1",
      "item_type": "spare_parts",
      "title": "Main bearing spare parts",
      "decision": "tbc",
      "reason": "备件供货责任未确认，当前只能待确认。",
      "blocking_fields": [
        "spare_parts_context.spare_parts_supply_mode"
      ],
      "suggested_status": "pending",
      "source": "quote_request.candidate_items"
    }
  ],
  "exclusions": [],
  "missing_fields": [],
  "questions_for_user": [],
  "review_flags": []
}
```

完整示例见：`references/EXAMPLES.md`

## 常见问题

### 这个 Skill 会直接生成报价金额吗？

不会。这属于 `quote_pricing_skill`。

### 这个 Skill 会直接生成最终报价单吗？

不会。它只负责判断可报价范围和输出审核/提问信息。

### 待确认项是否等于排除项？

不等于。待确认项在补充信息后仍可能进入报价。
