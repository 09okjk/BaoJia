# `quote_orchestration_skill` 设计说明

## 1. 文档目的

本文用于定义顶层工作流 Skill：`quote_orchestration_skill` 的设计，作为后续 Agent 接入、仓库维护、能力边界说明与联调参考。

本设计严格对齐以下文档与原则：

- 《智能报价 Agent Skill 设计说明书（V2.2）》
- `设计与规范/Hybrid 智能编排方案设计.md`
- `设计与规范/当前智能报价流程评审结论.md`
- `设计与规范/Hybrid 智能编排方案与当前实现对照表.md`

本 Skill 的核心目标不是替代底层 Skill，也不是重写 orchestrator，而是：

- 为 Agent 提供单一、明确、可发现的整单报价入口
- 在不破坏现有稳定编排链路的前提下，对外暴露完整工作流能力

---

## 2. Skill 定位

`quote_orchestration_skill` 是智能报价系统中的唯一对外工作流 Skill。

它接收评估单与补充上下文，内部调用 `quote_orchestration_skill/workflow/` 下的实现，输出完整智能报价结果。

它回答的核心问题是：

1. Agent 在需要“整单报价”时，应该调用哪个统一入口
2. 如何在不让 Agent 自己拼接底层 Skill 顺序的前提下，完成完整报价流程
3. 如何把 `pause / resume`、可选节点跳过、结构化 trace 一并暴露给 Agent

简化理解：

- 底层 Skill 负责原子能力
- `workflow/` 负责内部实现与编排
- `quote_orchestration_skill` 负责作为唯一对外入口暴露整条 workflow 能力

---

## 3. 设计目标与非目标

## 3.1 目标

- 为 Agent 提供统一的整单智能报价入口
- 内部复用 `quote_orchestration_skill/workflow/` 下的 workflow 实现
- 支持完整执行、可选节点判断、暂停与恢复
- 输出最终 `QuoteDocument` 与完整中间结果
- 输出 `feedback_reference` 等新增中间结果
- 输出 `execution_trace`、`planner_trace`、`skipped_skills`、`applied_planner_strategies`
- 保持与当前 orchestrator 输入输出契约一致

## 3.2 非目标

以下内容不属于本 Skill：

- 不替代底层 `quote_request_prepare_skill`、`quote_pricing_skill` 等原子 Skill
- 不重新实现 planner、policy 或底层业务规则
- 不改变现有 orchestrator 的职责边界
- 不把报价流程改造成“由 Agent 自己自由决定每个 Skill 顺序”的无约束模式

本 Skill 的职责是“统一封装与暴露 workflow”，不是“重新定义 workflow”。

---

## 4. 设计背景

当前仓库已经有底层 Skill 与 workflow 内部实现，但对 Agent 来说仍需要一个唯一明确的 workflow 入口。

问题在于：

- 对 Agent 来说，底层 Skill 太细，容易误选顺序
- 对 OpenClaw 风格调用来说，直接暴露内部实现文件不够自然
- 对渐进式披露来说，整单 workflow 需要一个明确的顶层使用入口

因此，需要由 `quote_orchestration_skill` 作为唯一对外入口，把 `workflow/` 封装为内部实现。

---

## 5. 上下游关系

## 5.1 上游输入

本 Skill 接收与内部 workflow 相同的输入对象：

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {},
  "user_decision": "accept | revise",
  "render_options": {},
  "resume_payload": {}
}
```

说明：

- `assessment_report` 是主输入
- `customer_context`、`business_context` 用于补充上下文与策略控制
- `business_context` 当前还可承载如 `sales_owner` 等 feedback reference 相关上下文
- `user_decision` 用于在对话式纠错阶段明确表达用户选择继续修改还是确认当前版本
- `render_options` 用于可选渲染
- `resume_payload` 用于从暂停状态继续

## 5.2 下游调用

本 Skill 内部调用：

- `.opencode/skills/quote_orchestration_skill/workflow/run.py`
- 其中的核心入口函数：`orchestrate_quote(payload)`

本 Skill 不直接逐个编排底层 Skill，而是统一把 payload 交给内部 workflow。

## 5.3 下游输出

本 Skill 输出与内部 workflow 一致的完整结果对象，例如：

```json
{
  "template_selection_result": {},
  "prepare_result": {},
  "feedback_reference": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {},
  "quote_document": {},
  "orchestration_status": "completed",
  "draft_status": "awaiting_user_decision",
  "user_decision": null,
  "execution_trace": [],
  "planner_trace": [],
  "skipped_skills": [],
  "applied_planner_strategies": []
}
```

若触发暂停，还可能包含：

- `pause_reason`
- `questions_for_user`
- `review_flags`
- `clarification_context`

若启用渲染，还可能包含：

- `render_result`

---

## 6. 设计原则

## 6.1 唯一对外入口，底层职责不混淆

Agent 做整单报价时，应直接调用 `quote_orchestration_skill`。

底层 Skill 仍保留独立职责，用于：

- 单点能力调用
- 定向调试
- 局部验证
- 后续更细粒度扩展

## 6.2 封装 workflow，而不是复制 workflow

本 Skill 不是重新实现第二套 workflow，而是直接封装本 Skill 内部已有的 workflow 实现。

这样可以保证：

- 生产链路稳定性不下降
- 不引入第二套工作流逻辑
- 对外入口与内部 workflow 契约保持一致

## 6.3 结构化输出优先

本 Skill 输出必须保持 JSON 结构化，不得退化为自由文本。

输出必须保留：

- 中间结果
- 最终结果
- trace
- 可选 skill 决策信息
- 暂停与恢复上下文

## 6.4 渐进式披露优先

本 Skill 的 `SKILL.md` 需要对 Agent 和人类维护者同时友好：

- 顶层先说明“何时用这个 Skill”
- 中层说明“它做什么、不做什么”
- 深层才展开 schema、样例和详细设计

这样可以避免 Agent 错把底层 Skill 当成顶层 workflow 入口。

---

## 7. 输入详细设计

## 7.1 输入契约来源

本 Skill 不单独发明一套新的 workflow 输入契约，而是直接复用：

- `.opencode/skills/quote_orchestration_skill/workflow/schemas/input.schema.json`

并通过 Skill 自己的 schema 文件做转引：

- `.opencode/skills/quote_orchestration_skill/references/quote-orchestration-input.schema.json`

这样做的原因是：

1. 避免顶层 Skill 与内部 workflow 出现双份输入定义
2. 保持 Agent 入口与系统入口一致
3. 减少后续契约维护成本

## 7.2 输入字段说明

### `assessment_report`

必需。整条报价链路的主输入。

### `customer_context`

可选。用于提供币种、客户补充信息、恢复时的 `confirmed_answers` 等。

### `business_context`

可选。用于提供：

- `interactive_mode`
- `resume_from`
- `skip_historical_reference`
- `prefer_fast_quote`
- `force_multi_option`
- `option_hints`

### `render_options`

可选。用于控制是否执行渲染，以及渲染语言和输出目录。

### `resume_payload`

可选。用于在 workflow 已暂停后继续执行。

---

## 8. 输出详细设计

## 8.1 输出契约来源

本 Skill 直接复用：

- `.opencode/skills/quote_orchestration_skill/workflow/schemas/output.schema.json`

并通过：

- `.opencode/skills/quote_orchestration_skill/references/quote-orchestration-output.schema.json`

做对外暴露。

## 8.2 输出层次

输出可分为四层：

1. 中间结果层
   - `template_selection_result`
   - `prepare_result`
   - `feedback_reference`
   - `feasibility_result`
   - `historical_reference`
   - `pricing_result`
2. 最终结果层
   - `quote_document`
   - `render_result`
3. 编排状态层
   - `orchestration_status`
   - `draft_status`
   - `user_decision`
   - `user_decision_prompt`
   - `pause_reason`
   - `clarification_context`
4. 解释与追踪层
   - `execution_trace`
   - `planner_trace`
   - `skipped_skills`
   - `applied_planner_strategies`

## 8.3 暂停与恢复约束

当输出为 `paused` 时：

- 不应伪造完整完成状态
- 应显式返回待确认问题
- 应保留恢复所需中间结果

补充说明：`paused` 主要用于“事实待确认后再继续”的业务暂停，不等于“用户对草案不满意”。

对于草案纠错闭环，建议调用方在前端额外维护显式用户决策状态：

1. `继续修改`
2. `确认当前版本`

其中只有用户明确选择 `确认当前版本`，才应视为本轮草案纠错结束。

当前实现中，这一机制已经通过对话式输入落地：

1. 首次生成草案后，workflow 输出：
   - `draft_status: "awaiting_user_decision"`
   - `user_decision_prompt`
2. 下一轮对话时，调用方可直接传入：
   - `user_decision: "accept"`
   - `user_decision: "revise"`
3. 系统会分别进入：
   - `accepted`
   - `revising`

恢复时：

- 调用方应把已有结果作为 `resume_payload` 传回
- 可通过 `confirmed_answers` 补充人工确认事实

---

## 9. 内部实现设计

## 9.1 目录结构

```text
.opencode/skills/quote_orchestration_skill/
├── SKILL.md
├── _meta.json
├── README.md
├── .gitignore
├── skill.py
├── run.py
├── validate_samples.py
├── scripts/
│   └── main.py
├── workflow/
│   ├── __init__.py
│   ├── run.py
│   ├── state.py
│   ├── planner.py
│   ├── policy.py
│   ├── skill_registry.py
│   └── schemas/
│       ├── input.schema.json
│       └── output.schema.json
├── references/
│   ├── WORKFLOW_CONTRACT.md
│   ├── quote-orchestration-input.schema.json
│   └── quote-orchestration-output.schema.json
└── samples/
    ├── sample-input.json
    └── sample-output.json
```

## 9.2 关键实现点

### `skill.py`

负责：

- 统一暴露 `run_quote_workflow(payload)`
- 内部导入 `workflow.run` 的 `orchestrate_quote(payload)`
- 作为 Agent 和 CLI 共享的主逻辑入口

### `run.py`

负责：

- 处理 CLI 参数
- 加载输入 JSON
- 校验输入输出 schema
- 调用 `run_quote_workflow(payload)`
- 输出 JSON 文件或标准输出

### `scripts/main.py`

负责：

- 作为 OpenClaw 风格的发布态脚本入口
- 转发到 `run.py`

## 9.3 与 orchestrator 的关系

该关系必须长期保持清晰：

- `quote_orchestration_skill` 是唯一对外入口层
- `workflow/` 是内部编排实现层
- 底层 Skill 是原子能力层

补充说明：

- 旧 `.opencode/quote_orchestrator/` 路径当前仅保留兼容壳用途
- 新增能力应优先落在 `quote_orchestration_skill/workflow/` 下

三者不是替代关系，而是分层关系。

---

## 10. 与其他 Skill 的关系

本 Skill 与下列 Skill 配合，但不取代其职责：

- `quote_template_select_skill`
- `quote_request_prepare_skill`
- `quote_feedback_reference_skill`
- `quote_feasibility_check_skill`
- `historical_quote_reference_skill`
- `quote_pricing_skill`
- `quote_review_output_skill`
- `quote_pdf_render_skill`

调用原则如下：

1. 做整单报价时，调用 `quote_orchestration_skill`
2. 做单阶段调试或研究时，按需调用底层 Skill
3. 不应让 Agent 在整单场景下自己决定底层 Skill 的顺序

补充说明：当前 workflow 已在 `prepare` 与 `feasibility` 之间接入 `quote_feedback_reference_skill`，用于把 memory 检索结果注入后续 pricing / review。

补充说明：当前 workflow 自身负责“生成草案”和“待确认后恢复”，而“是否接受当前草案”建议由上层产品交互通过显式按钮决定，不建议让 workflow 自行猜测用户满意度。

---

## 11. 渐进式披露设计说明

本 Skill 是最适合体现渐进式披露思想的入口层 Skill。

原因是：

1. Agent 首先需要知道“整单报价唯一应该调用哪个 Skill”
2. Agent 不应在最开始就暴露到底层所有细节
3. 人类维护者在深入排障时，才需要查看 schema、samples 与详细设计

因此其 `SKILL.md` 分层含义如下：

### 第一层：入口判断

- `When to Use`
- `When NOT to Use`

回答的是“该不该用这个 Skill”。

### 第二层：行为理解

- `Quick Start`
- `Core Behavior`
- `Core Rules`

回答的是“这个 Skill 做什么、不做什么、输出什么”。

### 第三层：深入维护

- `Deep Dive`
- `references/*.schema.json`
- `samples/`
- 本详细设计文档

回答的是“如果要维护或扩展，应去哪里看细节”。

---

## 12. Agent 使用建议

对于 Agent，建议把本 Skill 视为以下语义入口：

- “整单智能报价”
- “完整报价流程执行”
- “从评估单生成最终报价”
- “恢复一个已暂停的报价流程”

不建议把本 Skill 描述成：

- 一个新的底层定价 Skill
- 一个替代所有现有 Skill 的万能 Skill
- 一个自由决定业务流程的无边界 Agent

其最佳定位是：

- 顶层 workflow skill

---

## 13. 风险与边界

## 13.1 风险

- 若后续顶层 Skill 和 `workflow/` 契约不同步，会形成双份入口定义
- 若 Agent 绕过该 Skill 自行串联底层 Skill，会削弱编排一致性
- 若在顶层 Skill 里加入过多业务规则，会造成 orchestrator 与 Skill 重复

## 13.2 边界

- 本 Skill 不负责定义新的报价规则
- 本 Skill 不负责替换 orchestrator
- 本 Skill 不负责削弱底层 Skill 的独立复用性

---

## 14. 成功标准

若以下条件成立，则认为本 Skill 设计达成目标：

1. Agent 做整单报价时能够明确选择本 Skill 作为唯一入口
2. 本 Skill 能稳定调用内部 workflow 实现
3. 输出能完整保留当前 workflow 的中间结果和最终结果
4. `pause / resume` 能通过本 Skill 正常暴露
5. OpenClaw 风格目录、文档和样例完整
6. 顶层 Skill 的引入不破坏现有生产链路

---

## 15. 一句话结论

`quote_orchestration_skill` 的设计目标不是把现有智能报价系统重新做一遍，而是把现有已验证的 Hybrid workflow 实现封装成一个符合 Agent Skill 规范、OpenClaw 规范和渐进式披露思想的唯一对外 workflow 入口。
