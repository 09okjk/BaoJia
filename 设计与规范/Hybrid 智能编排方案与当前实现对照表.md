# Hybrid 智能编排方案与当前实现对照表

## 文档导航

本文定位：说明 Hybrid 设计目标与当前实现状态“是如何一一对应的”。

推荐阅读顺序：

1. `设计与规范/Hybrid 智能编排方案设计.md`
2. `设计与规范/当前智能报价流程评审结论.md`
3. `设计与规范/Hybrid 智能编排方案与当前实现对照表.md`

相关文档：

- `设计与规范/Hybrid 智能编排方案设计.md`
- `设计与规范/当前智能报价流程评审结论.md`

## 1. 文档目的

本文用于对照以下两份文档：

- `设计与规范/Hybrid 智能编排方案设计.md`
- `设计与规范/当前智能报价流程评审结论.md`

目标是把“设计目标”和“当前达成状态”放在同一张表里，便于后续判断：

1. 哪些目标已经落地。
2. 哪些目标已部分实现。
3. 哪些目标属于后续增强项。
4. 哪些事项当前不应作为阻塞问题处理。

## 2. 总体判断

总体上，当前实现与 Hybrid 方案设计方向是一致的。

当前状态可以概括为：

1. 核心架构方向已落地。
2. 第一阶段 Hybrid 目标已基本完成。
3. 第二阶段中的关键能力已经落地一部分，包括 `pause / resume`、S3 价值判断、多方案策略注入。
4. 仍有少量“增强型解释层”和“更强声明式化能力”未完全收口，但不影响当前方案成立。

## 3. 设计目标与当前状态对照

| 设计目标 | 设计文档中的要求 | 当前实现状态 | 判断 |
| --- | --- | --- | --- |
| 确定性骨架 + 智能分支 | 保留 orchestrator 稳定性，同时允许智能选择可选节点 | 已实现 `WorkflowState + PlannerDecision + policy`，核心链路稳定，可选节点已可智能判断 | 已达成 |
| Skill 文档参与运行时调度 | `SKILL.md` 中高层语义进入 registry 与 planner | 已实现 skill registry，planner 已基于高层语义和状态做部分决策 | 已达成 |
| 状态驱动而非纯步骤驱动 | orchestrator 要理解当前中间产物，而不只是“第几步” | 已基于 `template_selection_result / prepare_result / feasibility_result / pricing_result / quote_document` 做状态判断 | 已达成 |
| 失败必须结构化 | 缺字段、待确认、跳过、暂停都要结构化表达 | 已有 `orchestration_status`、`pause_reason`、`questions_for_user`、`review_flags`、`skipped_skills` | 已达成 |
| S0 可选化 | 模板选择在部分场景可跳过 | 已支持 `force_template_type` 等跳过逻辑 | 已达成 |
| S3 可选化 | 历史参考按价值判断是否执行 | 已支持显式跳过、快速报价跳过、结构价值驱动执行，并记录 `historical_reference_strategy` | 已达成 |
| S6 可选化 | 未请求渲染时可跳过 | 已实现基于 `render_options` 的可选渲染逻辑 | 已达成 |
| 暂停机制 | 在明确需要人工确认时返回 `pause` | 已支持 `interactive_mode` 下的 `pause` 行为 | 已达成 |
| 恢复机制 | 从暂停状态继续执行后续链路 | 已支持 `resume_payload` + `confirmed_answers` 恢复 | 已达成 |
| 渐进式披露进入运行时 | planner 只消费高层语义，不直接依赖深层示例 | 当前 registry/planner 已按该思路工作 | 已达成 |
| 输出增强 | 增加 execution/planner/skipped 等 trace | 已输出 `execution_trace`、`planner_trace`、`skipped_skills`、`applied_planner_strategies` | 已达成 |
| 多方案策略注入 | planner 可驱动 pricing 多方案行为 | 已支持 `force_multi_option`、`option_hints` 注入 pricing | 已达成 |
| S3 决策可解释 | 历史参考为什么执行/跳过要有理由 | 已通过 `planner_trace` 和 `historical_reference_strategy` 结构化表达 | 已达成 |
| 统一高层摘要层 | 对 planner 决策有统一 summary 层 | 目前已有 trace 和 strategy，但尚无单独 `planner_summary` | 部分达成 |
| 更强声明式调度 | 调度规则更多由配置或文档推导，而非代码硬编码 | 当前仍以 Python 规则为主，文档只参与高层语义 | 部分达成 |
| 纯 OpenClaw 原生 runtime | 完全由通用 OpenClaw runtime 驱动 skill 调度 | 当前仍是自研 Hybrid orchestrator | 未达成但当前不要求 |

## 4. 已经对齐的关键点

### 4.1 设计方向与实现方向一致

当前实现并没有偏离 Hybrid 方案，而是在沿着原设计逐步落地，尤其体现在以下几点：

1. 没有把 orchestrator 推翻重做为完全不可控的 agent。
2. 没有回退到“所有 skill 固定必跑”的纯串联脚本模式。
3. 没有把 `SKILL.md` 只停留在发布态摆设，而是开始服务于 registry 和调度语义。

### 4.2 第二阶段关键目标已有实质进展

当前第二阶段中最关键的三项里，已有以下结果：

1. `pause / resume` 已可用。
2. S3 历史参考是否值得执行，已从简单布尔条件升级为结构化价值判断。
3. planner 驱动的多方案注入已经可以影响 pricing 输出。

这说明当前实现已不是“只完成第一阶段”，而是已经进入第二阶段的可用状态。

## 5. 仍存在但不影响当前结论的差距

### 5.1 缺少统一摘要层

目前 trace 已较丰富，但用户若想快速读取“本次编排的总体决策”，仍需结合多个字段查看。

当前缺口包括：

- 没有统一 `planner_summary`
- 没有统一 `decision_rationale`
- 可选 skill 决策尚未聚合为单独高层摘要块

判断：属于增强项，不影响当前方案成立。

### 5.2 规则仍以代码实现为主

当前 planner 规则仍主要沉淀在 Python 中，这意味着：

1. 可解释性已经存在。
2. 但声明式程度还不高。
3. 后续若继续扩展更多智能点，需要注意避免 planner 规则分散失控。

判断：属于演进注意项，不是当前阻塞项。

### 5.3 不是纯 OpenClaw 原生编排

当前实现仍是 Hybrid orchestrator，而非通用原生 OpenClaw runtime 驱动。

判断：这是当前阶段的合理边界，不建议视为缺陷。

## 6. 推荐解释口径

后续对内或对外描述当前系统时，建议使用以下口径：

### 6.1 推荐说法

“当前系统已实现基于 OpenClaw 风格 skill 发布态的 Hybrid 智能报价编排。核心链路保持确定性，部分节点可按状态和语义进行智能选择，且已支持结构化 trace、pause / resume 与渐进式披露驱动的调度。”

### 6.2 不推荐说法

不建议简单描述为：

- “已经完全是 OpenClaw 原生系统”
- “已经完全声明式化”
- “已经不再依赖 orchestrator”

这些说法会放大当前尚未追求的目标，反而使系统定位失真。

## 7. 最终结论

结合设计目标与当前实现状态，可以给出以下正式结论：

1. 当前实现与 Hybrid 设计方案总体一致，没有方向性偏差。
2. 方案中的核心能力已经基本落地，当前系统已具备稳定、可解释、可恢复的智能报价编排能力。
3. 当前剩余差距主要集中在“更强的摘要层”和“更高程度的声明式化”，属于增强项，而非缺陷项。
4. 因此，当前最合适的策略仍然是在现有 Hybrid 路径上持续收敛和增强，而不是进行方向性重构。

## 8. 一句话结论

Hybrid 方案设计与当前实现已经基本对齐，当前系统处于“方案成立、实现可用、后续继续增强解释力与声明式程度”的健康状态。
