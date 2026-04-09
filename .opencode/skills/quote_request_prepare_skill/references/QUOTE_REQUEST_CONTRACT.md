# Quote Request Contract

## 目的

定义 `quote_request_prepare_skill` 的核心输出 `quote_request` 推荐结构，供实现和联调使用。

## 推荐结构

```json
{
  "request_meta": {
    "request_id": "",
    "source": "assessment_report",
    "prepared_at": "",
    "language": "zh-CN"
  },
  "header_context": {
    "currency": null,
    "vessel_name": null,
    "imo_no": null,
    "vessel_type": null,
    "customer_name": null,
    "service_port": null,
    "service_date": null,
    "attention": null,
    "customer_ref_no": null
  },
  "service_context": {
    "service_category": null,
    "service_mode": null,
    "location_type": null,
    "needs_multi_option": false,
    "option_hints": [],
    "urgency": null
  },
  "candidate_items": [],
  "spare_parts_context": {
    "has_spare_parts": null,
    "spare_parts_supply_mode": null,
    "spare_parts_items": []
  },
  "risk_context": {
    "risks": [],
    "pending_confirmations": [],
    "assumptions": []
  },
  "commercial_context": {
    "preferred_currency": null,
    "pricing_expectation": null,
    "special_terms": []
  },
  "source_refs": {
    "assessment_report_id": null,
    "customer_context_ref": null,
    "business_context_ref": null
  }
}
```

## 字段说明

### request_meta

- 记录准备动作本身的信息
- 用于追溯，但不参与报价计算

### header_context

- 面向未来 `QuoteDocument.header`
- 仅保留事实值，不做渲染文案

### service_context

- 承接服务类别、服务方式、地点类型、多方案线索
- 服务后续可报价判断、历史检索、定价

### candidate_items

- 是“候选报价项”而不是最终 `line`
- 允许粒度略粗，但必须足够支撑后续拆分 `section/group/line`

### spare_parts_context

- 独立承接备件相关事实
- 避免服务项与备件项在输入阶段混淆

### risk_context

- 集中表达风险、待确认事项、假设条件
- 不把待确认项写散在多个字段中

### commercial_context

- 保存币种偏好、商务要求、价格预期等上下文

### source_refs

- 记录原始来源标识
- 供审计和追溯使用

## candidate_items 推荐结构

```json
{
  "item_id": "",
  "item_type": "service | spare_parts | other",
  "title": "",
  "description": "",
  "work_scope": [],
  "quantity_hint": null,
  "unit_hint": null,
  "labor_hint": [],
  "pricing_clues": [],
  "status_hint": null,
  "source": "assessment_report"
}
```

## 约束

- 未确认事实使用 `null`
- 不在本层生成最终报价状态
- 不在本层生成金额字段
- 不直接构造 QuoteDocument 的 `quotation_options`

## 正式 Schema

- 输入 Schema：`../schemas/input.schema.json`
- 输出 Schema：`../schemas/output.schema.json`
