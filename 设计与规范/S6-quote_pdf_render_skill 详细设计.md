# `quote_pdf_render_skill` 详细设计

## 1. 文档目的

本文用于细化第六个 Skill：`quote_pdf_render_skill` 的设计，作为后续开发、联调和验收参考。

本设计严格对齐《智能报价 Agent Skill 设计说明书（V2.2）》中的以下原则：

- 智能报价 Agent 的最终核心产物仍然是 `QuoteDocument JSON`
- PDF / HTML / Word / Excel 渲染属于 `QuoteDocument` 之后的模板渲染层
- 渲染能力不应污染前五个核心报价 Skill 的职责边界
- 输入输出仍然使用结构化 JSON 契约，而不是自由文本命令

---

## 2. Skill 定位

`quote_pdf_render_skill` 是智能报价链路中的后处理导出层。

它接收最终 `quote_document`，调用 Skill 内部渲染逻辑，生成正式报价单 HTML/PDF 文件。

它回答的核心问题是：

1. 如何在不修改 `quote_document` 的前提下生成正式文件
2. 如何同时支持中文、英文或双语输出
3. 如何把文件导出结果结构化返回给上游编排层或调用方

---

## 3. 目标与非目标

## 3.1 目标

- 接收 `quote_document`
- 支持中文、英文或双语渲染
- 输出 HTML/PDF 文件
- 返回结构化文件路径和渲染状态
- 能被 `quote_orchestrator` 作为可选最后一步调用
- Skill 自带模板、资源和核心渲染代码，不再依赖 `quotation-pdf` 子项目运行

## 3.2 非目标

以下内容不属于本 Skill：

- 不重新计算金额
- 不重建 `quotation_options`
- 不重新生成 `footer`
- 不修改 `review_result`、`trace`
- 不负责邮件发送、审批流或归档入库

本 Skill 仅负责从最终结构化报价文档到模板文件的渲染导出。

---

## 4. 上下游关系

## 4.1 上游输入

本 Skill 直接接收：

```json
{
  "quote_document": {},
  "render_options": {}
}
```

同时为了兼容编排层，也允许接收完整 orchestrator 输出对象，只要其中存在：

- `quote_document`
或
- `review_output.quote_document`

## 4.2 下游输出

本 Skill 输出：

```json
{
  "render_result": {
    "document_type": "quotation",
    "document_version": "1.1",
    "outputs": []
  }
}
```

其中每个 output 记录一个语言版本的文件结果。

---

## 5. 设计原则

## 5.1 不改业务内容，只做渲染

Skill 不得修改 `quote_document` 的业务含义，只允许进行展示层映射和文件输出。

## 5.2 核心报价链路与导出链路分离

前五个 Skill 负责“生成 QuoteDocument”，本 Skill 负责“渲染 QuoteDocument”。

## 5.3 输出必须结构化可追踪

无论成功或失败，都必须结构化返回结果，而不是仅打印日志。

## 5.4 双语输出应拆分记录

中文、英文文件必须分别记录：

- `language`
- `html_path`
- `pdf_path`
- `status`
- `error`（如失败）

## 5.5 Skill 自包含优先

Skill 优先自带：

- 模板文件
- 图片资源
- QuoteDocument 映射逻辑
- HTML 渲染逻辑
- PDF 渲染逻辑

避免运行时依赖仓库内其他子项目。

---

## 6. 输入详细设计

## 6.1 输入对象

```json
{
  "quote_document": {},
  "render_options": {
    "languages": ["zh", "en"],
    "output_dir": ".opencode/skills/quote_pdf_render_skill/out"
  }
}
```

## 6.2 输入字段要求

### `quote_document`

必须满足最终 `quote-document-v1.1.schema.json` 约束。

### `render_options.languages`

可选，允许：

- `zh`
- `en`

若缺省，默认输出：

- `zh`

### `render_options.output_dir`

可选，表示 HTML/PDF 输出目录。

若缺省，默认使用：

- `.opencode/skills/quote_pdf_render_skill/out`

说明：

- 当单独运行 Skill 时，建议使用 Skill 自己的 `out/` 目录
- 当由 `quote_orchestrator` 集成调用时，建议输出到 orchestrator 自己的任务目录，便于每次报价的输入、JSON 结果与 HTML/PDF 产物归档在同一路径下

---

## 7. 输出详细设计

## 7.1 输出对象

```json
{
  "render_result": {
    "document_type": "quotation",
    "document_version": "1.1",
    "outputs": []
  }
}
```

## 7.2 `render_result.outputs[*]`

每个输出元素必须包含：

- `language`
- `html_path`
- `pdf_path`
- `status`

可选：

- `error`

### 成功示例

```json
{
  "language": "zh",
  "html_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-zh.html",
  "pdf_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-zh.pdf",
  "status": "success"
}
```

### 失败示例

```json
{
  "language": "zh",
  "html_path": "",
  "pdf_path": "",
  "status": "failed",
  "error": "Rendered files not found after CLI execution."
}
```

---

## 8. 关键模块设计

## 8.1 输入抽取模块

Skill 允许两种输入来源：

1. 直接 `payload.quote_document`
2. `payload.review_output.quote_document`

若两者都不存在，则报错。

## 8.2 Schema 校验模块

输入阶段校验：

- `render_options` 结构
- `quote_document` 最终契约

输出阶段校验：

- `render_result` 结构

## 8.3 QuoteDocument 映射模块

由 `quote_document_mapper.py` 负责：

- 读取 `quote_document`
- 校验最终 schema
- 映射为 `EngineeringPdfContext`
- 生成原报价模板所需的 `form_data`

该模块是 Skill 内部自带逻辑，不再依赖 `quotation-pdf` 的 Python 代码。

## 8.4 HTML 渲染模块

由 `html_renderer.py` 负责：

- 接收 `EngineeringPdfContext`
- 输出完整 HTML 文本
- 使用 Skill 自带图片资源生成本地 `file://` 资源 URI
- 当前实现以内联 HTML/CSS 方式输出与既有报价模板风格一致的页面结构

## 8.5 PDF 渲染模块

由 `pdf_renderer.py` 负责：

- 优先使用 `weasyprint`
- Chromium / Edge headless print-to-pdf 作为回退方案
- `wkhtmltopdf` 作为最终兜底方案

当前实现不依赖 `jinja2`、`pydantic` 等模板或建模三方包；若环境可用，则优先使用 `weasyprint` 提供更稳定的分页与页眉表现。

## 8.6 资源路径模块

Skill 自带：

- `assets/`

当前实现的核心资源是 `assets/` 下的品牌图片与 `html_renderer.py` / `quote_document_mapper.py` / `pdf_renderer.py` 三个内部模块；不再依赖独立模板文件落盘存在。

## 8.7 输出路径推导模块

Skill 基于：

- `quote_document.header.wk_offer_no`
- `language`

推导预期输出文件名：

- `报价单-<wk_offer_no>-zh.html`
- `报价单-<wk_offer_no>-zh.pdf`
- `报价单-<wk_offer_no>-en.html`
- `报价单-<wk_offer_no>-en.pdf`

---

## 9. 处理流程设计

建议流程如下：

```text
1. 检查输入结构完整性
2. 提取 quote_document
3. 解析 render_options
4. 针对每个 language 构建 EngineeringPdfContext
5. 调用 Skill 内部 HTML 渲染模块
6. 调用 Skill 内部 PDF 渲染模块
7. 组装 render_result.outputs
8. 返回 render_result
```

---

## 10. 依赖设计

## 10.1 当前实现依赖

当前 Skill 已经不再依赖 `quotation-pdf` 子项目运行。

Skill 自带：

1. 数据映射逻辑
2. HTML 渲染逻辑
3. PDF 渲染逻辑
4. 模板资源与图片资源

## 10.2 仍保留的外部运行依赖

虽然 Skill 已自包含，但 PDF 输出仍依赖系统可用的 PDF 后端之一：

1. `weasyprint`（若当前 Python 环境可导入）
2. Chrome / Edge headless
3. `wkhtmltopdf`

这属于系统级运行依赖，不属于仓库内代码依赖。

## 10.3 当前状态评价

当前版本已经符合“Skill 自包含”的主要目标，不再依赖 `quotation-pdf` 作为运行前提。

---

## 11. 示例

## 11.1 输入示例

```json
{
  "quote_document": {},
  "render_options": {
    "languages": ["zh", "en"],
    "output_dir": ".opencode/skills/quote_pdf_render_skill/out"
  }
}
```

## 11.2 输出示例

```json
{
  "render_result": {
    "document_type": "quotation",
    "document_version": "1.1",
    "outputs": [
      {
        "language": "zh",
        "html_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-zh.html",
        "pdf_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-zh.pdf",
        "status": "success"
      },
      {
        "language": "en",
        "html_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-en.html",
        "pdf_path": "E:\\PythonProjects\\BaoJia\\.opencode\\skills\\quote_pdf_render_skill\\out\\报价单-WK-demo-001-en.pdf",
        "status": "success"
      }
    ]
  }
}
```

---

## 12. 错误处理策略

## 12.1 缺少 `quote_document`

- 不允许继续渲染
- 直接报错

## 12.2 `weasyprint`、Chrome / Edge 与 `wkhtmltopdf` 都不可用

- 对应语言输出 `status = failed`
- 返回结构化错误信息

补充：若 `weasyprint` 不可用，Skill 会继续尝试 Chromium / Edge 与 `wkhtmltopdf`，只有三者都不可用时才判定失败。

## 12.3 HTML 渲染失败

- 返回错误摘要
- 不抛弃其他语言的渲染机会

## 12.4 文件未落盘

- 若渲染模块返回成功但目标文件不存在
- 输出 `failed`

---

## 13. 测试建议

至少应覆盖：

1. 标准 `QuoteDocument` sample 渲染
2. 双语输出成功
3. 真实 orchestrator 输出渲染
4. 缺失 `quote_document` 的失败路径
5. `weasyprint` 不可用时 Chromium / Edge 或 `wkhtmltopdf` 的回退路径
6. `weasyprint`、Chrome / Edge 与 `wkhtmltopdf` 都不可用时的失败路径

当前已提供：

- `examples/input.sample.json`
- `examples/output.sample.json`
- `validate_samples.py`

---

## 14. 与 orchestrator 的集成建议

本 Skill 适合作为 orchestrator 的可选最后一步。

建议策略：

- 默认不启用渲染
- 当输入中存在 `render_options.enabled = true` 或显式 `languages` 时启用
- 输出结果挂载到 orchestrator 的 `render_result`

这样既保留：

- 只输出 `quote_document` 的核心链路

又支持：

- 一步生成最终报价文件

---

## 15. 总结

`quote_pdf_render_skill` 的定位是：

> 对最终 `QuoteDocument` 进行模板渲染导出的后处理 Skill。

它不改变核心报价链路的职责边界，但把“正式文件导出”能力用结构化契约方式接入到了 Skill 体系和 orchestrator 中。

当前版本已经可用，并已成功接入 orchestrator，同时已经完成对 `quotation-pdf` 子项目运行依赖的解耦。
