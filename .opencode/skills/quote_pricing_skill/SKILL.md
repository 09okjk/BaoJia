---
name: quote_pricing_skill
description: 基于 quote_request、feasibility_result、historical_reference 和 pricing_rules 生成符合固定模板中间结构的 quotation_options，并输出 section、group、line 与 option summary。当用户提到报价正文建模、单方案/多方案输出、报价项金额结构、option summary 时使用。
---

# quote_pricing_skill

## 何时使用此 Skill

在以下场景使用：

- 已经有 `quote_request`
- 已经有 `feasibility_result`
- 已经有 `historical_reference`
- 需要输出 `quotation_options`
- 需要把报价内容映射为 `section / group / line / summary`

不要在以下场景使用：

- 还没有完成可报价判断
- 还没有完成历史参考整理
- 需要直接生成最终 `QuoteDocument`

## 前提条件

- 必须存在 `quote_request`
- 必须存在 `feasibility_result`
- 输入输出统一使用 JSON 对象
- 详细设计见：`设计与规范/quote_pricing_skill 详细设计.md`

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pricing_skill/run.py" --input ".opencode/skills/quote_pricing_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pricing_skill/run.py" --input ".opencode/skills/quote_pricing_skill/examples/input.sample.json" --skip-schema-validation`

## 输入

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

## 输出

```json
{
  "quotation_options": []
}
```

## 指令

1. 检查输入结构完整性，确认存在 `quote_request` 和 `feasibility_result`。
2. 基于 `feasibility_result` 提取 `quotable_items`、`tbc_items`、`exclusions`。
3. 根据 `quote_request` 与 `pricing_rules` 判断输出单方案还是多方案。
4. 将项目映射为 `service`、`spare_parts`、`other` 三类 section。
5. 为每个项目生成 group 和完整 line 结构。
6. 对可定价项目生成金额字段；对待确认或排除项目生成结构化状态表达。
7. 生成 option 级 `summary`。
8. 返回 `quotation_options`，不要输出最终 `header`、`footer`、`review_result`、`trace`。

## 输出要求

- `quotation_options` 必须符合 `quote-document-v1.1.schema.json` 对相关子结构的约束
- 每条 `line` 必须带齐完整字段
- 不得输出 group 级 summary
- `status`、`line_type`、`pricing_mode` 必须显式表达不确定状态

推荐结构见：`references/PRICING_CONTRACT.md`

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`

## 错误处理

### 缺少 feasibility_result

- 不要继续伪造定价输出
- 返回空 `quotation_options`

### pricing_rules 缺失或不完整

- 允许继续输出保守结构
- 对无法计算金额的行优先使用 `pending` / `as_actual` / `text_only`

### historical_reference 为空

- 不阻断输出
- 只是不使用历史参考辅助金额或 remark 模式

## 示例

### 输入

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

### 输出

```json
{
  "quotation_options": [
    {
      "option_id": "option-1",
      "title": "Option 1",
      "sections": [],
      "summary": {},
      "remarks": []
    }
  ]
}
```

完整示例见：`references/EXAMPLES.md`

## 常见问题

### 这个 Skill 只负责算金额吗？

不是。它还负责把结果建模为 `quotation_options` 中间结构。

### 这个 Skill 会输出 footer 吗？

不会。footer 由下一个 Skill 负责。

### 待确认项如何表达？

应通过 `line_type`、`pricing_mode`、`status`、`amount_display` 等字段结构化表达，而不是只写自由文本。
