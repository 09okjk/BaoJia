# AGENTS.md

## 仓库形态
- 这是一个以规范为中心的仓库，不是应用代码仓库：`main.py` 为空，根目录也没有已验证的构建、测试、CI 或任务运行配置。
- 可执行层面的事实来源是 `quote-document-v1.1.schema.json`；`quote-document-v1.1-example.json` 可作为标准结构示例。
- 业务背景资料在 `设计与规范/` 下，优先看 `设计与规范/智能报价 Agent Skill 设计说明书.md`。

## 工作假设
- 不要臆造 `pytest`、`ruff`、`mypy`、`npm`、`make`、`pre-commit` 之类命令，除非你在同一次修改里补上对应配置；当前仓库并未定义这些入口。
- 优先基于 JSON Schema 和示例文档验证修改，不要假设这里存在可运行应用。
- 说明文档只作上下文参考；如果文档、示例、Schema 不一致，以 Schema 为准。

## QuoteDocument 不变量
- 顶层必填键固定为：`document_type`、`document_version`、`header`、`table_schema`、`quotation_options`、`footer`、`review_result`、`trace`。
- `document_type` 必须保持为 `quotation`。
- `header` 是固定宽度对象：13 个字段全部必填，即使值为空字符串也不能省略。
- `table_schema.columns` 是严格定长且有序的：必须且只能按以下顺序保留 7 列：`item`、`description`、`unit_price`、`unit`、`qty`、`discount`、`amount`。
- Schema 各层普遍设置了 `additionalProperties: false`，多余字段会直接导致文档无效。
- `footer` 必填，且必须同时包含 `summary`、`remark`、`service_payment_terms`。
- `remark.title` 必须严格等于 `Remark`，`service_payment_terms.title` 必须严格等于 `Service Payment Terms`。
- `review_result` 和 `trace` 是正式输出的一部分，不是可选元数据。

## 报价结构
- `quotation_options` 同时支持单方案和多方案报价；不要把多方案压平成一个总摘要。
- 每个 option 都必须包含 `option_id`、`title`、`sections`、`summary`、`remarks`。
- `section.section_type` 只允许 `service`、`spare_parts`、`other`。
- schema v1.1 / 设计说明书 V2.2 明确不支持 group 级 summary；汇总只放在 option summary 和 footer summary。

## 行项目建模
- 每一行都必须带齐 Schema 要求的完整字段，包括 `unit_price_display`、`qty_display`、`amount_display` 这类展示字段。
- 有折扣时不要把折扣信息藏进 `description`，要使用结构化 `discount` 对象。
- 非价格文本行也是一等公民；优先使用现有枚举值，例如 `header`、`scope_note`、`technical_note`、`assumption_note`、`commercial_note`，不要自造形状。
- 不确定信息必须显式表达。设计说明书明确要求不要默认补全缺失业务事实；用 `line_type`、`pricing_mode`、`status` 和 summary 的显示文本表达待确认、按实际、额外收费、船东提供等状态。

## 仓库卫生
- 根目录存在 `.env`，但 `.gitignore` 并未忽略它；把它视为敏感本地文件，不要提交。
- `.venv/` 已被忽略；除非在排查本地环境问题，否则不要进入或搜索其中内容。
