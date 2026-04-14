# `historical_quote_reference_skill` 升级方案

## 1. 目标

本方案用于把当前历史报价参考能力从“可运行的样例检索”升级为“可解释、可扩展、可稳定服务定价”的历史参考模块。

本次升级遵循以下原则：

- 保持现有主链路可运行
- 保持 `historical_reference -> quote_pricing_skill` 的既有消费路径不被打断
- 先做无向量增强版，再预留向量化扩展位
- 优先增强 item 级匹配与 item 级价格参考能力

## 2. 当前问题

当前历史匹配主要依赖以下字段：

- `service_context.service_category`
- `service_context.service_mode`
- `service_context.location_type`
- `header_context.vessel_type`
- `quotable_items[*].title`

存在以下主要问题：

- 过度依赖少量场景字段，信息太薄
- `vessel_type` 采用精确文本匹配，鲁棒性弱
- item 相似度只看标题，不看 `description`、`work_scope`、`pricing_clues`
- 价格参考仍偏 quote 级，不利于后续 item 定价兜底
- 历史质量标记不足，难以向下游表达“命中了，但不够稳”

## 3. 本次落地范围

本次先做 6 项：

1. 增强历史样本结构
2. 引入 item-level 规则匹配
3. 增加 `vessel_type` 归一化
4. 增加 `reference_summary.item_price_hints`
5. 增强 `history_quality_flags`
6. 调整 `quote_pricing_skill` 优先消费 item 级历史价格提示

本次第二阶段落地“规则预筛 + 向量重排”，但在当前仓库依赖约束下，向量层采用零依赖本地 TF-IDF 稀疏向量实现，而不是外部 embedding 模型。

## 4. 历史样本结构升级

历史样本在保留当前字段的同时，新增更细粒度结构：

- `vessel_type_normalized`
- `service_port_region`
- `spare_parts_supply_mode`
- `option_style_tags`
- `charge_item_tags`
- `commercial_terms`
- `item_details`

其中 `item_details` 为核心增强点，建议结构如下：

```json
{
  "item_id": "hist-004-svc-1",
  "item_type": "service",
  "title": "HCU system overhaul",
  "description": "64k running hours overhaul scope",
  "work_scope": [
    "Overhaul ELFI valve and Multiway valve units"
  ],
  "labor_hint": [
    "1 supervisor 8 hours",
    "7 fitters 8 hours"
  ],
  "pricing_clues": [
    "mechanical",
    "dock repair"
  ],
  "amount": 2400.0,
  "currency": "USD",
  "status": "chargeable"
}
```

## 5. 匹配逻辑升级

### 5.1 两层匹配

第一层：场景匹配

- `service_mode`
- `service_category`
- `location_type`
- `vessel_type_normalized`

第二层：item 级匹配

- `item_type`
- `title`
- `description`
- `work_scope`
- `labor_hint`
- `pricing_clues`

### 5.2 item 相似度原则

对每个 `quotable_item`，在历史记录的 `item_details` 中寻找最佳匹配项。匹配分数由以下信号组成：

- `item_type` 一致
- 标题精确或高重合
- 描述与工作范围文本重合
- `pricing_clues` 命中
- `labor_hint` 命中

输出中应保留：

- `matched_item_pairs`
- `matched_signals`
- `match_level`

## 6. vessel_type 归一化

为避免 `Bulk Carrier`、`Kamsarmax Bulk Carrier`、`82,000 mt Kamsarmax Bulk Carrier` 被视为完全不同，增加归一化层。

建议枚举：

- `bulk_carrier`
- `tanker`
- `container`
- `general_cargo`
- `offshore`
- `unknown`

归一化后匹配以标准值为准，原始值仍保留在历史样本中。

## 7. 输出增强

在保持现有输出主体不变的前提下，新增以下结构。

### 7.1 `matches[*]`

新增：

- `match_level`
- `matched_item_pairs`
- `commercial_fit`

### 7.2 `reference_summary`

新增：

- `item_price_hints`

建议结构：

```json
{
  "query_item_id": "svc-1",
  "query_title": "HCU system overhaul",
  "currency": "USD",
  "min": 2400.0,
  "max": 2550.0,
  "median": 2475.0,
  "sample_size": 2,
  "matched_reference_item_ids": [
    "hist-004-svc-1",
    "hist-005-svc-1"
  ],
  "source_quote_ids": [
    "hist-004",
    "hist-005"
  ]
}
```

## 8. 历史质量标记增强

在现有基础上补充：

- `low_sample_size`
- `weak_top_match`
- `weak_item_overlap`
- `context_only_match`
- `commercial_mismatch`
- `low_item_sample_size`
- `broad_item_price_range`

这些标记继续服务 `quote_pricing_skill` 的保守消费策略。

## 9. 对 `quote_pricing_skill` 的影响

`quote_pricing_skill` 继续保留当前对以下字段的消费：

- `price_range_hint`
- `remark_patterns`
- `remark_blocks`
- `charge_item_hints`
- `option_style_hints`
- `history_quality_flags`

同时新增优先级更高的 item 级价格参考：

- 优先读取 `reference_summary.item_price_hints`
- 如果存在当前 item 的价格提示，则优先用 item 级中位价兜底
- 如果不存在，再退回 quote 级 `price_range_hint`

## 10. 规则预筛 + 向量重排

当前已落地的第二阶段实现为：

- 第一层：规则预筛
- 第二层：本地 TF-IDF 稀疏向量余弦重排

这样做的原因是当前 `.opencode/.venv` 中没有 `numpy`、`sklearn`、`sentence_transformers`、`transformers` 等可直接复用的向量依赖，因此先采用零依赖版本落地混合检索流程。

### 10.1 规则预筛

规则预筛主要使用：

- `service_mode`
- `service_category`
- `location_type`
- `vessel_type_normalized`
- `item_type_overlap`
- `title_overlap`

只有通过预筛的历史记录才进入下一阶段重排。

### 10.2 向量重排

当前重排层使用 query text 与 history text 的 TF-IDF 稀疏向量余弦相似度，输出：

- `semantic_score`

该分数与规则分、预筛分一起组成最终 `similarity`。

### 10.3 向量文本拼接

当前用于重排的文本由以下内容拼接而成：

- `item_type`
- `title`
- `description`
- `work_scope`
- `labor_hint`
- `pricing_clues`
- `service_mode`
- `location_type`
- `vessel_type_normalized`
- `remarks`

### 10.4 现阶段限制

当前实现虽然采用“向量重排”这个形态，但严格来说还是本地轻量语义检索，并非外部 embedding 模型。后续如果环境允许，可把这一层替换为真正的 embedding 向量。

## 11. 实施顺序

建议按以下顺序实施：

1. 升级历史样本结构
2. 升级 `historical_quote_reference_skill` 输出 schema
3. 实现 item-level 匹配与 `vessel_type` 归一化
4. 增加 `item_price_hints` 与增强质量标记
5. 升级 `quote_pricing_skill` 消费逻辑
6. 更新 examples 并做 skill / orchestrator 验证
7. 落地 `rule_prefilter+tfidf_rerank` 的混合检索实现

## 12. 验收标准

满足以下条件可视为本次升级完成：

- 历史 skill 样例契约校验通过
- 历史 skill 样例运行通过
- `quote_pricing_skill` 样例契约校验通过
- `quote_pricing_skill` 样例运行通过
- orchestrator 样例运行通过
- 历史输出中可见 `matched_item_pairs`、`item_price_hints`、增强后的 `history_quality_flags`
- pricing 在缺少规则金额时，能够优先使用 item 级历史价格提示兜底
