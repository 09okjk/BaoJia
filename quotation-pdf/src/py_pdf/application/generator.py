from __future__ import annotations

from pathlib import Path

from engineering_pdf_renderer import render_engineering_pdf
from pdf_renderer import PdfRenderError, render_pdf
from py_pdf.domain.models import EngineeringPdfContext, QuoteDocumentPdfContext


class OutputFileNamer:
    def __init__(self, default_base: str = "engineering_pdf") -> None:
        self._default_base = default_base

    def base_name(
        self, context: EngineeringPdfContext | QuoteDocumentPdfContext
    ) -> str:
        inquiry_no = (context.inquiry_no or "").strip()
        if not inquiry_no:
            return self._default_base
        safe = self._sanitize(inquiry_no)
        return f"报价单-{safe}"

    def base_name_with_language(
        self, context: EngineeringPdfContext | QuoteDocumentPdfContext
    ) -> str:
        base = self.base_name(context)
        language = getattr(context, "display_language", "auto") or "auto"
        if language == "auto":
            return base
        return f"{base}-{language}"

    def _sanitize(self, text: str) -> str:
        replaced = text.replace("/", "-").replace("\\", "-").replace("\n", " ").strip()
        replaced = replaced.replace(":", "：")
        return replaced


class QuotationPdfGenerator:
    def __init__(self, *, out_dir: Path, namer: OutputFileNamer | None = None) -> None:
        self._out_dir = out_dir
        self._namer = namer or OutputFileNamer()

    def generate(
        self, context: EngineeringPdfContext | QuoteDocumentPdfContext
    ) -> tuple[Path, Path]:
        if isinstance(context, QuoteDocumentPdfContext):
            raise RuntimeError(
                "QuoteDocumentPdfContext should be converted to EngineeringPdfContext before rendering."
            )

        html = render_engineering_pdf(context)

        base = self._namer.base_name_with_language(context)
        self._out_dir.mkdir(parents=True, exist_ok=True)
        html_path = self._out_dir / f"{base}.html"
        pdf_path = self._out_dir / f"{base}.pdf"

        html_path.write_text(html, encoding="utf-8")

        try:
            render_pdf(
                html=html,
                output_pdf_path=pdf_path,
                base_url=str(self._out_dir.resolve()),
            )
        except PdfRenderError as e:
            raise RuntimeError(
                f"PDF 生成失败：{e}\n建议：先执行 `uv sync` 安装依赖，再用 `uv run python src/main.py` 运行。"
            ) from e

        return html_path, pdf_path
