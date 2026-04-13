# py-pdf

## 功能

- 使用 Jinja2 先生成 HTML 报价单
- 再将 HTML 转换为 PDF
- 支持两类输入：
  - 旧接口响应 JSON，例如 `reponse.json`
  - 智能报价流程最终输出的 `QuoteDocument v1.1`

PDF 后端优先级：

1. WeasyPrint
2. Chrome / Edge headless print-to-pdf
3. wkhtmltopdf

## 运行

```bash
uv sync
uv run python src/main.py --data reponse.json
```

渲染 `QuoteDocument`：

```bash
uv run python src/main.py --data "..\.opencode\quote-document-v1.1-example.json"
uv run python src/main.py --data "..\.opencode\skills\quote_review_output_skill\examples\output.sample.json"
```

如需自定义 schema：

```bash
uv run python src/main.py --data your-quote.json --schema your-schema.json
```

输出文件位于 `out/`。
