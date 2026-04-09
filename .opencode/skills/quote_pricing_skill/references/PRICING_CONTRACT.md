# Pricing Contract

## 目的

定义 `quote_pricing_skill` 的输入输出推荐结构。

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

## 关键约束

- `quotation_options[*]` 必须包含：`option_id`、`title`、`sections`、`summary`、`remarks`
- `section.section_type` 仅允许：`service`、`spare_parts`、`other`
- `line` 必须带齐完整字段
- `summary` 必须包含：`service_charge`、`spare_parts_fee`、`other`、`total`
- 不允许 group 级 summary
