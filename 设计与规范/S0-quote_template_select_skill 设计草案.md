# `quote_template_select_skill` 设计草案

## 1. 定位

`quote_template_select_skill` 作为智能报价链路的 `S0`，位于所有报价 skill 之前。

它的职责是：

- 基于评估单判断报价类型
- 输出统一 `template_type`
- 为后续 skill 提供模板分类结果
- 在低置信度时输出候选模板和人工确认提示

当前默认兜底模板：`engineering-service`

---

## 2. 在链路中的位置

建议链路调整为：

1. `quote_template_select_skill`
2. `quote_request_prepare_skill`
3. `quote_feasibility_check_skill`
4. `historical_quote_reference_skill`
5. `quote_pricing_skill`
6. `quote_review_output_skill`
7. `quote_pdf_render_skill`

---

## 3. 输出给后续链路的关键信息

`template_selection_result` 至少应向后传递：

- `template_type`
- `confidence`
- `candidate_templates`
- `needs_manual_confirmation`

建议在 orchestrator 中：

- 将完整 `template_selection_result` 挂到最终结果顶层
- 将 `template_type` 注入 `business_context`
- 将 `template_type` 进一步传给 `quote_review_output_skill` 和 `quote_pdf_render_skill`

---

## 4. 模板类型枚举

- `engineering-service`
- `digital-product`
- `laboratory`
- `man-hour`
- `product`
- `supercharger`
- `valva`

---

## 5. 推荐判断机制

### 5.1 第一层：规则预判

从评估单中提取显式信号，按模板打分。

高优先级专项模板：

- `laboratory`：检测、化验、sample、intake water、discharge water、实验室
- `supercharger`：turbocharger、supercharger、增压器、running hours、VTR/TCA/MET
- `valva`：valve、阀、repair kit、complete valve、position no、valve list

中优先级模板：

- `digital-product`：software、license、subscription、platform、数字产品、系统授权
- `product`：商品、备件、规格、型号、数量为主，缺少施工任务
- `man-hour`：工时、人工、engineer、fitter、attendance、days、hours 为主

兜底模板：

- `engineering-service`

### 5.2 第二层：LLM 结构化判断

将评估单摘要、规则命中结果、模板定义一起输入模型，要求模型：

- 只能从固定枚举中选择
- 必须给出理由
- 必须说明为什么不是相近模板
- 低置信度时给出候选模板，不允许伪高置信度

### 5.3 第三层：程序约束

- `template_type` 必须属于固定枚举
- `confidence < 0.65` 时，建议标记 `needs_manual_confirmation = true`
- 模板冲突时优先保留候选列表
- 无法明确判断时使用 `engineering-service` 兜底

---

## 6. 与 orchestrator 的接入建议

当前 `quote_orchestrator/run.py` 需要增加：

1. 加载 `quote_template_select_skill`
2. 在 `prepare_result` 之前调用 S0
3. 将 `template_selection_result` 挂到最终结果顶层
4. 将 `template_type` 合并进后续 skill 输入上下文

建议伪代码：

```python
template_module = _load_skill_module("quote_template_select_skill")
template_selection_result = template_module.select_quote_template(payload)

payload_for_prepare = {
    **payload,
    "business_context": {
        **payload.get("business_context", {}),
        "template_type": template_selection_result["template_selection_result"]["template_type"],
    },
}
```

最终结果建议增加：

```json
{
  "template_selection_result": {},
  "prepare_result": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {},
  "quote_document": {},
  "render_result": {}
}
```

---

## 7. 当前阶段建议

第一阶段只做：

- S0 识别模板类型
- orchestrator 传递 `template_type`
- `quote_pdf_render_skill` 消费 `template_type`

后续再逐步让：

- 历史检索按模板优先过滤
- 定价逻辑按模板区分
- QuoteDocument 输出 trace 中记录模板类型
