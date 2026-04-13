from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from py_pdf.application.generator import OutputFileNamer, QuotationPdfGenerator
from py_pdf.domain.models import EngineeringPdfContext
from py_pdf.infrastructure.quote_document import QuoteDocumentJsonDataSource
from py_pdf.infrastructure.quotation_response import QuotationResponseJsonDataSource


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据数据生成报价单 PDF。")
    parser.add_argument(
        "--data",
        type=Path,
        help="输入 JSON 文件路径，支持旧接口响应或 QuoteDocument",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        help="QuoteDocument schema 路径；未传时默认使用仓库内 .opencode/quote-document-v1.1.schema.json",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("out"),
        help="输出目录（默认 out）",
    )
    parser.add_argument(
        "--display-language",
        choices=["auto", "zh", "en"],
        default="auto",
        help="项目内容显示语言偏好（默认 auto）",
    )
    parser.add_argument(
        "--bilingual",
        action="store_true",
        help="同时输出中文和英文两份报价单",
    )
    return parser


def _demo_context() -> EngineeringPdfContext:
    return EngineeringPdfContext(
        quotation_type=1,
        quotation_template=1,
        display_discounts=1,
        tax_rate=False,
        currency_name="USD",
        currency_symbol="$",
        inquiry_no="DEMO-0001",
        form_data={
            "vesselName": "DEMO VESSEL",
            "date": date.today(),
            "imoNo": "1234567",
            "vesselType": "Bulk Carrier",
            "customerName": "Demo Customer",
            "servicePort": "Qingdao",
            "attention": "Mr. Zhang",
            "wkOfferNo": "WK-2026-0001",
            "youRefNo": "RFQ-001",
            "quotationValidity": "30 days",
            "poNo": "PO-0001",
            "inquiryInitiator": "WinKong PIC",
            "descriptions": [
                {
                    "index": 1,
                    "content": "Service A\nLine 2",
                    "price": 1200,
                    "unit": "set",
                    "qty": 1,
                    "discount": "-",
                    "amount": 1200,
                    "fixedAppendFlag": False,
                    "discountType": 0,
                }
            ],
            "summary": [
                {
                    "serviceCharge": 1200,
                    "sparePartsFee": 0,
                    "other": 0,
                    "total": 1200,
                }
            ],
        },
    )


def _default_schema_path() -> Path:
    return (
        Path(__file__).resolve().parents[3]
        / ".opencode"
        / "quote-document-v1.1.schema.json"
    )


def _load_json_root(path: Path) -> Mapping[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload: object = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _looks_like_quote_document(payload: Mapping[str, Any]) -> bool:
    candidate = payload.get("quote_document", payload)
    if not isinstance(candidate, dict):
        return False
    return candidate.get("document_type") == "quotation" and "header" in candidate


def _load_context(
    data_path: Path, schema_path: Path | None, display_language: str
) -> EngineeringPdfContext:
    payload = _load_json_root(data_path)

    if _looks_like_quote_document(payload):
        resolved_schema = schema_path or _default_schema_path()
        data_source = QuoteDocumentJsonDataSource(
            data_path,
            schema_path=resolved_schema,
            display_language=display_language,
        )
        return data_source.to_engineering_context()

    data_source = QuotationResponseJsonDataSource(data_path)
    return data_source.to_engineering_context()


def _apply_display_language(
    context: EngineeringPdfContext, display_language: str
) -> EngineeringPdfContext:
    return context.model_copy(update={"display_language": display_language})


def run(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    generator = QuotationPdfGenerator(out_dir=args.out_dir, namer=OutputFileNamer())

    contexts: list[EngineeringPdfContext] = []
    requested_languages = [args.display_language]
    if args.bilingual:
        requested_languages = ["zh", "en"]

    for language in requested_languages:
        if args.data and args.data.exists():
            context = _load_context(args.data, args.schema, language)
        else:
            context = _demo_context()
        contexts.append(_apply_display_language(context, language))

    for item in contexts:
        html_path, pdf_path = generator.generate(item)
        print(f"Rendered HTML: {html_path.resolve()}")
        print(f"Rendered PDF:  {pdf_path.resolve()}")
    return 0
