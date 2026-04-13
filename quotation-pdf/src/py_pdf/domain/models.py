from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class EngineeringPdfContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    form_data: dict[str, Any]
    quotation_template: int
    display_discounts: int
    tax_rate: bool
    currency_name: str
    currency_symbol: str = ""
    quotation_type: int = 1
    inquiry_no: str = ""
    display_language: str = "auto"


class QuoteDocumentPdfContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    quote_document: dict[str, Any]
    source_name: str = "quote_document"

    @property
    def inquiry_no(self) -> str:
        header = self.quote_document.get("header")
        if isinstance(header, dict):
            return str(header.get("wk_offer_no", "") or "")
        return ""
