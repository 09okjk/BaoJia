# AGENTS.md

## 仓库形态
- 这个仓库的可执行事实来源在 `.opencode/` 下，不在仓库根目录。
- 最终 QuoteDocument 契约是 `.opencode/quote-document-v1.1.schema.json`；`.opencode/quote-document-v1.1-example.json` 是标准完整示例。
- 业务与架构上下文在 `设计与规范/` 下，优先看 `设计与规范/智能报价 Agent Skill 设计说明书.md`。

## 实际工作流
- 不要从仓库根目录臆造 `pytest`、`ruff`、`mypy`、`npm`、`make` 或 CI 命令。仓库根目录没有已验证的 manifest、任务运行器或工作流配置。
- 当前已实现的链路是 `.opencode/skills/` 下的五个本地 skill：`quote_request_prepare_skill` -> `quote_feasibility_check_skill` -> `historical_quote_reference_skill` -> `quote_pricing_skill` -> `quote_review_output_skill`。
- 修改某个 skill 前，先读该 skill 的 `SKILL.md`、`schemas/`、`examples/` 和 `run.py`。这些文件定义了契约和准确的 CLI 入口。

## 已验证命令
- 使用仓库自带解释器：`& ".opencode/.venv/Scripts/python.exe" ...`。
- 单个 skill 的样例契约校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/validate_samples.py"`
- 单个 skill 的定向手动运行：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/<skill_name>/run.py" --input ".opencode/skills/<skill_name>/examples/input.sample.json"`
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
- 各 skill 的 `SKILL.md` 里仍然用的是简化版详细设计文档名；`设计与规范/` 下真实文件名是 `S1-...` 到 `S5-...`。
- `.opencode/.env` 是本地敏感文件，而且 `.gitignore` 没有忽略它；不要提交。
- 除非任务明确与本地环境有关，否则避免搜索或编辑 `.opencode/.venv/` 和 `.ruff_cache/`。
