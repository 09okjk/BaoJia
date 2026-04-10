# `quote_review_output_skill` 详细设计

## 1. 文档目的

本文用于细化第五个 Skill：`quote_review_output_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》和 `quote-document-v1.1.schema.json` 中以下约束：

- 第五个 Skill 的目标是“生成最终 QuoteDocument，补齐 footer、remark、payment terms、review_result 与 trace”
- 最终输出必须满足 `quote-document-v1.1.schema.json`
- `footer`、`review_result`、`trace` 是正式输出的一部分，不是可选元数据
- 多方案场景下，本 Skill 必须决定 `footer.summary` 的生成策略

---

## 2. Skill 定位

`quote_review_output_skill` 是智能报价链路中的最终组装与审核输出层。

它接收前四个 Skill 的结构化结果，生成最终 `quote_document`。

它回答的核心问题是：

1. 如何把已有中间结构拼装为最终 QuoteDocument
2. 如何补齐固定 `header`
3. 如何生成固定 `table_schema`
4. 如何生成 `footer.summary`、`footer.remark`、`footer.service_payment_terms`
5. 如何生成 `review_result` 与 `trace`

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `quote_request`、`feasibility_result`、`historical_reference`、`pricing_result`
- 输出最终 `quote_document`
- 补齐 `header`
- 补齐固定 `table_schema`
- 生成 `footer`
- 生成 `review_result`
- 生成 `trace`

## 3.2 非目标

以下内容不属于本 Skill：

- 不重新计算报价金额
- 不重新生成 `quotation_options`
- 不重新做可报价判断
- 不重新做历史案例检索

本 Skill 主要负责最终文档拼装与审阅层信息补齐。

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 接收：

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

## 4.2 下游输出

本 Skill 输出最终：

```json
{
  "quote_document": {}
}
```

此结构应可直接用于后续渲染、导出或系统集成。

---

## 5. 设计原则

## 5.1 最终输出必须严格服从 Schema

该 Skill 是最终结构把关层，不能再输出任何额外字段。

## 5.2 中间结果优先复用，不重算

优先复用前四个 Skill 的输出，而不是在本层重写判断或重做定价。

## 5.3 表头与表尾必须固定

`header`、`table_schema`、`footer` 的固定约束必须在本层统一兜底。

## 5.4 审核与追溯信息必须显式输出

`review_result` 和 `trace` 是正式文档组成部分，不能省略。

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

## 6.2 输入字段要求

### `quote_request`

提供最终 header 生成所需的基础上下文。

### `feasibility_result`

提供审核提示来源，例如：

- `review_flags`
- `missing_fields`

### `historical_reference`

提供 trace 中的历史引用信息。

### `pricing_result`

提供最终正文 `quotation_options`。

若 `pricing_result.quotation_options` 缺失，本 Skill 不应伪造最终报价文档。

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "quote_document": {}
}
```

## 7.2 `quote_document` 顶层结构

必须包含：

- `document_type`
- `document_version`
- `header`
- `table_schema`
- `quotation_options`
- `footer`
- `review_result`
- `trace`

---

## 8. 关键模块设计

## 8.1 Header 生成

根据 `quote_request.header_context` 映射最终 `header`。

注意：

- 最终 header 是固定 13 字段
- 即使信息缺失，也必须输出空字符串
- `date` 必须映射到 header 的 `date`

## 8.2 Table Schema 生成

本 Skill 固定输出 7 列，顺序必须为：

1. `item`
2. `description`
3. `unit_price`
4. `unit`
5. `qty`
6. `discount`
7. `amount`

## 8.3 Footer 生成

`footer` 必须包含：

- `summary`
- `remark`
- `service_payment_terms`

### `footer.summary`

第一版建议：

- 单方案：复用第一个 option 的 summary
- 多方案：保守输出 `status` 或文本型 summary，避免误导为单一总价

### `footer.remark`

建议来源：

- `pricing_result.quotation_options[*].remarks`
- `quote_request.commercial_context.special_terms`
- 默认商务条款模板

### `footer.service_payment_terms`

第一版可从默认模板或规则配置生成。

## 8.4 Review Result 生成

第一版建议聚合：

- `feasibility_result.review_flags`
- 高风险 `missing_fields`

并生成：

- `review_flags`
- `risk_flags`
- `approval_level`

## 8.5 Trace 生成

第一版建议输出：

- `historical_references`
- `pricing_basis`
- `rule_versions`

---

## 9. 处理流程设计

建议流程如下：

```text
1. 检查输入完整性
2. 生成固定 header
3. 生成固定 table_schema
4. 复用 pricing_result.quotation_options
5. 生成 footer
6. 生成 review_result
7. 生成 trace
8. 组装为 quote_document
```

---

## 10. 示例

## 10.1 示例输入

```json
{
  "quote_request": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {}
}
```

## 10.2 示例输出

```json
{
  "quote_document": {
    "document_type": "quotation",
    "document_version": "1.1"
  }
}
```

---

## 11. MVP 开发建议

第一版建议先做以下能力：

1. 生成固定 `header`
2. 生成固定 `table_schema`
3. 复用 `pricing_result.quotation_options`
4. 生成基础 `footer`
5. 生成基础 `review_result`
6. 生成基础 `trace`

第一版可以暂不做：

- 多方案 footer summary 优化
- 高级 approval_level 规则
- 更复杂的 remark 去重与归类

---

## 12. 验收标准

当本 Skill 达到以下效果时，可视为设计目标基本满足：

1. 能稳定消费前四个 Skill 的输出
2. 能输出符合 `quote-document-v1.1.schema.json` 的最终 `quote_document`
3. 能补齐固定 `header`、`table_schema`、`footer`
4. 能输出 `review_result` 与 `trace`
5. 不遗漏任何最终正式输出字段

---

## 13. 后续优化与增强建议

- 优化多方案 footer summary 生成策略
- 优化 remark 去重、归类和模板化输出
- 优化 approval_level 计算规则
- 细化 trace 的定价依据和规则版本来源

---

## 14. 历史参考增强后的组装与审核方向

### 14.1 当前约束

即使后续增强历史参考能力，本 Skill 仍然不能：

- 重新计算金额
- 重新做历史检索
- 重新生成 `quotation_options`

本 Skill 只负责复用上游结果并把“历史依据”更清晰地表达在最终文档里。

### 14.2 后续推荐增强点

#### A. remark 组装优先使用结构化历史块

若 `historical_reference.reference_summary` 后续增加结构化 `remark_blocks`，本 Skill 应：

1. 优先按类型合并：
- `warranty`
- `waiting`
- `safety`
- `payment_term`
- `commercial`

2. 再与以下来源做去重：
- `pricing_result.quotation_options[*].remarks`
- `quote_request.commercial_context.special_terms`
- 默认 remark 模板

目标：
- 避免 footer remark 只是若干历史自由文本拼接。

#### B. review_result 增加历史参考质量提示

若历史摘要后续输出 `history_quality_flags`，本 Skill 可在 `review_result.review_flags` 中增加如下提醒：

- 历史样本数量不足
- 当前项目与历史案例相似度偏弱
- 历史价格区间过宽，参考价值有限

目标：
- 让审核人知道“当前报价对历史的依赖程度”和“历史参考是否可信”。

#### C. trace 更精确表达历史使用方式

后续版本可在 `trace` 中更细地表达：

1. 历史命中结果
2. 历史摘要被用于哪些模块
3. 历史只参与了 remark / fallback / option style 哪一类决策

推荐方向：
- `pricing_basis` 更明确区分：
  - `historical_price_range`
  - `historical_remark_block`
  - `historical_charge_item_hint`
  - `historical_option_style_hint`

### 14.3 建议的落地顺序

第一阶段：
- 增加历史质量相关 review flag
- 增加 trace 中的历史使用分类

第二阶段：
- 使用结构化 `remark_blocks` 改善 footer remark 组装

第三阶段：
- 根据历史增强后的 option style 来源，优化 review 审批提示

### 14.4 验收重点

1. 最终 `quote_document` 仍严格符合 QuoteDocument Schema
2. `review_result` 能明确提示历史参考是否可靠
3. `trace` 能回答“历史参考到底被用在了哪里”
4. remark 组装更像真实报价单，而不是自由文本拼接
