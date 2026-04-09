# Examples

## 基本示例

### 输入

```json
{
  "quote_request": {
    "service_context": {
      "service_mode": "voyage_repair",
      "location_type": "port",
      "needs_multi_option": false
    },
    "candidate_items": [
      {
        "item_id": "svc-1",
        "item_type": "service",
        "title": "AE-1 crankshaft trueness checks in place",
        "description": "Working time abt 15 hours",
        "work_scope": [
          "2pcs M/B lower bearing remove",
          "Crankshaft run-out check by magnetic gauge"
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
    },
    "risk_context": {
      "pending_confirmations": [
        "Whether spare parts are owner supply"
      ]
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
  "missing_fields": [
    {
      "field": "spare_parts_context.spare_parts_supply_mode",
      "required_for": ["feasibility_check", "pricing"],
      "severity": "medium",
      "reason": "备件供货责任未确认，影响是否纳入报价。",
      "suggested_source": "customer_context"
    }
  ],
  "questions_for_user": [
    {
      "question_id": "q-1",
      "target": "customer",
      "topic": "spare_parts_supply_mode",
      "question": "Main bearing spare parts 由船东提供还是由我司供货？",
      "related_item_ids": [
        "spr-1"
      ]
    }
  ],
  "review_flags": [
    {
      "flag_code": "partial_quote_scope",
      "severity": "medium",
      "message": "当前仅部分项目具备报价条件。",
      "related_item_ids": [
        "svc-1",
        "spr-1"
      ]
    }
  ]
}
```

## 边缘情况

### quote_request 缺失

处理要求：

- 输出 `can_quote = false`
- 输出 `quote_scope = not_ready`
- 输出高严重度缺失项

### candidate_items 为空

处理要求：

- 不要制造可报价项
- 通常输出 `not_ready`

### 责任边界明确归船东或第三方

处理要求：

- 进入 `exclusions`，不要放入 `tbc_items`
