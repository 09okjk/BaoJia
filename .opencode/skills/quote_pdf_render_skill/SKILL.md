---
name: quote-pdf-render-skill
slug: quote-pdf-render-skill
version: 1.0.0
author: "BaoJia Team"
description: 基于最终 quote_document 调用报价模板渲染器，生成 HTML/PDF 文件，并返回输出路径、渲染语言和后端结果。当用户提到报价单导出、PDF 报价渲染、中英文报价文件、HTML/PDF 输出时使用。
metadata:
  clawdbot:
    requires:
      bins: ["python"]
    os: ["win32"]
---

# quote-pdf-render-skill

## When to Use（何时使用）

- 已经有最终 `quote_document`
- 需要输出正式报价单 HTML/PDF
- 需要一次生成中文、英文或双语报价文件

## When NOT to Use（何时不用）

- 还没有最终 `QuoteDocument`
- 还在做可报价判断、历史检索或定价计算
- 需要修改报价内容本身，而不是渲染输出

## Quick Start（快速开始）

运行命令：`python scripts/main.py --input samples/sample-input.json --output out/sample-output.json`

如需跳过校验：`python scripts/main.py --input samples/sample-input.json --skip-schema-validation`

最小输入骨架：

```json
{
  "quote_document": {},
  "render_options": {
    "languages": ["zh", "en"],
    "output_dir": ".opencode/out/quotes"
  }
}
```

最小输出骨架：

```json
{
  "render_result": {
    "document_type": "quotation",
    "document_version": "1.1",
    "outputs": [
      {
        "language": "zh",
        "html_path": "",
        "pdf_path": "",
        "status": "success"
      }
    ]
  }
}
```

## Core Behavior（核心行为）

- 只负责渲染，不修改报价内容
- 根据 `template_type` 做模板分发并生成 HTML/PDF
- 必须按语言分别返回 `html_path`、`pdf_path`、`status`
- recognized but unimplemented 的模板必须显式报错

## Deep Dive（深入资料）

- 完整样例：`samples/sample-input.json`、`samples/sample-output.json`
- 正式 Schema：`references/quote-pdf-render-input.schema.json`、`references/quote-pdf-render-output.schema.json`
- 模板实现请查看 skill 目录下各 mapper / renderer 文件

## Setup（安装配置）

- 当前仓库使用：`& ".opencode/.venv/Scripts/python.exe" ".opencode/skills/quote_pdf_render_skill/scripts/main.py" --input ".opencode/skills/quote_pdf_render_skill/samples/sample-input.json"`
- 默认输出目录：`.opencode/out/quotes`

## Options（选项说明）

- `--input`：输入 JSON 路径，必需
- `--output`：输出 JSON 路径，可选
- `--skip-schema-validation`：跳过 schema 校验，可选

## Core Rules（核心规则）

- 模板分发必须按 `template_type` 隔离
- 不得修改输入 `quote_document`
- 双语输出必须分开记录结果

## Security & Privacy（安全说明）

- 当前渲染在本地完成
- 输出文件路径可能包含报价编号与客户相关信息，归档和共享时需控制访问范围

## Related Skills（相关技能）

- `quote-template-select-skill`
- `quote-review-output-skill`

## Feedback（反馈）

- 新增模板时同步更新 mapper、renderer、示例输入与分发注册表
