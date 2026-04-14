from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EngineeringPdfContext:
    form_data: dict[str, Any]
    quotation_template: int
    display_discounts: int
    tax_rate: bool
    currency_name: str
    currency_symbol: str = ""
    quotation_type: int = 1
    inquiry_no: str = ""
    display_language: str = "auto"

    def model_copy(self, *, update: dict[str, Any]) -> "EngineeringPdfContext":
        data = {
            "form_data": self.form_data,
            "quotation_template": self.quotation_template,
            "display_discounts": self.display_discounts,
            "tax_rate": self.tax_rate,
            "currency_name": self.currency_name,
            "currency_symbol": self.currency_symbol,
            "quotation_type": self.quotation_type,
            "inquiry_no": self.inquiry_no,
            "display_language": self.display_language,
        }
        data.update(update)
        return EngineeringPdfContext(**data)


@dataclass(frozen=True)
class QuoteDocumentPdfContext:
    quote_document: dict[str, Any]
    source_name: str = "quote_document"

    @property
    def inquiry_no(self) -> str:
        header = self.quote_document.get("header")
        if isinstance(header, dict):
            return str(header.get("wk_offer_no", "") or "")
        return ""
