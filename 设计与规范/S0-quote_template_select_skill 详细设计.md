# `quote_template_select_skill` 详细设计

## 1. 定位

`quote_template_select_skill` 是智能报价链路的第零步（S0）。

它的职责是在后续报价结构化、可报价判断、历史检索、定价和 PDF 渲染之前，先根据智能评估单识别本次报价应采用的模板类型。

当前模板类型固定为 7 类：

1. `engineering-service`
2. `digital-product`
3. `laboratory`
4. `man-hour`
5. `product`
6. `supercharger`
7. `valva`

当前默认兜底模板为：`engineering-service`

---

## 2. 目标

本 Skill 负责输出：

- `template_type`
- `confidence`
- `candidate_templates`
- `rule_scores`
- `reasons`
- `matched_signals`
- `needs_manual_confirmation`
- `template_data_hints`

本 Skill 不负责：

- 生成 `quote_request`
- 生成报价金额
- 组装 `QuoteDocument`
- 补齐模板额外字段值
- 渲染 HTML/PDF

---

## 3. 输入与输出

## 3.1 输入

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {
    "force_template_type": null
  }
}
```

说明：

- `assessment_report` 是主输入
- `force_template_type` 可用于后续人工强制指定模板
- 若存在有效 `force_template_type`，可跳过自动判断并直接返回高置信度结果

## 3.2 输出

```json
{
  "template_selection_result": {
    "template_type": "engineering-service",
    "confidence": 0.88,
    "candidate_templates": [
      "engineering-service",
      "man-hour"
    ],
    "rule_scores": {
      "engineering-service": 8,
      "digital-product": 0,
      "laboratory": 0,
      "man-hour": 6,
      "product": 1,
      "supercharger": 0,
      "valva": 0
    },
    "reasons": [
      "评估单显示当前需求以工程服务为主"
    ],
    "matched_signals": [],
    "needs_manual_confirmation": false,
    "questions_for_user": [],
    "review_flags": [],
    "template_data_hints": {
      "needs_extra_fields": [],
      "likely_history_sources": []
    }
  }
}
```

---

## 4. 分类原则

## 4.1 先规则，后 LLM

建议采用两阶段分类：

1. 规则预打分
2. LLM 结构化裁决

规则用于：

- 降低自由判断漂移
- 增强可解释性
- 提供冲突候选模板

LLM 用于：

- 综合多条评估事实
- 区分近似模板
- 输出结构化理由与置信度

## 4.2 模板选择只能从固定枚举中选

不允许在运行时生成新的模板类型名称。

## 4.3 低置信度允许回退

若信息不足或候选模板冲突明显，则：

- `needs_manual_confirmation = true`
- `template_type` 回退为 `engineering-service`

---

## 5. 规则特征设计

## 5.1 `laboratory`

优先命中：

- 检测 / 化验 / 分析 / sample / testing
- intake water / discharge water
- system info / maker model / class / flag

## 5.2 `supercharger`

优先命中：

- turbocharger / supercharger / 增压器
- running hours
- turbocharger type
- 专项增压器大修、检查、routine overhaul

## 5.3 `valva`

优先命中：

- valve / 阀 / repair kit / complete valve
- position no / valve list
- engine maker/type / built year / built yard

## 5.4 `digital-product`

优先命中：

- digital / software / platform / license / subscription
- 数字产品 / 系统授权 / 软件服务

## 5.5 `product`

优先命中：

- 纯商品 / 纯备件 / spare parts / part no / specification
- 服务弱、货物强

## 5.6 `man-hour`

优先命中：

- man-hour / 工时 / engineer / fitter / technician / attendance
- 人数、天数、工时信息强于设备专项结构

## 5.7 `engineering-service`

作为默认工程服务模板，适用于：

- 现场工程服务
- 大修 / 校验 / 调试 / 检修 / 故障排查
- 不明显属于其他 6 类模板的服务型需求

---

## 6. 与现有链路的集成

推荐链路：

1. `S0 quote_template_select_skill`
2. `S1 quote_request_prepare_skill`
3. `S2 quote_feasibility_check_skill`
4. `S3 historical_quote_reference_skill`
5. `S4 quote_pricing_skill`
6. `S5 quote_review_output_skill`
7. `S6 quote_pdf_render_skill`

## 6.1 orchestrator 接入建议

在 `.opencode/quote_orchestrator/run.py` 中：

1. 最先加载 `quote_template_select_skill`
2. 运行后得到 `template_selection_result`
3. 将结果写入：
   - orchestrator 最终结果顶层
   - `business_context.template_type`
   - 后续各 Skill 输入上下文
4. `quote_pdf_render_skill` 直接消费 `template_type`

## 6.2 推荐字段传递方式

建议后续统一传递：

```json
"business_context": {
  "template_type": "engineering-service"
}
```

并在最终 `trace` 中保留：

- `selected_template_type`
- `template_selection_confidence`

---

## 7. 模板额外字段边界

本 Skill 只负责识别模板类型，不负责补字段值。

由于各模板可能需要历史报价中的额外字段，而历史库字段名未必与模板字段名一致，因此建议在后续渲染层单独维护：

- `历史字段 -> 标准模板字段` 的映射表
- 每种模板的额外字段清单

本 Skill 只通过 `template_data_hints` 输出提示。

---

## 8. 当前实施建议

第一阶段：

- 先实现 S0 契约与 orchestrator 接入
- 先让 `quote_pdf_render_skill` 消费 `template_type`
- 当前未命中时默认回退到 `engineering-service`

第二阶段：

- 让历史检索和定价也感知 `template_type`
- 逐步完善 `template_data_hints` 与历史字段映射体系
