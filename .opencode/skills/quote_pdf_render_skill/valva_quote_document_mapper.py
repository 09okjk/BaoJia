from __future__ import annotations

from typing import Any

from models import EngineeringPdfContext
from quote_document_mapper import QuoteDocumentMapper


class ValvaQuoteDocumentMapper(QuoteDocumentMapper):
    def to_engineering_context(self) -> EngineeringPdfContext:
        base = super().to_engineering_context()
        quote_document = self._extract_quote_document(self._payload)
        form_data = dict(base.form_data)

        repair_items: list[dict[str, Any]] = []
        complete_valve_items: list[dict[str, Any]] = []
        total_price = ""

        quotation_options = quote_document.get("quotation_options", [])
        if isinstance(quotation_options, list):
            for option in quotation_options:
                if not isinstance(option, dict):
                    continue
                summary = option.get("summary")
                if isinstance(summary, dict):
                    total_price = self._summary_display(
                        summary, "total", base.currency_name
                    )
                sections = option.get("sections")
                if not isinstance(sections, list):
                    continue
                for section in sections:
                    if not isinstance(section, dict):
                        continue
                    groups = section.get("groups")
                    if not isinstance(groups, list):
                        continue
                    for group in groups:
                        if not isinstance(group, dict):
                            continue
                        title = self._display_text(str(group.get("title", "") or ""))
                        target = (
                            complete_valve_items
                            if "complete valve" in title.lower()
                            else repair_items
                        )
                        lines = group.get("lines")
                        if not isinstance(lines, list):
                            continue
                        for line in lines:
                            if not isinstance(line, dict):
                                continue
                            if str(line.get("line_type", "") or "") != "priced":
                                continue
                            target.append(
                                {
                                    "no": str(
                                        line.get("line_no", "")
                                        or line.get("item", "")
                                        or ""
                                    ),
                                    "model": title,
                                    "positionNo": _infer_position_no(
                                        str(line.get("description", "") or "")
                                    ),
                                    "qty": str(line.get("qty_display", "") or ""),
                                    "service": _infer_service_value(
                                        str(line.get("description", "") or "")
                                    ),
                                    "unitPrice": str(
                                        line.get("unit_price_display", "") or ""
                                    ),
                                    "discount": str(
                                        line.get("discount", {}).get("display", "")
                                        if isinstance(line.get("discount"), dict)
                                        else ""
                                    ),
                                    "total": str(line.get("amount_display", "") or ""),
                                    "fixedAppendFlag": False,
                                    "discountType": 1,
                                }
                            )

        header = quote_document.get("header", {})
        if not isinstance(header, dict):
            header = {}

        form_data.update(
            {
                "title": "Valve Quotation",
                "engineMakerType": _join_non_blank(
                    [header.get("vessel_type"), form_data.get("vesselType")]
                ),
                "builtYear": "",
                "buitYard": "",
                "drewBy": str(form_data.get("inquiryInitiator", "") or ""),
                "valveListReferedTo": str(form_data.get("youRefNo", "") or ""),
                "quotationForRepairKit": repair_items,
                "completeValve": complete_valve_items,
                "totalPrice": total_price,
            }
        )

        return base.model_copy(
            update={
                "form_data": form_data,
                "quotation_template": _infer_quotation_template(form_data),
            }
        )


def _infer_position_no(text: str) -> str:
    lowered = text.lower()
    marker = "position"
    if marker not in lowered:
        return ""
    start = lowered.find(marker)
    return text[start:].strip()


def _infer_service_value(text: str) -> int:
    lowered = text.lower()
    if "check" in lowered or "condition" in lowered:
        return 3
    if "repair" in lowered or "inspection" in lowered or "o/h" in lowered:
        return 2
    return 1


def _infer_quotation_template(form_data: dict[str, Any]) -> int:
    customer_name = str(form_data.get("customerName", "") or "").lower()
    if "mgs" in customer_name or "singapore" in customer_name:
        return 2
    return 1


def _join_non_blank(values: list[Any]) -> str:
    parts = [str(item).strip() for item in values if str(item).strip()]
    return " / ".join(parts)
