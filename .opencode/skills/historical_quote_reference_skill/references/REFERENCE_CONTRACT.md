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
  "recommended_reference_ids": [],
  "item_clusters": [],
  "remark_blocks": [],
  "charge_item_hints": [],
  "option_style_hints": [],
  "history_quality_flags": []
}
```

## 派生摘要说明

- `item_clusters`: 基于历史 `items` 文本归一化后的常见项目簇，仅供下游识别常见项模式。
- `remark_blocks`: 基于历史 `remarks` 的类型化归类结果，仅供下游组装 remark。
- `charge_item_hints`: 基于历史 `items` / `remarks` 文本推断出的常见附加费用线索，不是最终收费结论。
- `option_style_hints`: 基于历史文本推断出的常见方案风格线索，例如 `owner_supply_spares`。
- `history_quality_flags`: 对当前历史参考质量的保守标记，用于提醒下游不要过度依赖历史。
