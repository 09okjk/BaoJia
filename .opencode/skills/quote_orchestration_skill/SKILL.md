---
name: quote-orchestration-skill
slug: quote-orchestration-skill
version: 1.0.0
author: "BaoJia Team"
description: 统一封装完整智能报价流程，接收 assessment_report 与补充上下文，内部调用 orchestrator 输出最终报价结果、暂停状态和结构化 trace。当用户提到整单智能报价、完整报价流程执行、暂停后恢复、生成 QuoteDocument 或 HTML/PDF 报价时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-orchestration-skill

## When to Use（何时使用）

- 需要从 `assessment_report` 启动整条智能报价链路
- 需要让 Agent 用一个统一入口完成模板选择、标准化、可报价判断、历史参考、定价、输出组装与可选渲染
- 需要处理交互式 `pause / resume`
- 需要输出最终 `QuoteDocument`、结构化 trace 或可选的 HTML/PDF 渲染结果

## When NOT to Use（何时不用）

- 只想单独做某一个底层能力，例如仅标准化、仅可报价判断、仅历史参考、仅定价或仅渲染
- 已经拿到完整 `QuoteDocument`，只需要单独渲染文件
- 只想研究某个阶段的局部行为而不需要跑完整流程

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "assessment_report": {},
  "customer_context": {},
  "business_context": {},
  "render_options": {}
}
```

最小输出骨架：

```json
{
  "template_selection_result": {},
  "prepare_result": {},
  "feasibility_result": {},
  "historical_reference": {},
  "pricing_result": {},
  "quote_document": {},
  "orchestration_status": "completed",
  "execution_trace": [],
  "planner_trace": [],
  "skipped_skills": [],
  "applied_planner_strategies": []
}
```

## Core Behavior（核心行为）

- 这是面向 Agent 的唯一对外工作流 skill，不替代底层 skill，而是统一封装本 skill 内部的 workflow 实现
- 内部调用 `quote_orchestration_skill/workflow/` 下的工作流实现
- 默认返回完整中间结果、最终报价结果和结构化 trace
- 遇到明确待确认事项时，可返回 `paused` 状态，而不是伪造完整报价
- 恢复时接收 `resume_payload` 和 `confirmed_answers`，从已暂停状态继续执行

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 结构契约：`references/WORKFLOW_CONTRACT.md`
- 正式 Schema：`references/quote-orchestration-input.schema.json`、`references/quote-orchestration-output.schema.json`
- 详细设计：`设计与规范/quote_orchestration_skill 设计说明.md`
- 设计方案：`设计与规范/Hybrid 智能编排方案设计.md`
- 评审结论：`设计与规范/当前智能报价流程评审结论.md`
- 方案对照：`设计与规范/Hybrid 智能编排方案与当前实现对照表.md`

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_orchestration_skill/scripts/main.py" --input ".opencode/skills/quote_orchestration_skill/samples/sample-input.json"`
- 内部依赖：`.opencode/skills/quote_orchestration_skill/workflow/`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过输入输出 schema 校验，可选

## Core Rules（核心规则）

- Agent 做整单报价时，应调用本 skill，而不是自行拼装底层 skill 顺序
- 底层 skill 仍然保持职责分离，本 skill 只做顶层工作流封装
- `paused` 必须是正式状态，不得把待确认事实伪装成完整完成
- 输出必须保留 `execution_trace`、`planner_trace`、`skipped_skills` 与 `applied_planner_strategies`

## Security & Privacy（安全说明）

- 当前处理默认在本地完成
- 输入和输出可能包含客户、船舶、报价与历史参考信息，日志和样例应避免泄露真实敏感数据
- 恢复输入中的 `resume_payload` 可能含完整中间结果，外部使用时应控制访问范围

## Related Skills（相关技能）

- `quote-template-select-skill`
- `quote-request-prepare-skill`
- `quote-feasibility-check-skill`
- `historical-quote-reference-skill`
- `quote-pricing-skill`
- `quote-review-output-skill`
- `quote-pdf-render-skill`

## Feedback（反馈）

- 修改 workflow 输入输出契约时同步更新 `references/*.schema.json`、`samples/` 与 orchestrator schema
- 新增 planner 能力时同步更新本 skill 的 `Core Behavior` 与 `Core Rules`
