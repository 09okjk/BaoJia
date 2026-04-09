# Examples

## 基本示例

### 输入

```json
{
  "assessment_report": {
    "vessel_name": "MV EXAMPLE",
    "imo_no": "1234567",
    "customer_name": "ABC Shipping",
    "service_port": "Zhapu Port, China",
    "service_items": [
      {
        "title": "AE-1 crankshaft trueness checks in place",
        "details": [
          "Working time abt 15 hours",
          "2pcs M/B lower bearing remove",
          "Crankshaft run-out check by magnetic gauge"
        ]
      }
    ],
    "pending_items": [
      "Whether spare parts are owner supply"
    ]
  },
  "customer_context": {
    "currency": "USD"
  },
  "business_context": {
    "service_mode": "voyage repair"
  }
}
```

### 输出

```json
{
  "quote_request": {
    "request_meta": {
      "request_id": "qr-0001",
      "source": "assessment_report",
      "prepared_at": "2026-04-09T10:00:00Z",
      "language": "zh-CN"
    },
    "header_context": {
      "currency": "USD",
      "vessel_name": "MV EXAMPLE",
      "imo_no": "1234567",
      "vessel_type": null,
      "customer_name": "ABC Shipping",
      "service_port": "Zhapu Port, China",
      "service_date": null,
      "attention": null,
      "customer_ref_no": null
    },
    "service_context": {
      "service_category": "service",
      "service_mode": "voyage_repair",
      "location_type": "port",
      "needs_multi_option": false,
      "option_hints": [],
      "urgency": null
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
        ],
        "quantity_hint": null,
        "unit_hint": null,
        "labor_hint": [],
        "pricing_clues": [],
        "status_hint": null,
        "source": "assessment_report"
      }
    ],
    "spare_parts_context": {
      "has_spare_parts": null,
      "spare_parts_supply_mode": null,
      "spare_parts_items": []
    },
    "risk_context": {
      "risks": [],
      "pending_confirmations": [
        "Whether spare parts are owner supply"
      ],
      "assumptions": []
    },
    "commercial_context": {
      "preferred_currency": "USD",
      "pricing_expectation": null,
      "special_terms": []
    },
    "source_refs": {
      "assessment_report_id": null,
      "customer_context_ref": null,
      "business_context_ref": null
    }
  },
  "normalization_flags": [
    {
      "flag_code": "normalized_service_mode",
      "field": "service_context.service_mode",
      "from": "voyage repair",
      "to": "voyage_repair",
      "reason": "统一服务模式枚举"
    }
  ],
  "missing_fields": [
    {
      "field": "header_context.vessel_type",
      "required_for": ["pricing", "quote_document"],
      "severity": "medium",
      "reason": "船型缺失，可能影响历史参考和表头完整性",
      "suggested_source": "assessment_report"
    }
  ]
}
```

## 边缘情况

### assessment_report 缺失

处理要求：

- 不生成看似完整的 `quote_request`
- 返回结构化错误或高严重度缺失项

### 只有部分表头信息

处理要求：

- 能提取的先提取
- 不能确认的字段填 `null`
- 缺失项进入 `missing_fields`

### 同一字段多来源冲突

处理要求：

- 按明确优先级归一
- 把处理过程写入 `normalization_flags`
