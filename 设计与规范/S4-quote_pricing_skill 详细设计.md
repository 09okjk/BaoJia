# `quote_pricing_skill` 详细设计

## 1. 文档目的

本文用于细化第四个 Skill：`quote_pricing_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》与 `quote-document-v1.1.schema.json` 中以下约束：

- 第四个 Skill 的目标是“结合报价请求、可报价范围、历史参考与规则配置，生成正文报价结构与方案级 summary”
- 本 Skill 负责输出 `quotation_options`
- 本 Skill 不只负责计算金额，还负责将内容映射到固定模板中间表格结构
- `quotation_options`、`section`、`group`、`line`、`summary` 必须满足 QuoteDocument Schema 约束

---

## 2. Skill 定位

`quote_pricing_skill` 是智能报价链路中的正文建模与定价层。

它接收：

- `quote_request`
- `feasibility_result`
- `historical_reference`
- `pricing_rules`

并输出符合 QuoteDocument 中间结构要求的 `quotation_options`。

它回答的核心问题是：

1. 本次报价应形成一个方案还是多个方案
2. 各项内容应如何映射为 `section / group / line`
3. 每一行的 `line_type`、`pricing_mode`、`status`、`discount`、`amount` 应如何表达
4. 每个 option 的 `summary` 应如何生成

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `quote_request`、`feasibility_result`、`historical_reference`、`pricing_rules`
- 输出单方案或多方案 `quotation_options`
- 输出 `section / group / line` 结构
- 输出 line 的状态、折扣、金额、展示字段
- 输出 option 级 `summary`

## 3.2 非目标

以下内容不属于本 Skill：

- 不生成最终 `QuoteDocument`
- 不生成固定 `header`
- 不生成最终 `footer`
- 不生成最终 `review_result` 与 `trace`
- 不把 group summary 私自加入结构中

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 接收：

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

## 4.2 下游输出

本 Skill 直接服务于：

1. `quote_review_output_skill`

下游将直接复用 `quotation_options` 作为最终报价文档主体。

---

## 5. 设计原则

## 5.1 以 QuoteDocument Schema 为准

本 Skill 的输出不是任意“报价草稿”，而是必须向最终 `quotation_options` 结构靠拢。

## 5.2 结构建模优先于金额精度

第一版实现优先保证 `section / group / line / summary` 结构正确，再逐步增强定价精度。

## 5.3 不确定状态必须结构化表达

对待确认、额外收费、按实际结算、船东提供等情况，优先用：

- `line_type`
- `pricing_mode`
- `status`
- `amount_display`

显式表达，不能用自由文本硬塞进 `description`。

## 5.4 不支持 group 级 summary

根据 Schema 和设计说明，汇总只放在 option summary，不得在 group 层补私有字段。

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_rules": {}
}
```

## 6.2 输入字段要求

### `quote_request`

提供基础上下文、候选项和商务偏好。

### `feasibility_result`

提供：

- `quote_scope`
- `quotable_items`
- `tbc_items`
- `exclusions`

### `historical_reference`

提供：

- `matches`
- `reference_summary`

### `pricing_rules`

第一版建议至少支持：

- `currency`
- `service_rates`
- `lump_sum_overrides`
- `remark_hints`
- `multi_option_mode`

若规则缺失，第一版允许输出保守的 `pending` / `as_actual` 结构，而不是伪造金额。

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "quotation_options": []
}
```

## 7.2 `quotation_options` 结构要求

每个 option 必须满足以下字段：

- `option_id`
- `title`
- `sections`
- `summary`
- `remarks`

其中：

- `sections[].section_type` 只允许 `service`、`spare_parts`、`other`
- `group` 不允许自定义 summary 字段
- `line` 必须带齐所有 Schema 要求的完整字段

---

## 8. 推荐建模策略

## 8.1 Option 生成策略

第一版建议：

- 默认输出单方案 `Option 1`
- 当 `quote_request.service_context.needs_multi_option = true` 或 `pricing_rules.multi_option_mode = true` 时，可输出双方案

## 8.2 Section 映射策略

建议映射如下：

- 可报价服务项 -> `service` section
- 可报价备件项 -> `spare_parts` section
- 其他费用或说明 -> `other` section

## 8.3 Group 映射策略

第一版可采用“一项一组”的保守策略：

- 每个报价项生成一个 group
- `group_no` 可用 `1`、`2`、`3`
- `description` 保留原始项描述摘要

## 8.4 Line 映射策略

### 可报价项

优先映射为：

- `line_type = priced`
- `pricing_mode = lump_sum` 或 `unit_price`
- `status = chargeable`

### 待确认项

优先映射为：

- `line_type = pending`
- `pricing_mode = pending`
- `status = pending`
- `amount_display = Pending`

### 船东提供或排除项

优先映射为：

- `line_type = note` 或 `included` / `conditional` 的保守结构
- `pricing_mode = text_only` 或 `included`
- `status = by_owner` 或 `excluded`

### 额外收费 / 按实际

优先映射为：

- `status = extra` / `as_actual`
- `amount_display = Extra` / `As actual`

---

## 9. Summary 生成规则

每个 option 的 `summary` 必须包含：

- `service_charge`
- `spare_parts_fee`
- `other`
- `total`

### 第一版建议规则

- 若当前行均可计算金额，则 `value_type = amount`
- 若存在待确认阻断，可输出 `value_type = status` 与 `display = Pending`
- 若为纯文本说明，可输出 `value_type = text`

---

## 10. 处理流程设计

建议流程如下：

```text
1. 检查输入结构完整性
2. 读取 quotable_items / tbc_items / exclusions
3. 确定单方案或多方案
4. 生成 sections
5. 生成 groups
6. 生成 lines
7. 计算或映射 summary
8. 输出 quotation_options
```

---

## 11. 示例

## 11.1 示例输入

```json
{
  "quote_request": {},
  "feasibility_result": {
    "quotable_items": [
      {
        "item_id": "svc-1",
        "item_type": "service",
        "title": "AE-1 crankshaft trueness checks in place",
        "decision": "quotable",
        "suggested_status": "chargeable"
      }
    ],
    "tbc_items": [
      {
        "item_id": "spr-1",
        "item_type": "spare_parts",
        "title": "Main bearing spare parts",
        "decision": "tbc",
        "suggested_status": "pending"
      }
    ]
  },
  "historical_reference": {
    "reference_summary": {
      "price_range_hint": {
        "currency": "USD",
        "min": 3200.0,
        "max": 3800.0
      }
    }
  },
  "pricing_rules": {
    "currency": "USD",
    "lump_sum_overrides": {
      "svc-1": 3500.0
    }
  }
}
```

## 11.2 示例输出

```json
{
  "quotation_options": [
    {
      "option_id": "option-1",
      "title": "Option 1",
      "sections": [],
      "summary": {},
      "remarks": []
    }
  ]
}
```

---

## 12. MVP 开发建议

第一版建议先做以下能力：

1. 输出单方案 `quotation_options`
2. 支持 `service` / `spare_parts` / `other` 三类 section
3. 支持可报价行、待确认行、排除/船东提供行的基本建模
4. 支持保守的 lump sum 金额或 `Pending` 文本展示
5. 输出 option 级 summary

第一版可以暂不做：

- 复杂多方案建模
- 折扣策略优化
- 高级费率规则组合
- relation 关系建模

---

## 13. 验收标准

当本 Skill 达到以下效果时，可视为设计目标基本满足：

1. 能稳定消费前 3 个 Skill 的结构化输出
2. 能输出符合 QuoteDocument Schema 要求的 `quotation_options`
3. 能显式表达 pending / by_owner / extra / as_actual 等状态
4. 能生成 option 级 summary
5. 不越界生成最终 `header` / `footer` / `review_result` / `trace`

---

## 14. 后续优化与增强建议

- 增加多方案建模策略
- 增加更细粒度折扣对象生成
- 增加 rate-based 定价与按实际规则
- 增加 relation 建模支持
- 增加更丰富的 pricing_rules 外置配置能力
