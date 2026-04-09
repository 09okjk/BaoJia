---
name: quote_request_prepare_skill
description: 将智能评估单、客户补充信息、业务补充信息标准化为统一的 quote_request。当用户提到评估单转报价请求、标准化报价输入、提取待确认项、整理报价上下文、准备后续报价链路输入时使用。
---

# quote_request_prepare_skill

## 何时使用此 Skill

在以下场景使用：

- 需要把 `assessment_report` 转成统一 `quote_request`
- 需要从评估单中提取报价相关事实
- 需要标准化服务项、服务场景、备件上下文
- 需要输出 `missing_fields` 和 `normalization_flags`
- 需要为 `quote_feasibility_check_skill`、`historical_quote_reference_skill`、`quote_pricing_skill` 准备稳定输入

不要在以下场景使用：

- 已经进入可报价范围判断
- 已经进入历史报价检索
- 已经进入金额计算、折扣计算、summary 生成
- 已经进入最终 `QuoteDocument` 组装

## 前提条件

- 必须存在 `assessment_report`
- 输入输出统一使用 JSON 对象
- 不得默认补全缺失业务事实
- 若设计说明与其他文档冲突，以 `quote-document-v1.1.schema.json` 和 `设计与规范/智能报价 Agent Skill 设计说明书.md` 为准

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_request_prepare_skill/run.py" --input ".opencode/skills/quote_request_prepare_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_request_prepare_skill/run.py" --input ".opencode/skills/quote_request_prepare_skill/examples/input.sample.json" --skip-schema-validation`

详细设计见：`设计与规范/quote_request_prepare_skill 详细设计.md`

## 输入

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {}
}
```

## 输出

```json
{
  "quote_request": {},
  "normalization_flags": [],
  "missing_fields": []
}
```

## 指令

1. 检查输入是否包含 `assessment_report`，并确认三类输入均为 JSON 对象。
2. 提取基础报价事实：船舶信息、客户信息、服务地点、时间、币种。
3. 提取服务相关事实：服务类别、服务模式、地点类型、是否存在多方案线索。
4. 提取候选报价项，输出为 `candidate_items`，只保留候选结构，不直接生成 `section/group/line`。
5. 提取备件相关事实，单独放入 `spare_parts_context`，不要与服务项混写。
6. 提取风险、待确认事项、假设条件，统一写入 `risk_context`。
7. 对可归一化字段做标准化，并把每一次标准化动作记录到 `normalization_flags`。
8. 识别缺失关键字段，写入 `missing_fields`，不要猜测补全。
9. 组装统一的 `quote_request`，保证下游 Skill 可以直接消费。
10. 返回结构化结果，不输出报价结论、不输出金额、不输出最终报价文档。

## 输出要求

- `quote_request` 必须稳定、可复用、可追溯
- `normalization_flags` 建议使用对象数组，而不是纯字符串
- `missing_fields` 建议包含 `field`、`required_for`、`severity`、`reason`、`suggested_source`
- 无法确认的事实使用 `null` 或空数组显式表达
- 禁止把待确认事实伪装成已确认事实

`quote_request` 推荐结构见：`references/QUOTE_REQUEST_CONTRACT.md`

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`
- 最小校验脚本：`validate_samples.py`

## 错误处理

### 缺少 assessment_report

- 这是主输入缺失
- 不要继续生成看似完整的 `quote_request`
- 返回结构化失败结果，或至少输出高严重度 `missing_fields`

### 输入不是对象

- 不要尝试按自由文本硬解析为最终结构
- 先要求上游转换为 JSON 对象，或仅提取能明确识别的事实并标记高风险

### 信息不完整

- 允许继续输出部分 `quote_request`
- 必须把缺失点写入 `missing_fields`
- 不要在本 Skill 直接向用户发问，问题应留给后续可报价判断阶段汇总

### 多来源字段冲突

- 可以按明确优先级做归一
- 必须把冲突处理写入 `normalization_flags`
- 不要静默覆盖

## 示例

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
          "2pcs M/B lower bearing remove"
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
      "needs_multi_option": false
    },
    "candidate_items": [
      {
        "item_id": "svc-1",
        "item_type": "service",
        "title": "AE-1 crankshaft trueness checks in place",
        "description": "Working time abt 15 hours",
        "work_scope": [
          "2pcs M/B lower bearing remove"
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

完整示例见：`references/EXAMPLES.md`

## 常见问题

### 这个 Skill 能直接输出报价单吗？

不能。它只负责把输入整理成统一报价请求对象。

### 这个 Skill 能判断哪些项目可以报价吗？

不能。这属于 `quote_feasibility_check_skill` 的职责。

### 这个 Skill 能直接计算金额吗？

不能。金额、折扣、summary 由后续定价 Skill 负责。
