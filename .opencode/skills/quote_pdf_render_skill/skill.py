from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from digital_product_quote_document_mapper import DigitalProductQuoteDocumentMapper
from digital_product_renderer import render_html as render_digital_product_html
from html_renderer import render_html
from laboratory_quote_document_mapper import LaboratoryQuoteDocumentMapper
from laboratory_renderer import render_html as render_laboratory_html
from man_hour_quote_document_mapper import ManHourQuoteDocumentMapper
from man_hour_renderer import render_html as render_man_hour_html
from pdf_renderer import render_pdf
from product_quote_document_mapper import ProductQuoteDocumentMapper
from product_renderer import render_html as render_product_html
from quote_document_mapper import QuoteDocumentMapper
from supercharger_quote_document_mapper import SuperchargerQuoteDocumentMapper
from supercharger_renderer import render_html as render_supercharger_html
from valva_quote_document_mapper import ValvaQuoteDocumentMapper
from valva_renderer import render_html as render_valva_html

ROOT_DIR = Path(__file__).resolve().parents[3]
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
QUOTE_DOCUMENT_SCHEMA_PATH = ROOT_DIR / ".opencode" / "quote-document-v1.1.schema.json"
SUPPORTED_TEMPLATE_TYPES = {
    "engineering-service",
    "digital-product",
    "laboratory",
    "man-hour",
    "product",
    "supercharger",
    "valva",
}
ALL_TEMPLATE_TYPES = {
    "engineering-service",
    "digital-product",
    "laboratory",
    "man-hour",
    "product",
    "supercharger",
    "valva",
}


def load_json(path: str | Path) -> dict[str, Any]:
    content = Path(path).read_text(encoding="utf-8")
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be an object.")
    return data


def dump_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_render_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_document = _extract_quote_document(payload)
    if not isinstance(quote_document, dict):
        raise ValueError("quote_document is required and must be an object.")

    render_options = payload.get("render_options")
    if not isinstance(render_options, dict):
        render_options = {}

    languages = render_options.get("languages")
    if not isinstance(languages, list) or not languages:
        languages = ["zh"]
    normalized_languages = []
    for language in languages:
        if language in {"zh", "en"} and language not in normalized_languages:
            normalized_languages.append(language)
    if not normalized_languages:
        normalized_languages = ["zh"]

    output_dir_raw = render_options.get("output_dir")
    output_dir = (
        ROOT_DIR / str(output_dir_raw)
        if isinstance(output_dir_raw, str) and output_dir_raw.strip()
        else ROOT_DIR / ".opencode" / "out" / "quotes"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    template_type = render_options.get("template_type")
    if not isinstance(template_type, str) or template_type not in ALL_TEMPLATE_TYPES:
        template_type = "engineering-service"

    outputs = []
    for language in normalized_languages:
        outputs.append(
            _render_one_language(
                quote_document=quote_document,
                language=language,
                output_dir=output_dir,
                template_type=template_type,
            )
        )

    return {
        "render_result": {
            "document_type": str(quote_document.get("document_type") or "quotation"),
            "document_version": str(quote_document.get("document_version") or "1.1"),
            "outputs": outputs,
        }
    }


def _extract_quote_document(payload: dict[str, Any]) -> dict[str, Any] | None:
    candidate = payload.get("quote_document")
    if isinstance(candidate, dict):
        return candidate

    review_output = payload.get("review_output")
    if isinstance(review_output, dict):
        candidate = review_output.get("quote_document")
        if isinstance(candidate, dict):
            return candidate

    return None


def _render_one_language(
    quote_document: dict[str, Any],
    language: str,
    output_dir: Path,
    template_type: str,
) -> dict[str, Any]:
    html_path, pdf_path = _expected_output_paths(quote_document, language, output_dir)
    try:
        if template_type not in SUPPORTED_TEMPLATE_TYPES:
            raise ValueError(
                f"template_type '{template_type}' is recognized but not implemented in quote_pdf_render_skill yet"
            )
        mapper = _build_mapper(template_type, quote_document, language)
        context = mapper.to_engineering_context().model_copy(
            update={"display_language": language}
        )
        html = _render_template_html(template_type, context)
        html_path.write_text(html, encoding="utf-8")
        render_pdf(
            html=html,
            output_pdf_path=pdf_path,
            base_url=str(ASSETS_DIR.resolve()),
            prefer="weasyprint",
        )
        return {
            "language": language,
            "html_path": str(html_path.resolve()),
            "pdf_path": str(pdf_path.resolve()),
            "status": "success",
        }
    except Exception as exc:
        return {
            "language": language,
            "html_path": "",
            "pdf_path": "",
            "status": "failed",
            "error": str(exc),
        }


def _expected_output_paths(
    quote_document: dict[str, Any], language: str, output_dir: Path
) -> tuple[Path, Path]:
    header = quote_document.get("header")
    wk_offer_no = ""
    if isinstance(header, dict):
        wk_offer_no = str(header.get("wk_offer_no", "") or "").strip()
    safe_offer_no = wk_offer_no.replace("/", "-").replace("\\", "-").replace(":", "：")
    base_name = (
        f"报价单-{safe_offer_no}-{language}"
        if safe_offer_no
        else f"quotation-{language}"
    )
    return output_dir / f"{base_name}.html", output_dir / f"{base_name}.pdf"


def _build_mapper(
    template_type: str, quote_document: dict[str, Any], language: str
) -> QuoteDocumentMapper:
    mapper_cls = {
        "engineering-service": QuoteDocumentMapper,
        "digital-product": DigitalProductQuoteDocumentMapper,
        "laboratory": LaboratoryQuoteDocumentMapper,
        "man-hour": ManHourQuoteDocumentMapper,
        "product": ProductQuoteDocumentMapper,
        "supercharger": SuperchargerQuoteDocumentMapper,
        "valva": ValvaQuoteDocumentMapper,
    }.get(template_type)
    if mapper_cls is None:
        raise ValueError(f"Unsupported template mapper: {template_type}")
    return mapper_cls(
        {"quote_document": quote_document},
        schema_path=QUOTE_DOCUMENT_SCHEMA_PATH,
        display_language=language,
    )


def _render_template_html(template_type: str, context: Any) -> str:
    renderer = {
        "engineering-service": render_html,
        "digital-product": render_digital_product_html,
        "laboratory": render_laboratory_html,
        "man-hour": render_man_hour_html,
        "product": render_product_html,
        "supercharger": render_supercharger_html,
        "valva": render_valva_html,
    }.get(template_type)
    if renderer is None:
        raise ValueError(f"Unsupported template renderer: {template_type}")
    return renderer(context, assets_dir=ASSETS_DIR)
