from __future__ import annotations

from models import EngineeringPdfContext
from quote_document_mapper import QuoteDocumentMapper


class ProductQuoteDocumentMapper(QuoteDocumentMapper):
    def to_engineering_context(self) -> EngineeringPdfContext:
        base = super().to_engineering_context()
        form_data = dict(base.form_data)
        form_data.setdefault("to", form_data.get("customerName", ""))
        form_data.setdefault("from", "WinKong Marine Engineering Co.，Ltd.")
        form_data.setdefault("tel", "")
        form_data.setdefault("paymentTerms", "")
        form_data.setdefault("paymentTermsForSpareParts", [])
        form_data.setdefault("inscribe", "")

        summary = form_data.get("summary") or [{}]
        if isinstance(summary, list) and summary:
            first = dict(summary[0]) if isinstance(summary[0], dict) else {}
            first.setdefault("productTaxRate", "")
            summary = [first]
        else:
            summary = [{"productTaxRate": ""}]
        form_data["summary"] = summary

        return base.model_copy(
            update={
                "form_data": form_data,
                "tax_rate": bool(summary[0].get("productTaxRate")),
            }
        )
