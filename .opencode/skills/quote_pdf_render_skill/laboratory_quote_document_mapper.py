from __future__ import annotations

from typing import Any

from models import EngineeringPdfContext
from quote_document_mapper import QuoteDocumentMapper


class LaboratoryQuoteDocumentMapper(QuoteDocumentMapper):
    def to_engineering_context(self) -> EngineeringPdfContext:
        base = super().to_engineering_context()
        form_data = dict(base.form_data)
        form_data["description"] = form_data.get("descriptions", [])
        form_data.setdefault("vesselFlag", "")
        form_data.setdefault("vesselClass", "")
        form_data.setdefault("systemInfo", form_data.get("vesselType", ""))
        form_data.setdefault("makerModel", "")
        form_data.setdefault("paymentTerms", "")
        form_data.setdefault("preparedBy", "")
        form_data.setdefault("approvedBy", "")
        form_data.setdefault("inscribe", "")
        form_data.setdefault("testingItems", [])
        return base.model_copy(update={"form_data": form_data, "tax_rate": False})
