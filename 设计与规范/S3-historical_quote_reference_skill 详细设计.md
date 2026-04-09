# `historical_quote_reference_skill` 详细设计

## 1. 文档目的

本文用于细化第三个 Skill：`historical_quote_reference_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》中的以下约束：

- 第三个 Skill 的目标是“从历史报价数据库检索相似案例，并形成报价参考摘要”
- 各 Skill 之间统一使用 JSON 作为输入输出协议
- 本 Skill 提供报价参考，不直接输出金额结论或最终报价文档
- 历史参考应服务后续定价和审核，而不是替代规则计算

---

## 2. Skill 定位

`historical_quote_reference_skill` 是智能报价链路中的历史参考检索层。

它接收标准化后的 `quote_request` 和第二个 Skill 输出的 `quotable_items`，从历史报价样本中检索相似案例，并输出结构化参考结果。

它回答的核心问题是：

1. 当前报价任务和哪些历史案例相似
2. 历史上常见的报价项有哪些
3. 历史 remark / 商务条款模式有哪些
4. 当前历史参考结果的可信度大致如何

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `quote_request` 和 `quotable_items`
- 检索相似历史案例
- 输出 `matches`
- 输出 `reference_summary`
- 输出 `confidence`

## 3.2 非目标

以下内容不属于本 Skill：

- 不生成可报价判断
- 不计算最终金额
- 不生成 `quotation_options`
- 不生成最终 `QuoteDocument`
- 不直接决定 remark 最终写法

本 Skill 只提供“参考”，不输出最终定价结论。

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 接收：

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

其中：

- `quote_request` 来自第一个 Skill
- `quotable_items` 来自第二个 Skill

## 4.2 下游输出

本 Skill 直接服务于：

1. `quote_pricing_skill`
2. `quote_review_output_skill`

其中：

- `quote_pricing_skill` 依赖历史相似案例、价格带和常见项参考
- `quote_review_output_skill` 可复用历史引用信息生成 `trace`

---

## 5. 设计原则

## 5.1 历史参考是辅助，不是替代

历史案例只能作为参考输入，不能替代当前业务事实和规则计算。

## 5.2 结果必须结构化

不要只输出一段自由文本总结，应输出可被后续 Skill 消费的结构化对象。

## 5.3 相似性要可解释

历史匹配结果应能说明“为什么相似”，而不仅是给出一个 ID。

## 5.4 置信度必须保守

当历史样本不足、特征不充分时，`confidence` 应保守，不要人为拉高。

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

## 6.2 输入字段要求

### `quote_request`

至少应提供部分以下信息：

- `header_context`
- `service_context`
- `candidate_items`
- `commercial_context`

### `quotable_items`

应提供第二个 Skill 已判定可进入报价的项目列表。

若 `quotable_items` 为空，本 Skill 仍可运行，但应输出低置信度结果。

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "matches": [],
  "reference_summary": {},
  "confidence": 0.0
}
```

## 7.2 字段定义

### `matches`

历史匹配结果列表。

### `reference_summary`

对历史参考的聚合摘要。

### `confidence`

`0.0 - 1.0` 之间的置信度，用于表达当前历史参考结果的可靠程度。

---

## 8. 推荐数据结构

## 8.1 `matches`

推荐结构：

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

字段说明：

- `quote_id`：历史报价唯一标识
- `similarity`：相似度分值
- `reason`：简短说明为什么相似
- `matched_features`：命中的相似特征
- `reference_items`：可供后续参考的历史报价项标题
- `reference_remarks`：可供后续参考的历史 remark 文本

## 8.2 `reference_summary`

推荐结构：

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

说明：

- `price_range_hint`：仅提供区间参考，不直接形成最终报价金额
- `common_items`：历史常见报价项标题或模式
- `remark_patterns`：历史 remark 模板或常见表达
- `recommended_reference_ids`：建议优先参考的历史报价 ID

---

## 9. 检索规则设计

## 9.1 相似性判断维度

至少可从以下维度做相似性判断：

1. 服务类别
2. 服务模式
3. 地点类型或服务地点
4. 候选报价项标题
5. 船型或项目类型线索

## 9.2 基础检索策略

第一版建议采用可解释、可控的规则式检索：

- 先按服务类别和服务模式过滤
- 再按 `quotable_items` 标题做关键词重合度匹配
- 再补充地点、船型等特征加权

## 9.3 置信度生成策略

第一版可根据以下因素粗略生成：

- 匹配样本数量
- 关键特征命中程度
- 是否命中高权重特征，例如服务模式、核心项目标题

---

## 10. 处理流程设计

建议流程如下：

```text
1. 检查输入结构完整性
2. 提取检索特征
3. 读取历史样本库
4. 计算每条历史样本的相似度
5. 选取 Top N 匹配结果
6. 生成 matches
7. 聚合生成 reference_summary
8. 计算 confidence
9. 输出结构化结果
```

---

## 11. 示例

## 11.1 示例输入

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

## 11.2 示例输出

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
        "AE-1 crankshaft trueness checks in place",
        "M/B lower bearing remove"
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
      "AE-1 crankshaft trueness checks in place",
      "M/B lower bearing remove"
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

---

## 12. MVP 开发建议

第一版建议先做以下能力：

1. 基于本地 JSON 样本库做规则式历史匹配
2. 输出 Top N `matches`
3. 输出价格区间提示、常见项和 remark 模式摘要
4. 输出保守的 `confidence`

第一版可以暂不做：

- 向量检索
- 语义召回模型
- 高级重排序模型
- 历史成交/未成交经验细分建模

---

## 13. 验收标准

当本 Skill 达到以下效果时，可视为设计目标基本满足：

1. 能稳定消费 `quote_request` 和 `quotable_items`
2. 能输出结构化 `matches`
3. 能输出可供后续定价使用的 `reference_summary`
4. 能输出合理且保守的 `confidence`
5. 不越界生成最终定价结论或报价文档

---

## 14. 后续优化与增强建议

- 用配置化权重替代固定相似度规则
- 引入更丰富的历史样本特征字段
- 增加向量化或语义检索能力
- 区分成交案例与未成交案例的参考价值
- 对 remark 模板做更细粒度归类
