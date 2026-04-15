# Workflow Contract

`quote_orchestration_skill` 是面向 Agent 的顶层 workflow skill。

## Input

- 直接复用 `.opencode/skills/quote_orchestration_skill/workflow/schemas/input.schema.json` 的输入骨架
- 支持完整执行、交互式暂停和恢复执行

## Output

- 直接复用 `.opencode/skills/quote_orchestration_skill/workflow/schemas/output.schema.json` 的输出骨架
- 输出中保留完整中间结果、最终报价结果和 planner trace

## Design Notes

- 对 Agent 暴露统一入口
- 对内部由 `quote_orchestration_skill/workflow/` 提供已验证的 workflow 实现
- 不改变现有底层 skill 的职责边界
