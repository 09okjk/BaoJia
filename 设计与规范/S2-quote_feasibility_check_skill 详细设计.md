# `quote_feasibility_check_skill` 详细设计

## 1. 文档目的

本文用于细化第二个 Skill：`quote_feasibility_check_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》中的以下约束：

- 第二个 Skill 的目标是“判断哪些内容可以报价，哪些必须待确认”
- 各 Skill 之间统一使用 JSON 作为输入输出协议
- 系统不得在信息不完整时默认补全业务事实
- 本 Skill 负责形成审核提示，但不负责金额计算与最终报价文档输出

---

## 2. Skill 定位

`quote_feasibility_check_skill` 是智能报价链路中的可报价判断层。

它接收第一个 Skill 输出的标准 `quote_request`，对输入事实进行可报价性分析，回答以下核心问题：

1. 当前是否可以进入正式报价
2. 可以全量报价，还是只能部分报价
3. 哪些项可报价，哪些项必须待确认
4. 哪些项当前应排除在报价范围之外
5. 哪些问题需要后续补问用户或补充内部确认

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `quote_request`
- 判断当前是否具备报价条件
- 输出 `can_quote`
- 输出 `quote_scope`
- 输出 `quotable_items`
- 输出 `tbc_items`
- 输出 `exclusions`
- 输出 `missing_fields`
- 输出 `questions_for_user`
- 输出 `review_flags`

## 3.2 非目标

以下内容不属于本 Skill：

- 不生成历史报价参考
- 不计算金额、折扣、汇总
- 不生成 `quotation_options`
- 不生成 `footer`、`remark`、`service_payment_terms`
- 不生成最终 `QuoteDocument`
- 不把待确认项直接伪装成可收费项

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 接收：

```json
{
  "quote_request": {}
}
```

其中 `quote_request` 由 `quote_request_prepare_skill` 输出。

## 4.2 下游输出

本 Skill 直接服务于：

1. `historical_quote_reference_skill`
2. `quote_pricing_skill`
3. `quote_review_output_skill`

其中：

- `historical_quote_reference_skill` 依赖 `quotable_items` 缩小历史检索范围
- `quote_pricing_skill` 依赖 `quotable_items`、`tbc_items`、`exclusions` 组织报价正文
- `quote_review_output_skill` 可复用 `review_flags`

---

## 5. 设计原则

## 5.1 判断范围优先，避免过早定价

本 Skill 的核心是“能不能报、报哪些”，而不是“报多少钱”。

## 5.2 待确认与排除必须区分

待确认项不等于排除项。

- `tbc_items`：当前信息不足，但后续补充后可能纳入报价
- `exclusions`：当前明确不纳入本次报价范围，或应由其他责任方处理

## 5.3 不确定性必须显式输出

不能因为想让结果“看起来完整”，就把待确认项归入可报价项。

## 5.4 输出要直接服务后续 Skill

输出必须让下游能够直接消费，而不是要求下游重新解释判断结果。

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "quote_request": {}
}
```

## 6.2 输入字段要求

`quote_request` 至少应具备以下信息中的一部分：

- `header_context`
- `service_context`
- `candidate_items`
- `spare_parts_context`
- `risk_context`
- `commercial_context`

如果 `quote_request` 缺少核心结构，本 Skill 不负责重新抽取原始评估单，而应输出保守判断结果与缺失提示。

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "can_quote": true,
  "quote_scope": "full | partial | not_ready",
  "quotable_items": [],
  "tbc_items": [],
  "exclusions": [],
  "missing_fields": [],
  "questions_for_user": [],
  "review_flags": []
}
```

## 7.2 字段定义

### `can_quote`

布尔值。

- `true`：当前至少存在可以进入报价的范围
- `false`：当前不具备稳定报价条件

### `quote_scope`

枚举值：

- `full`：全部候选项都可以进入报价
- `partial`：只有部分候选项可以进入报价
- `not_ready`：当前不建议进入正式报价

### `quotable_items`

当前可进入报价范围的项目列表。

### `tbc_items`

待确认后才能决定是否报价的项目列表。

### `exclusions`

当前明确不纳入本次报价范围的项目列表。

### `missing_fields`

延续第一个 Skill 的思路，显式标出影响判断的缺失信息。

### `questions_for_user`

建议后续向用户或内部确认人发起的问题。

### `review_flags`

对审核方有价值的提醒，例如：

- 报价范围不完整
- 关键场景未确认
- 费用责任边界不清晰

---

## 8. 推荐数据结构

## 8.1 `quotable_items` / `tbc_items` / `exclusions`

建议三类列表采用统一结构，便于后续处理。

```json
{
  "item_id": "",
  "item_type": "service | spare_parts | other",
  "title": "",
  "decision": "quotable | tbc | excluded",
  "reason": "",
  "blocking_fields": [],
  "suggested_status": "chargeable | pending | by_owner | excluded | if_needed",
  "source": "quote_request.candidate_items"
}
```

说明：

- `decision` 用于表达本 Skill 的判断结论
- `blocking_fields` 用于列出导致待确认或排除的关键字段
- `suggested_status` 仅是对后续 Skill 的建议，不是最终 line.status

## 8.2 `questions_for_user`

推荐结构：

```json
{
  "question_id": "",
  "target": "customer | internal",
  "topic": "",
  "question": "",
  "related_item_ids": []
}
```

## 8.3 `review_flags`

推荐结构：

```json
{
  "flag_code": "",
  "severity": "high | medium | low",
  "message": "",
  "related_item_ids": []
}
```

---

## 9. 判断规则设计

## 9.1 判断维度

本 Skill 至少从以下维度判断可报价性：

1. 候选项是否存在
2. 工作范围是否足够明确
3. 服务场景是否足够明确
4. 是否存在关键待确认项
5. 是否存在责任边界明确应排除的内容

## 9.2 全局判断规则

### 可判定 `not_ready` 的典型情况

- `candidate_items` 为空
- 服务模式、服务地点等关键上下文严重缺失
- 绝大部分项目都依赖关键待确认项

### 可判定 `partial` 的典型情况

- 至少一部分项目工作范围明确，可直接报价
- 同时存在部分项目因关键事实缺失只能待确认

### 可判定 `full` 的典型情况

- 候选项完整
- 服务场景足够清晰
- 没有关键阻断项

## 9.3 单项判断规则

### 可报价项

通常满足：

- 标题明确
- 工作范围基本明确
- 没有关键阻断字段
- 不属于明确排除责任

### 待确认项

通常满足：

- 项目本身存在
- 但关键事实不完整，例如数量、责任归属、备件供货方式、实际范围未确认

### 排除项

通常满足：

- 当前责任边界明确不属于本次报价
- 客户侧提供、代理安排或其他第三方负责
- 当前输入已明确写出不纳入本次报价

---

## 10. 缺失信息与问题生成策略

## 10.1 `missing_fields`

本 Skill 应继续补充与“可报价判断”直接相关的缺失项，例如：

- `service_context.service_mode`
- `header_context.service_port`
- `spare_parts_context.spare_parts_supply_mode`
- 某个候选项缺少关键数量或范围线索

## 10.2 `questions_for_user`

只有当缺失项可以转化为明确可提问问题时，才输出到 `questions_for_user`。

例如：

- 备件由船东提供还是我司提供？
- 本次报价范围是否包含额外拆装工作？
- 是否需要提供多方案报价？

## 10.3 `review_flags`

以下场景应生成审核提示：

- 当前只能部分报价
- 关键工作范围尚未确认
- 存在较多待确认项
- 服务责任边界不清晰

---

## 11. 处理流程设计

建议流程如下：

```text
1. 检查 quote_request 结构完整性
2. 读取全局上下文和候选项
3. 判断全局阻断条件
4. 对每个 candidate_item 做可报价分类
5. 汇总 quotable_items / tbc_items / exclusions
6. 生成 missing_fields
7. 生成 questions_for_user
8. 生成 review_flags
9. 输出 can_quote 与 quote_scope
```

---

## 12. 示例

## 12.1 示例输入

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

## 12.2 示例输出

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

---

## 13. MVP 开发建议

第一版建议先做以下能力：

1. 基于 `quote_request` 做全局可报价判断
2. 基于 `candidate_items` 做三分类：可报价 / 待确认 / 排除
3. 输出结构化 `missing_fields`
4. 输出结构化 `questions_for_user`
5. 输出结构化 `review_flags`

第一版可以暂不做：

- 复杂业务规则引擎
- 细粒度责任边界推理
- 多轮问题合并与优先级排序
- 高级置信度评分

---

## 14. 验收标准

当本 Skill 达到以下效果时，可视为设计目标基本满足：

1. 能稳定消费 `quote_request`
2. 能输出明确的 `can_quote` 和 `quote_scope`
3. 能清晰区分 `quotable_items`、`tbc_items`、`exclusions`
4. 能显式输出影响判断的缺失信息
5. 能生成后续可操作的问题与审核提示
6. 不越界做金额计算或最终报价组装

---

## 15. 后续优化与增强建议

- 引入更细粒度的可报价规则配置，而不是全部硬编码在代码中
- 为待确认项增加问题优先级与问题归并能力
- 增加不同服务类别的专项判断规则，例如轮机、电气、第三方服务
- 增加更稳定的责任边界识别，例如 `by_owner`、`arranged_by_agent`、`excluded`
- 为审核提示增加更明确的严重度和升级路径
