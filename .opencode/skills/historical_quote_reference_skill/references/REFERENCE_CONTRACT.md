# Reference Contract

## 目的

定义 `historical_quote_reference_skill` 的输入输出推荐结构。

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

## matches 推荐结构

```json
{
  "quote_id": "",
  "similarity": 0.0,
  "reason": "",
  "matched_features": [],
  "reference_items": [],
  "reference_remarks": []
}
```

## reference_summary 推荐结构

```json
{
  "price_range_hint": {
    "currency": null,
    "min": null,
    "max": null,
    "sample_size": 0
  },
  "common_items": [],
  "remark_patterns": [],
  "recommended_reference_ids": []
}
```
