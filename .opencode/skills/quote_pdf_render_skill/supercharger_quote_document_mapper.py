from __future__ import annotations

from typing import Any

from models import EngineeringPdfContext
from quote_document_mapper import QuoteDocumentMapper


class SuperchargerQuoteDocumentMapper(QuoteDocumentMapper):
    def to_engineering_context(self) -> EngineeringPdfContext:
        base = super().to_engineering_context()
        form_data = dict(base.form_data)

        descriptions = []
        work_scope: list[str] = []
        total_amount = ""
        quotation_options = self._extract_quote_document(self._payload).get(
            "quotation_options", []
        )
        if isinstance(quotation_options, list):
            for option in quotation_options:
                if not isinstance(option, dict):
                    continue
                summary = option.get("summary")
                if isinstance(summary, dict):
                    total_amount = self._summary_display(
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
                        group_title = self._display_text(
                            str(group.get("title", "") or "")
                        )
                        lines = group.get("lines")
                        if not isinstance(lines, list):
                            continue
                        for line in lines:
                            if not isinstance(line, dict):
                                continue
                            description = self._customer_facing_description(
                                line, group_title=group_title
                            )
                            if description and description not in work_scope:
                                work_scope.append(description)
                            if str(line.get("line_type", "") or "") != "priced":
                                continue
                            descriptions.append(
                                {
                                    "itemAndWorkScope": group_title,
                                    "index": str(
                                        line.get("line_no", "")
                                        or line.get("item", "")
                                        or ""
                                    ),
                                    "content": description,
                                    "price": str(
                                        line.get("unit_price_display", "") or ""
                                    ),
                                    "qty": str(line.get("qty_display", "") or ""),
                                    "unit": str(line.get("unit", "") or ""),
                                    "discount": str(
                                        line.get("discount", {}).get("display", "")
                                        if isinstance(line.get("discount"), dict)
                                        else ""
                                    ),
                                    "amount": str(line.get("amount_display", "") or ""),
                                    "fixedAppendFlag": False,
                                    "discountType": 1,
                                }
                            )

        form_data["descriptions"] = descriptions
        form_data.setdefault(
            "turbochargerType", _infer_turbocharger_type(work_scope, form_data)
        )
        form_data.setdefault("hours", "")
        form_data.setdefault(
            "runningHours", _infer_running_hours(form_data, work_scope)
        )
        form_data["workScope"] = work_scope
        form_data["totalAmount"] = total_amount
        form_data.setdefault("serviceTaxRate", "")
        form_data.setdefault("productTaxRate", "")
        form_data.setdefault("finalAmount", "")
        form_data.setdefault("logo", 0)

        return base.model_copy(
            update={
                "form_data": form_data,
                "quotation_template": _infer_quotation_template(form_data),
            }
        )


def _infer_turbocharger_type(work_scope: list[str], form_data: dict[str, Any]) -> str:
    vessel_type = str(form_data.get("vesselType", "") or "")
    for text in work_scope:
        lowered = text.lower()
        for token in ["vtr", "tca", "met", "nr"]:
            if token in lowered:
                return token.upper()
    return vessel_type


def _infer_running_hours(form_data: dict[str, Any], work_scope: list[str]) -> str:
    for text in work_scope + [str(form_data.get("remarks", "") or "")]:
        lowered = text.lower()
        if "64k" in lowered:
            return "64000"
        if "running hours" in lowered:
            return "running_hours"
    return ""


def _infer_quotation_template(form_data: dict[str, Any]) -> int:
    customer_name = str(form_data.get("customerName", "") or "").lower()
    if "mitsubishi" in customer_name or "mgs" in customer_name:
        return 2
    return 1
