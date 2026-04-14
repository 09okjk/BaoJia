---
name: quote_pdf_render_skill
description: 基于最终 quote_document 调用报价模板渲染器，生成 HTML/PDF 文件，并返回输出路径、渲染语言和后端结果。当用户提到报价单导出、PDF 报价渲染、中英文报价文件、HTML/PDF 输出时使用。
---

# quote_pdf_render_skill

## 何时使用此 Skill

在以下场景使用：

- 已经有最终 `quote_document`
- 需要输出正式报价单 HTML/PDF
- 需要一次生成中文、英文或双语报价文件
- 需要返回文件路径供后续下载、展示或归档

不要在以下场景使用：

- 还没有最终 `QuoteDocument`
- 还在做可报价判断、历史检索或定价计算
- 需要修改报价内容本身，而不是渲染输出

## 前提条件

- 必须存在 `quote_document`
- 输入输出统一使用 JSON 对象
- 本 Skill 是 `QuoteDocument JSON -> 报价模板文件` 的后处理渲染器
- 不负责重新定价、重建 `quotation_options` 或修改 `footer`

运行命令：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pdf_render_skill/run.py" --input ".opencode/skills/quote_pdf_render_skill/examples/input.sample.json"`

默认会执行输入和输出的 JSON Schema 校验。

如需跳过校验：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pdf_render_skill/run.py" --input ".opencode/skills/quote_pdf_render_skill/examples/input.sample.json" --skip-schema-validation`

## 输入

```json
{
  "quote_document": {},
  "render_options": {
    "languages": ["zh", "en"],
    "output_dir": ".opencode/skills/quote_pdf_render_skill/out"
  }
}
```

## 输出

```json
{
  "render_result": {
    "document_type": "quotation",
    "document_version": "1.1",
    "outputs": [
      {
        "language": "zh",
        "html_path": "",
        "pdf_path": ""
      }
    ]
  }
}
```

## 指令

1. 检查输入是否包含 `quote_document`，并确认其为 JSON 对象。
2. 校验 `quote_document` 是否满足最终契约。
3. 根据 `render_options.languages` 决定生成中文、英文或双语文件。
4. 调用现有 `quotation-pdf` 渲染逻辑生成 HTML/PDF。
5. 返回每种语言对应的输出路径和渲染状态。
6. 不要在输出里夹带模板内部中间结构。

## 输出要求

- 不得修改输入 `quote_document`
- 必须显式返回每个输出文件的 `language`、`html_path`、`pdf_path`
- 若某个 PDF 生成失败，必须结构化返回错误信息
- 允许双语输出，但每个语言结果必须分开记录

正式契约文件：

- 输入 Schema：`schemas/input.schema.json`
- 输出 Schema：`schemas/output.schema.json`

## 常见问题

### 这个 Skill 会重新计算金额吗？

不会。它只负责渲染现有 `quote_document`。

### 这个 Skill 会修改 QuoteDocument 内容吗？

不会。它只做展示层映射与文件输出。

### 这个 Skill 会同时生成中英文吗？

会。通过 `render_options.languages` 控制。

### 为什么控制台里中文路径可能显示乱码？

Windows 控制台可能对中文文件名显示不稳定，但只要 `render_result.outputs[*].status = success`，并且 JSON 中返回了路径，就应以 JSON 结果和实际文件存在性为准。
