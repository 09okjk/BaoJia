# Examples

## 基本示例

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

## 边缘情况

### quotable_items 为空

处理要求：

- 允许继续检索
- `confidence` 应降低

### 历史样本库为空

处理要求：

- 返回空 `matches`
- 返回空摘要
- `confidence = 0.0`
