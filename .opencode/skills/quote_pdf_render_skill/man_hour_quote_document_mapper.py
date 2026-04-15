from __future__ import annotations

from typing import Any

from models import EngineeringPdfContext
from quote_document_mapper import QuoteDocumentMapper


class ManHourQuoteDocumentMapper(QuoteDocumentMapper):
    def to_engineering_context(self) -> EngineeringPdfContext:
        base = super().to_engineering_context()
        form_data = dict(base.form_data)
        descriptions = []
        for item in form_data.get("descriptions", []):
            if not isinstance(item, dict):
                continue
            new_item = dict(item)
            if "mergeFlag" not in new_item:
                new_item["mergeFlag"] = _default_merge_flag(new_item)
            if "mergeContent" not in new_item:
                new_item["mergeContent"] = ""
            descriptions.append(new_item)

        form_data["descriptions"] = descriptions
        form_data.setdefault("serviceTaxRate", "")
        form_data.setdefault("productTaxRate", "")
        form_data.setdefault("paymentTermsForSpareParts", [])
        form_data.setdefault("inscribe", "")

        return base.model_copy(
            update={
                "form_data": form_data,
                "quotation_template": _infer_quotation_template(base.form_data),
            }
        )


def _default_merge_flag(item: dict[str, Any]) -> int:
    has_pricing_fields = any(
        str(item.get(key, "") or "").strip()
        for key in ["price", "unit", "qty", "discount", "amount"]
    )
    return 0 if has_pricing_fields else 1


def _infer_quotation_template(form_data: dict[str, Any]) -> int:
    inquiry_initiator = str(form_data.get("inquiryInitiator", "") or "").lower()
    if "mgs" in inquiry_initiator or "singapore" in inquiry_initiator:
        return 2
    return 1
