---
name: historical_quote_reference_skill
description: 基于 quote_request 和 quotable_items 检索相似历史报价案例，输出 matches、reference_summary 和 confidence。当用户提到历史报价参考、相似案例检索、价格带参考、remark 模式参考时使用。
---

# historical_quote_reference_skill

## 何时使用此 Skill

在以下场景使用：

- 已经有 `quote_request`
- 已经有 `quotable_items`
- 需要检索历史相似报价案例
- 需要形成价格带、常见项、remark 模式参考

不要在以下场景使用：

- 还没有完成可报价判断
- 已经进入最终金额计算和正文结构生成
- 需要直接生成最终报价单

## 前提条件

- 必须存在 `quote_request`
- 建议存在 `quotable_items`
- 输入输出统一使用 JSON 对象
- 详细设计见：`设计与规范/historical_quote_reference_skill 详细设计.md`

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/historical_quote_reference_skill/run.py" --input ".opencode/skills/historical_quote_reference_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/historical_quote_reference_skill/run.py" --input ".opencode/skills/historical_quote_reference_skill/examples/input.sample.json" --skip-schema-validation`

## 输入

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

## 输出

```json
{
  "matches": [],
  "reference_summary": {},
  "confidence": 0.0
}
```

## 指令

1. 检查输入是否包含 `quote_request`，并确认输入为 JSON 对象。
2. 从 `quote_request` 和 `quotable_items` 提取检索特征，例如服务类别、服务模式、地点类型、项目标题。
3. 从历史样本库中检索相似案例。
4. 为每个候选历史案例计算相似度，并保留可解释的命中特征。
5. 输出 Top N 匹配结果到 `matches`。
6. 聚合历史结果，输出 `reference_summary`。
7. 根据匹配质量和样本充分性输出保守的 `confidence`。
8. 返回结构化结果，不直接输出最终报价金额，不生成 `quotation_options` 或 `QuoteDocument`。

## 输出要求

- `matches` 中每条结果都应说明“为什么相似”
- `reference_summary.price_range_hint` 仅作参考，不得视为最终报价结论
- `confidence` 范围必须在 `0.0` 到 `1.0` 之间

推荐结构见：`references/REFERENCE_CONTRACT.md`

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`

## 错误处理

### 缺少 quote_request

- 不要继续检索
- 返回空 `matches`、空摘要和低置信度结果

### quotable_items 为空

- 允许继续检索，但应降低 `confidence`
- 结果更多依赖全局场景特征，可靠性较低

### 历史样本库为空

- 返回空 `matches`
- `reference_summary` 保持空结构
- `confidence` 设为 `0.0`

## 示例

### 输入

```json
{
  "quote_request": {
    "service_context": {
      "service_category": "service",
      "service_mode": "voyage_repair",
      "location_type": "port"
    }
  },
  "quotable_items": [
    {
      "item_id": "svc-1",
      "item_type": "service",
      "title": "AE-1 crankshaft trueness checks in place"
    }
  ]
}
```

### 输出

```json
{
  "matches": [
    {
      "quote_id": "hist-001",
      "similarity": 0.82,
      "reason": "服务模式、地点类型和核心服务项高度相似。",
      "matched_features": [
        "service_mode: voyage_repair",
        "location_type: port",
        "item_title: AE-1 crankshaft trueness checks"
      ],
      "reference_items": [
        "AE-1 crankshaft trueness checks in place"
      ],
      "reference_remarks": [
        "Other repair if needed to be charged extra"
      ]
    }
  ],
  "reference_summary": {
    "price_range_hint": {
      "currency": "USD",
      "min": 3200.0,
      "max": 3800.0,
      "sample_size": 2
    },
    "common_items": [
      "AE-1 crankshaft trueness checks in place"
    ],
    "remark_patterns": [
      "Other repair if needed to be charged extra"
    ],
    "recommended_reference_ids": [
      "hist-001"
    ]
  },
  "confidence": 0.82
}
```

完整示例见：`references/EXAMPLES.md`

## 常见问题

### 这个 Skill 会直接决定报价金额吗？

不会。它只提供历史参考。

### 这个 Skill 会直接生成 remark 吗？

不会。它只提供 remark 模式参考。

### 历史参考为空是否代表不能报价？

不代表。只表示当前缺少可用历史参考，后续仍可按规则和业务事实定价。
