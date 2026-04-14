# `historical_quote_reference_skill` 详细设计

## 1. 文档目的

本文用于细化第三个 Skill：`historical_quote_reference_skill` 的当前实现设计，作为开发、联调和验收参考。

本设计对齐当前仓库中的可执行实现、样例与 schema，重点说明历史参考如何为后续定价与审核提供结构化辅助信息。

## 2. Skill 定位

`historical_quote_reference_skill` 是智能报价链路中的历史参考检索层。

它接收：

- `quote_request`
- `quotable_items`

并从本地历史样本库中检索相似案例，输出：

- `matches`
- `reference_summary`
- `confidence`

它回答的核心问题是：

1. 当前报价请求和哪些历史案例相似
2. 相似性主要来自上下文还是 item 级工作内容
3. 历史中常见的报价项、remark 模式、附加收费线索、方案风格线索有哪些
4. 当前历史参考是否足够可靠，是否存在明显质量风险
5. 哪些历史 item 可以为当前 item 提供价格区间参考

## 3. 目标与非目标

### 3.1 目标

- 消费 `quote_request` 与 `quotable_items`
- 输出可解释的历史匹配结果 `matches`
- 输出可供下游消费的 `reference_summary`
- 输出保守的 `confidence`
- 提供 item 级历史价格提示 `item_price_hints`

### 3.2 非目标

以下内容不属于本 Skill：

- 不输出可报价判断
- 不直接计算最终金额
- 不生成 `quotation_options`
- 不生成最终 `QuoteDocument`
- 不直接决定最终 remark 写法

本 Skill 的职责是“提供参考”，而不是“替代定价”。

## 4. 上下游关系

### 4.1 上游输入

本 Skill 接收：

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

其中：

- `quote_request` 来自 `quote_request_prepare_skill`
- `quotable_items` 来自 `quote_feasibility_check_skill`

### 4.2 下游输出

本 Skill 直接服务于：

1. `quote_pricing_skill`
2. `quote_review_output_skill`

其中：

- `quote_pricing_skill` 消费价格区间、item 级价格提示、remark 模式、附加费用线索、方案风格线索和质量标记
- `quote_review_output_skill` 可复用历史引用结果和摘要信息生成最终 `trace`

## 5. 设计原则

### 5.1 历史参考是辅助，不是替代

历史样本只能作为参考输入，不能替代当前业务事实与规则计算。

### 5.2 相似性必须可解释

输出不能只有“命中某个 quote_id”，还应说明命中的上下文特征、item 特征和商业特征。

### 5.3 优先 item 级参考

对下游定价最有价值的是 item 级相似性与 item 级价格提示，而不是只返回 quote 级总价区间。

### 5.4 保守表达不确定性

当历史样本不足、item 重叠弱、商业条件不一致时，必须用 `history_quality_flags` 与较保守的 `confidence` 显式表达。

## 6. 输入详细设计

### 6.1 输入对象

```json
{
  "quote_request": {},
  "quotable_items": []
}
```

### 6.2 输入字段要求

#### `quote_request`

当前实现主要使用以下字段：

- `header_context.vessel_type`
- `service_context.service_category`
- `service_context.service_mode`
- `service_context.location_type`
- `spare_parts_context.spare_parts_supply_mode`
- `candidate_items[*]`

其中 `candidate_items[*]` 虽不直接作为主输入列表参与排序，但其字段形状与 `quotable_items` 的 `item_id` 对应关系决定了整条链路中 item 的可解释性与下游复用能力。

#### `quotable_items`

本 Skill 主要围绕 `quotable_items` 做 item-level 匹配。

当前实现至少消费：

- `item_id`
- `item_type`
- `title`

并在 item 级文本匹配中兼容读取：

- `description`
- `work_scope`
- `labor_hint`
- `pricing_clues`

如果 `quotable_items` 为空，本 Skill 仍可运行，但会输出更保守的历史参考结果。

## 7. 历史样本结构

历史样本库位于：

` .opencode/skills/historical_quote_reference_skill/data/historical_quotes.sample.json `

当前实现支持以下历史字段：

- `quote_id`
- `service_category`
- `service_mode`
- `location_type`
- `vessel_type`
- `vessel_type_normalized`
- `service_port_region`
- `spare_parts_supply_mode`
- `currency`
- `total_amount`
- `items`
- `remarks`
- `commercial_terms`
- `option_style_tags`
- `charge_item_tags`
- `item_details`

其中 `item_details` 是 item-level 匹配和 item 级价格提示的核心数据结构。

推荐结构：

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
  "amount": 2550.0,
  "currency": "USD",
  "status": "chargeable"
}
```

## 8. 输出详细设计

### 8.1 输出对象

```json
{
  "matches": [],
  "reference_summary": {},
  "confidence": 0.0
}
```

### 8.2 `matches`

每个历史命中结果包含：

- `quote_id`
- `similarity`
- `reason`
- `matched_features`
- `reference_items`
- `reference_remarks`
- `match_level`
- `matched_item_pairs`
- `commercial_fit`

说明：

- `match_level` 用于表达当前命中更偏上下文还是 item 级重合
- `matched_item_pairs` 用于表达 query item 与 reference item 的具体对应关系
- `commercial_fit` 用于表达商业条件是否接近，例如备件供应责任是否一致

### 8.3 `reference_summary`

当前实现输出以下聚合字段：

- `price_range_hint`
- `common_items`
- `remark_patterns`
- `recommended_reference_ids`
- `item_clusters`
- `remark_blocks`
- `charge_item_hints`
- `option_style_hints`
- `history_quality_flags`
- `item_price_hints`
- `retrieval_strategy`

其中：

- `price_range_hint` 是 quote 级总价区间，仅作兜底参考
- `item_price_hints` 是 item 级价格提示，优先级高于 quote 级区间
- `charge_item_hints` 为附加收费线索，不代表直接金额结论
- `option_style_hints` 为历史方案风格线索，不直接生成报价方案
- `history_quality_flags` 用于表达历史参考的可信度风险

### 8.4 `confidence`

`confidence` 取值范围为 `0.0 - 1.0`，基于：

- Top match 相似度
- 样本数量
- 是否存在 item 级命中
- 是否缺少 `quotable_items`

## 9. 匹配逻辑设计

### 9.1 场景匹配

当前场景级匹配使用以下字段：

1. `service_category`
2. `service_mode`
3. `location_type`
4. `vessel_type_normalized`

其中 `vessel_type` 会先归一化，例如：

- `Kamsarmax Bulk Carrier` -> `bulk_carrier`
- `82,000 mt Kamsarmax Bulk Carrier` -> `bulk_carrier`
- `Oil/Chemical Tanker` -> `tanker`

### 9.2 item-level 匹配

当前 item-level 匹配围绕 `quotable_items` 与历史 `item_details` 进行。

匹配信号包括：

1. `item_type` 是否一致
2. `title` 是否精确命中或高重合
3. `description + work_scope + labor_hint + pricing_clues` 拼接文本的 token overlap
4. `pricing_clues` 是否重合
5. `labor_hint` 是否重合

每个 query item 只保留当前历史记录中的最佳 reference item 匹配对。

### 9.3 商业适配度

当前 `commercial_fit` 主要表达：

1. `spare_parts_supply_mode_match`
2. `option_style_overlap`

该信息主要用于提示“技术上像，但商业边界可能不同”的情况。

### 9.4 规则预筛

当前实现先做规则预筛，预筛分主要来自：

1. `service_mode`
2. `service_category`
3. `location_type`
4. `vessel_type_normalized`
5. `item_type_overlap`
6. `title_overlap`

只有通过预筛的历史记录才进入下一阶段重排。

### 9.5 向量重排

当前实现已进入“规则预筛 + 向量重排”的混合检索阶段。

当前实现优先使用阿里云 `text-embedding-v4` 的 OpenAI 兼容接口做向量重排；如果未配置 `DASHSCOPE_API_KEY` 或调用失败，则自动回退到本地零依赖 TF-IDF 稀疏向量余弦相似度实现。

新增输出字段：

1. `prefilter_score`
2. `semantic_score`
3. `rerank_stage`

其中：

- `prefilter_score` 表示规则预筛得分
- `semantic_score` 表示 query 与历史记录文本的 embedding 或 TF-IDF 语义相似度
- `rerank_stage` 当前固定为 `hybrid`

当前 `reference_summary.retrieval_strategy` 可能取值：

1. `rule_prefilter+aliyun_embedding_rerank`
2. `rule_prefilter+tfidf_fallback`

### 9.6 排序与截断

所有通过预筛的历史记录会结合：

1. 规则分
2. 预筛分
3. `semantic_score`

计算最终 `similarity`，再按 `similarity` 降序排序，最终取 Top 3 作为 `matches`。

## 10. 处理流程设计

当前实现流程如下：

```text
1. 校验输入结构
2. 提取 service_context / header_context / spare_parts_context
3. 归一化 vessel_type
4. 读取历史样本库
5. 对每条历史记录做规则预筛
6. 构造 query text 与 record text
7. 使用 TF-IDF 余弦做语义重排
8. 对每条历史记录做 item-level 匹配
9. 计算商业适配度
10. 聚合为 similarity / matched_features / matched_item_pairs
11. 生成 Top 3 matches
12. 聚合生成 reference_summary
13. 生成 item_price_hints 与 history_quality_flags
14. 写入 retrieval_strategy
15. 计算 confidence
16. 输出结果
```

## 11. 质量标记设计

当前实现支持以下 `history_quality_flags`：

- `low_sample_size`
- `weak_top_match`
- `weak_item_overlap`
- `context_only_match`
- `broad_price_range`
- `low_item_sample_size`
- `broad_item_price_range`
- `commercial_mismatch`
- `semantic_only_match`

这些标记会被下游用于更保守地消费历史参考。

## 12. 对下游的价值

当前历史 Skill 对下游的价值主要体现在：

1. 为 `quote_pricing_skill` 提供 quote 级总价区间兜底
2. 为 `quote_pricing_skill` 提供 item 级价格提示 `item_price_hints`
3. 为 `quote_pricing_skill` 提供 `charge_item_hints`，辅助补充附加费用项
4. 为 `quote_pricing_skill` 提供 `option_style_hints`，辅助多方案建模
5. 为 `quote_pricing_skill` 提供 `remark_patterns` 与 `remark_blocks`
6. 为 `quote_review_output_skill` 提供更可解释的历史 trace 基础

## 13. 示例

### 13.1 示例输入

```json
{
  "quote_request": {
    "header_context": {
      "vessel_type": "Tanker"
    },
    "service_context": {
      "service_category": "service",
      "service_mode": "voyage_repair",
      "location_type": "port"
    },
    "spare_parts_context": {
      "spare_parts_supply_mode": null
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
        "labor_hint": [
          "1 supervisor",
          "2 fitters"
        ],
        "pricing_clues": [
          "mechanical",
          "crankshaft"
        ]
      }
    ]
  },
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
  ]
}
```

### 13.2 示例输出

```json
{
  "matches": [
    {
      "quote_id": "hist-001",
      "similarity": 0.74,
      "reason": "核心项目工作范围、文本语义与服务场景相似。",
      "matched_features": [
        "service_category: service",
        "service_mode: voyage_repair",
        "location_type: port",
        "vessel_type_normalized: tanker",
        "item_type: service",
        "item_type_match: service",
        "item_title: AE-1 crankshaft trueness checks in place",
        "work_scope_match: AE-1 crankshaft trueness checks in place",
        "pricing_clue_match: AE-1 crankshaft trueness checks in place",
        "labor_hint_match: AE-1 crankshaft trueness checks in place"
      ],
      "reference_items": [
        "AE-1 crankshaft trueness checks in place"
      ],
      "reference_remarks": [
        "Other repair if needed to be charged extra"
      ],
      "match_level": "strong_item_match",
      "matched_item_pairs": [
        {
          "query_item_id": "svc-1",
          "query_title": "AE-1 crankshaft trueness checks in place",
          "reference_item_id": "hist-001-svc-1",
          "reference_title": "AE-1 crankshaft trueness checks in place",
          "similarity": 0.65,
          "matched_signals": [
            "item_type_match: service",
            "item_title: AE-1 crankshaft trueness checks in place",
            "work_scope_match: AE-1 crankshaft trueness checks in place",
            "pricing_clue_match: AE-1 crankshaft trueness checks in place",
            "labor_hint_match: AE-1 crankshaft trueness checks in place"
          ]
        }
      ],
      "commercial_fit": {
        "spare_parts_supply_mode_match": false,
        "option_style_overlap": [
          "standard_vs_discount"
        ]
      },
      "prefilter_score": 0.85,
      "semantic_score": 0.89,
      "rerank_stage": "hybrid"
    }
  ],
  "reference_summary": {
    "price_range_hint": {
      "currency": "USD",
      "min": 3200.0,
      "max": 9800.0,
      "sample_size": 3
    },
    "common_items": [
      "AE-1 crankshaft trueness checks in place"
    ],
    "remark_patterns": [
      "Other repair if needed to be charged extra"
    ],
    "recommended_reference_ids": [
      "hist-001"
    ],
    "item_clusters": [],
    "remark_blocks": [],
    "charge_item_hints": [],
    "option_style_hints": [],
    "history_quality_flags": [
      "broad_price_range",
      "broad_item_price_range",
      "commercial_mismatch"
    ],
    "item_price_hints": [
      {
        "query_item_id": "svc-1",
        "query_title": "AE-1 crankshaft trueness checks in place",
        "currency": "USD",
        "min": 3200.0,
        "max": 9800.0,
        "median": 3500.0,
        "sample_size": 3,
        "matched_reference_item_ids": [
          "hist-001-svc-1",
          "hist-002-svc-1",
          "hist-003-svc-1"
        ],
        "source_quote_ids": [
          "hist-001",
          "hist-002",
          "hist-003"
        ]
      }
    ],
    "retrieval_strategy": "rule_prefilter+tfidf_rerank"
  },
  "confidence": 1.0
}
```

## 14. MVP 与当前实现边界

当前版本已经不再是最初的“仅标题规则匹配”，而是一个“规则预筛 + 阿里云 embedding 重排，失败时回退 TF-IDF”的混合检索实现。

当前仍然没有做：

- 学习排序模型
- 成交/未成交历史价值区分

## 15. 后续优化方向

建议下一阶段按以下顺序优化：

1. 增加更稳定的 `service_port_region` 归一化与消费
2. 把 `matched_item_pairs` 更深度接入定价逻辑
3. 如果需要更高检索精度，可从 OpenAI 兼容接口切换到 DashScope 原生接口，以支持 `text_type`、`instruct`、`dense&sparse`
4. 区分成交案例、失败案例和仅参考案例
5. 提升商业条件建模，例如备件归属、付款方式、报价方案类型

## 16. 验收标准

当本 Skill 满足以下条件时，可视为与当前设计一致：

1. 能稳定消费 `quote_request` 和 `quotable_items`
2. 能输出包含 `match_level`、`matched_item_pairs`、`commercial_fit` 的 `matches`
3. 能输出包含 `item_price_hints` 的 `reference_summary`
4. 能输出可解释且保守的 `history_quality_flags`
5. 能输出保守合理的 `confidence`
6. 不越界输出最终定价结论或报价文档
