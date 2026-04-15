# Hybrid 智能编排方案设计

## 文档导航

本文定位：说明 Hybrid 智能编排方案“应该如何设计”。

推荐阅读顺序：

1. `设计与规范/Hybrid 智能编排方案设计.md`
2. `设计与规范/当前智能报价流程评审结论.md`
3. `设计与规范/Hybrid 智能编排方案与当前实现对照表.md`

相关文档：

- `设计与规范/当前智能报价流程评审结论.md`
- `设计与规范/Hybrid 智能编排方案与当前实现对照表.md`

## 1. 目标

当前 `.opencode/quote_orchestrator/run.py` 采用固定顺序的代码式编排，优点是稳定、可预测，但不会在运行时利用 OpenClaw Skill 的 `SKILL.md`、`samples/`、`references/` 等发布态能力。

本方案目标是：

1. 保留现有 orchestrator 的稳定性与可控性。
2. 让 skill 能够被“按需智能调用”，而不是所有节点都固定必跑。
3. 让 `SKILL.md` 中的渐进式披露信息真正参与调度决策。
4. 不引入一个新的“独立智能评估系统”作为前置依赖，输入仍然可以直接是 `assessment_report`。

## 2. 设计原则

### 2.1 确定性骨架 + 智能分支

- 核心顺序约束继续由 orchestrator 代码保证。
- 可选节点、跳过策略、人工确认暂停策略由 planner 决策。

### 2.2 Skill 文档参与运行时调度，但不直接作为执行器

- `SKILL.md` 用于构建 skill registry 和调度提示。
- 实际执行仍由 `skill.py` / `run.py` 完成。

### 2.3 状态驱动，而不是纯步骤驱动

- orchestrator 不再只理解“第几步”。
- orchestrator 需要理解“当前已经具备哪些结构化产物”。

### 2.4 失败必须结构化

- 无论是缺输入、低置信度、待确认项过多，还是可选 skill 被跳过，都必须以结构化状态返回。

## 3. 分层架构

### 3.1 State Layer

负责描述当前流程状态，建议以 `WorkflowState` 维护：

- 原始输入：`assessment_report`、`customer_context`、`business_context`、`render_options`
- 中间结果：`template_selection_result`、`prepare_result`、`feasibility_result`、`historical_reference`、`pricing_result`、`quote_document`、`render_result`
- 状态标记：
  - `template_selected`
  - `quote_request_ready`
  - `feasibility_ready`
  - `pricing_ready`
  - `document_ready`
  - `render_done`
  - `paused_for_confirmation`

### 3.2 Skill Registry Layer

负责把 skill 发布态元数据转换成调度时可用索引。输入来源：

- `SKILL.md`
- `_meta.json`

推荐抽取字段：

- `skill_id`
- `description`
- `when_to_use`
- `when_not_to_use`
- `core_behavior`
- `required_inputs`
- `produced_outputs`
- `is_optional`
- `supports_pause`

说明：当前仓库中 `SKILL.md` 已完成渐进式披露改造，因此 registry 主要消费 `When to Use`、`When NOT to Use`、`Core Behavior`。

### 3.3 Policy Layer

负责硬约束校验，不允许 planner 越界。关键规则：

1. 没有 `quote_request` 时，不能进入 S2/S3/S4/S5/S6。
2. 没有 `feasibility_result` 时，不能进入 S4/S5/S6。
3. 没有 `pricing_result` 时，不能进入 S5/S6。
4. 没有 `quote_document` 时，不能进入 S6。
5. `render_options` 未启用时，不进入 S6。

### 3.4 Planner Layer

负责“下一个动作”的智能决策。planner 输出建议形态：

```json
{
  "action": "run_skill | pause | finish",
  "skill_name": "quote_pricing_skill",
  "reason": "feasibility_result already available and historical reference is optional for this case",
  "decision_type": "required | optional | skipped",
  "planner_notes": []
}
```

### 3.5 Executor Layer

负责实际执行 skill：

- 调用 `skill.py` 导出的主函数
- 校验输入输出
- 更新 state
- 记录执行 trace

## 4. 混合编排策略

### 4.1 必经节点

以下节点默认视为必经：

1. S1 `quote_request_prepare_skill`
2. S2 `quote_feasibility_check_skill`
3. S4 `quote_pricing_skill`
4. S5 `quote_review_output_skill`

说明：S0 和 S6 取决于输入与渲染参数，S3 可智能跳过。

### 4.2 可选节点

#### S0 `quote_template_select_skill`

在以下场景可跳过：

- `business_context.force_template_type` 已提供且合法
- `render_options.template_type` 已显式指定且与业务上下文一致

#### S3 `historical_quote_reference_skill`

在以下场景可跳过：

- `feasibility_result.quote_scope = not_ready`
- `quotable_items` 为空
- `business_context.skip_historical_reference = true`
- planner 判定当前仅需快速报价草案

#### S6 `quote_pdf_render_skill`

在以下场景可跳过：

- `render_options.enabled != true`
- `render_options.languages` 为空或不存在

### 4.3 暂停节点

当满足以下条件时，planner 可返回 `pause`：

- `template_selection_result.needs_manual_confirmation = true`
- `feasibility_result.quote_scope = not_ready`
- `feasibility_result.questions_for_user` 非空且阻断严重

暂停时建议输出：

```json
{
  "orchestration_status": "paused",
  "pause_reason": "manual_confirmation_required",
  "questions_for_user": [],
  "review_flags": []
}
```

## 5. 渐进式披露在运行时的作用

### 5.1 当前问题

固定顺序 orchestrator 在运行时不会读取 `SKILL.md`，因此渐进式披露只对人类和发布态有价值，对调度逻辑无直接影响。

### 5.2 Hybrid 方案中的利用方式

通过 skill registry 提取 `SKILL.md` 前两层信息：

- `When to Use`
- `When NOT to Use`
- `Core Behavior`

planner 在运行时只依赖这几类高层语义，不直接消费冗长的深层示例。这样：

1. `SKILL.md` 参与了实际调度。
2. 渐进式披露避免把深层细节暴露给 planner。
3. 深层内容继续保留给人类维护者和深入排障使用。

## 6. 推荐最小落地范围

第一阶段仅做 3 个智能点：

1. S0 是否跳过
2. S3 是否调用
3. 是否暂停并请求人工确认

这样可以最大化复用现有 orchestrator 逻辑，避免一次性重构为完全 agent-driven 调度。

## 7. 模块拆分建议

新增目录：`.opencode/quote_orchestrator/`

- `state.py`
- `skill_registry.py`
- `planner.py`
- `policy.py`

### 7.1 state.py

定义：

- `WorkflowState`
- `build_initial_state(payload)`
- `derive_state_flags(state)`

### 7.2 skill_registry.py

定义：

- `SkillRegistryEntry`
- `load_skill_registry(skills_dir)`

当前仓库中可以先用静态注册 + 轻量 Markdown 提取实现，后续再增强。

### 7.3 policy.py

定义：

- `can_run_skill(state, skill_name)`
- `required_next_skills(state)`

### 7.4 planner.py

定义：

- `PlannerDecision`
- `plan_next_action(state, registry)`

## 8. 对现有 orchestrator 的最小改造思路

当前：`orchestrate_quote(payload)` 内固定顺序调用 skill。

改造后：

1. 初始化 state
2. 构建 registry
3. 循环调用 planner
4. planner 返回下一个 action
5. executor 执行对应 skill 并回写 state
6. 直到 `finish` 或 `pause`

## 9. 输出增强建议

为便于调试与审计，建议在 orchestrator 输出中新增：

- `orchestration_status`
- `execution_trace`
- `planner_trace`
- `skipped_skills`

其中：

- `execution_trace`：实际执行过的 skill 顺序
- `planner_trace`：每一步 planner 的决策理由
- `skipped_skills`：被判断为可跳过的 skill 及原因

## 10. 风险与边界

### 10.1 风险

- 过度智能化会降低可预测性
- planner 如果无约束，可能绕过必要步骤
- 低质量 registry 会让 skill 选择失真

### 10.2 边界

- Hybrid 不等于完全 LLM 驱动
- 核心顺序仍由 policy 固定
- planner 只决定“可选节点是否执行”与“是否暂停”

## 11. 当前版本实施建议

当前仓库建议按以下顺序实施：

1. 新增 `WorkflowState`
2. 新增轻量 `SkillRegistry`
3. 新增 `PlannerDecision`
4. 在 orchestrator 中替换 S0/S3/S6 的固定调用逻辑
5. 增加 `pause` 输出
6. 增加 `execution_trace` 和 `planner_trace`

## 12. 预期收益

1. skill 文档不再只是发布资料，而是运行时调度输入。
2. orchestrator 仍然稳定，不会退化成完全不可控的 agent。
3. 用户可以从同一套 skill 体系同时获得：
   - 发布态 OpenClaw skill
   - 稳定的生产流水线
   - 局部智能决策能力
