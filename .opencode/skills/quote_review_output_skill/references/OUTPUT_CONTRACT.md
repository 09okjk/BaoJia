# Output Contract

## 目的

定义 `quote_review_output_skill` 的最终输出结构。

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

## 关键约束

- `quote_document` 顶层必须包含：
  - `document_type`
  - `document_version`
  - `header`
  - `table_schema`
  - `quotation_options`
  - `footer`
  - `review_result`
  - `trace`
- `document_type` 必须为 `quotation`
- `header` 固定 13 字段必须全部存在
- `footer.remark.title` 必须为 `Remark`
- `footer.service_payment_terms.title` 必须为 `Service Payment Terms`
