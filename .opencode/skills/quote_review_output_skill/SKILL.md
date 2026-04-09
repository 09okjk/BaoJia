---
name: quote_review_output_skill
description: 基于 quote_request、feasibility_result、historical_reference 和 pricing_result 生成最终 quote_document，补齐固定 header、table_schema、footer、review_result 与 trace。当用户提到最终报价 JSON、QuoteDocument 输出、footer 生成、review_result、trace 时使用。
---

# quote_review_output_skill

## 何时使用此 Skill

在以下场景使用：

- 已经有 `pricing_result`
- 需要生成最终 `QuoteDocument`
- 需要补齐 `header`、`table_schema`、`footer`
- 需要生成 `review_result` 和 `trace`

不要在以下场景使用：

- 还没有完成正文 `quotation_options` 生成
- 还在做可报价判断或历史检索

## 前提条件

- 必须存在 `pricing_result`
- 输入输出统一使用 JSON 对象
- 最终输出必须满足 `quote-document-v1.1.schema.json`
- 详细设计见：`设计与规范/quote_review_output_skill 详细设计.md`

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_review_output_skill/run.py" --input ".opencode/skills/quote_review_output_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_review_output_skill/run.py" --input ".opencode/skills/quote_review_output_skill/examples/input.sample.json" --skip-schema-validation`

## 输入

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

## 输出

```json
{
  "quote_document": {}
}
```

## 指令

1. 检查输入是否包含 `pricing_result`，并确认其为 JSON 对象。
2. 从 `quote_request` 生成固定 `header`。
3. 生成固定 `table_schema`。
4. 复用 `pricing_result.quotation_options`。
5. 生成 `footer.summary`、`footer.remark`、`footer.service_payment_terms`。
6. 聚合生成 `review_result`。
7. 聚合生成 `trace`。
8. 组装最终 `quote_document`，不要输出任何 Schema 之外的字段。

## 输出要求

- `quote_document.document_type` 必须为 `quotation`
- `quote_document` 顶层字段必须完整
- `header` 固定 13 字段必须全部输出
- `footer`、`review_result`、`trace` 不能省略

推荐结构见：`references/OUTPUT_CONTRACT.md`

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`

## 错误处理

### 缺少 pricing_result

- 不要伪造最终报价文档
- 返回空或失败结构时，也应显式说明缺失来源

### quotation_options 为空

- 通常不应输出正式报价文档
- 除非业务明确允许空报价文档

### header 信息缺失

- 仍需输出固定 13 字段
- 缺失字段用空字符串占位

## 示例

### 输入

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

### 输出

```json
{
  "quote_document": {
    "document_type": "quotation",
    "document_version": "1.1"
  }
}
```

完整示例见：`references/EXAMPLES.md`

## 常见问题

### 这个 Skill 会重新计算金额吗？

不会。它主要负责最终组装。

### 这个 Skill 会重新生成 quotation_options 吗？

不会。它优先复用 `pricing_result.quotation_options`。

### 为什么 review_result 和 trace 不能省略？

因为它们是最终 QuoteDocument 的正式组成部分。
