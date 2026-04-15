# AGENTS.md

## 仓库形态
- 这个仓库的可执行事实来源在 `.opencode/` 下，不在仓库根目录。
- 最终 QuoteDocument 契约是 `.opencode/quote-document-v1.1.schema.json`；`.opencode/quote-document-v1.1-example.json` 是标准完整示例。
- 业务与架构上下文在 `设计与规范/` 下，优先看 `设计与规范/智能报价 Agent Skill 设计说明书.md`。

## 实际工作流
- 不要从仓库根目录臆造 `pytest`、`ruff`、`mypy`、`npm`、`make` 或 CI 命令。仓库根目录没有已验证的 manifest、任务运行器或工作流配置。
- 当前唯一对外 workflow 入口是 `.opencode/skills/quote_orchestration_skill/`。
- `quote_orchestration_skill` 内部 workflow 实现在 `.opencode/skills/quote_orchestration_skill/workflow/`，这是当前唯一维护中的编排实现。
- `.opencode/quote_orchestrator/` 仅保留兼容层和历史样例，不再是维护主目录。
- 修改某个 skill 前，先读该 skill 的 `SKILL.md`、`references/`、`samples/`、`run.py` 和必要的内部实现目录。`quote_orchestration_skill` 还应优先看 `workflow/`。

## 已验证命令
- 使用仓库自带解释器：`& ".opencode/.venv/Scripts/python.exe" ...`。
- 单个 skill 的样例契约校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/validate_samples.py"`
- 单个 skill 的定向手动运行：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/run.py" --input ".opencode/skills/<skill_name>/samples/sample-input.json"`
- 顶层 workflow skill 的样例契约校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_orchestration_skill/validate_samples.py"`
- 顶层 workflow skill 的定向手动运行：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_orchestration_skill/run.py" --input ".opencode/skills/quote_orchestration_skill/samples/sample-input.json"`
- 兼容层入口仍可运行，但仅用于兼容旧路径：`& ".opencode/.venv/Scripts/python.exe" ".opencode/quote_orchestrator/run.py" --input ".opencode/quote_orchestrator/examples/input.dimitra-m.json"`
- `run.py` 默认会校验输入和输出 schema；存在 `--skip-schema-validation`，所以不要把默认运行当成“无校验”。
- `quote_pricing_skill` 的输出校验还会解析 `.opencode/quote-document-v1.1.schema.json` 引用；如果改了 pricing 输出，要验证这个 skill，不要只看它本地的 schema 文件。

## QuoteDocument 易错规则
- 顶层必填键是固定的：`document_type`、`document_version`、`header`、`table_schema`、`quotation_options`、`footer`、`review_result`、`trace`。
- `document_type` 是 schema `const`，必须保持为 `quotation`。
- `header` 是固定 13 字段对象，且 `additionalProperties: false`；缺键就会破坏契约。
- `table_schema.columns` 是固定长度且有顺序的。必须严格保留这 7 列，顺序为：`item`、`description`、`unit_price`、`unit`、`qty`、`discount`、`amount`。
- `quotation_options[*]` 必须包含 `option_id`、`title`、`sections`、`summary`、`remarks`。
- `section.section_type` 只允许 `service`、`spare_parts`、`other`。
- group 级 summary 是明确不支持的。summary 只保留在 option 级和 footer 级。
- 每一行都必须带完整 schema 形状，包括 `unit_price_display`、`qty_display`、`amount_display` 这类展示字段，即使是纯文本行也一样。
- 折扣要用结构化 `discount`，不要把折扣文本藏在 `description` 里。
- `line_type`、`pricing_mode`、`status` 都受枚举约束，仓库就是靠它们表达待确认、额外收费、按实结算、船东提供等状态；不要改成自由文本约定。
- `footer` 是必填，且必须包含 `summary`、`remark`、`service_payment_terms`。
- `remark.title` 是 schema `const`，必须等于 `Remark`；`service_payment_terms.title` 必须等于 `Service Payment Terms`。
- `summary` 的值是结构化对象，不是普通数字。多方案报价时，绝不要把多个 option summary 直接相加写进 footer total。
- `review_result` 和 `trace` 是最终输出的正式组成部分，不是可选元数据。

## 仓库特有注意点
- 文档优先级低于可执行契约。如果 prose、example 和 schema 冲突，以 `.opencode/quote-document-v1.1.schema.json` 以及各 skill 的 schema/run 脚本为准。
- `quote_orchestration_skill` 的真实内部实现位于 `.opencode/skills/quote_orchestration_skill/workflow/`；不要再把 `.opencode/quote_orchestrator/` 当成主实现目录修改。
- 各 skill 的 `SKILL.md` 里仍可能引用较旧的详细设计命名；以 `设计与规范/` 中现有实际文件名和对应 skill 目录为准。
- `.opencode/.env` 是本地敏感文件，而且 `.gitignore` 没有忽略它；不要提交。
- 除非任务明确与本地环境有关，否则避免搜索或编辑 `.opencode/.venv/` 和 `.ruff_cache/`。
