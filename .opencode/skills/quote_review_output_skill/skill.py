from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


TABLE_COLUMNS = [
    {"key": "item", "label": "Item"},
    {"key": "description", "label": "Description"},
    {"key": "unit_price", "label": "Unit Price"},
    {"key": "unit", "label": "Unit"},
    {"key": "qty", "label": "Q'ty"},
    {"key": "discount", "label": "Discount"},
    {"key": "amount", "label": "Amount"},
]


def build_quote_document(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_request = (
        payload.get("quote_request")
        if isinstance(payload.get("quote_request"), dict)
        else {}
    )
    feasibility_result = (
        payload.get("feasibility_result")
        if isinstance(payload.get("feasibility_result"), dict)
        else {}
    )
    historical_reference = (
        payload.get("historical_reference")
        if isinstance(payload.get("historical_reference"), dict)
        else {}
    )
    pricing_result = (
        payload.get("pricing_result")
        if isinstance(payload.get("pricing_result"), dict)
        else {}
    )

    quotation_options = (
        pricing_result.get("quotation_options")
        if isinstance(pricing_result.get("quotation_options"), list)
        else []
    )
    if not quotation_options:
        return {"quote_document": {}}

    header = _build_header(quote_request)
    footer = _build_footer(quote_request, quotation_options)
    review_result = _build_review_result(feasibility_result)
    trace = _build_trace(historical_reference, pricing_result)

    return {
        "quote_document": {
            "document_type": "quotation",
            "document_version": "1.1",
            "header": header,
            "table_schema": {"columns": TABLE_COLUMNS},
            "quotation_options": quotation_options,
            "footer": footer,
            "review_result": review_result,
            "trace": trace,
        }
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


def _build_header(quote_request: dict[str, Any]) -> dict[str, str]:
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )
    commercial_context = (
        quote_request.get("commercial_context")
        if isinstance(quote_request.get("commercial_context"), dict)
        else {}
    )

    service_date = str(header_context.get("service_date") or "")
    if not service_date:
        service_date = date.today().isoformat()

    return {
        "currency": _string_or_blank(
            header_context.get("currency")
            or commercial_context.get("preferred_currency")
        ),
        "vessel_name": _string_or_blank(header_context.get("vessel_name")),
        "date": service_date,
        "imo_no": _string_or_blank(header_context.get("imo_no")),
        "vessel_type": _string_or_blank(header_context.get("vessel_type")),
        "customer_name": _string_or_blank(header_context.get("customer_name")),
        "service_port": _string_or_blank(header_context.get("service_port")),
        "attention": _string_or_blank(header_context.get("attention")),
        "wk_offer_no": _build_offer_no(quote_request),
        "your_ref_no": _string_or_blank(header_context.get("customer_ref_no")),
        "quotation_validity": "30 days",
        "po_no": "",
        "pic_of_winkong": "Winkong",
    }


def _build_offer_no(quote_request: dict[str, Any]) -> str:
    source_refs = (
        quote_request.get("source_refs")
        if isinstance(quote_request.get("source_refs"), dict)
        else {}
    )
    assessment_id = _string_or_blank(source_refs.get("assessment_report_id"))
    if assessment_id:
        return f"WK-{assessment_id}"
    request_meta = (
        quote_request.get("request_meta")
        if isinstance(quote_request.get("request_meta"), dict)
        else {}
    )
    request_id = _string_or_blank(request_meta.get("request_id"))
    return f"WK-{request_id}" if request_id else "WK-DRAFT"


def _build_footer(
    quote_request: dict[str, Any], quotation_options: list[Any]
) -> dict[str, Any]:
    summary = (
        quotation_options[0]["summary"] if quotation_options else _empty_summary("USD")
    )
    remarks = _build_footer_remarks(quote_request, quotation_options)
    return {
        "summary": summary,
        "remark": {
            "title": "Remark",
            "items": remarks,
        },
        "service_payment_terms": {
            "title": "Service Payment Terms",
            "content": "Payment within 30 days upon invoice date.",
        },
    }


def _build_footer_remarks(
    quote_request: dict[str, Any], quotation_options: list[Any]
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        for remark in option.get("remarks", []):
            if not isinstance(remark, dict):
                continue
            remark_type = _string_or_blank(remark.get("type")) or "commercial"
            text = _string_or_blank(remark.get("text"))
            if not text:
                continue
            key = (remark_type, text)
            if key in seen:
                continue
            seen.add(key)
            items.append({"type": remark_type, "text": text})

    commercial_context = (
        quote_request.get("commercial_context")
        if isinstance(quote_request.get("commercial_context"), dict)
        else {}
    )
    special_terms = (
        commercial_context.get("special_terms")
        if isinstance(commercial_context.get("special_terms"), list)
        else []
    )
    for term in special_terms:
        text = _string_or_blank(term)
        if not text:
            continue
        key = ("commercial", text)
        if key in seen:
            continue
        seen.add(key)
        items.append({"type": "commercial", "text": text})

    if not items:
        items.append(
            {
                "type": "commercial",
                "text": "Quoted scope is subject to final onboard condition.",
            }
        )
    return items


def _build_review_result(feasibility_result: dict[str, Any]) -> dict[str, Any]:
    review_flags = (
        feasibility_result.get("review_flags")
        if isinstance(feasibility_result.get("review_flags"), list)
        else []
    )
    missing_fields = (
        feasibility_result.get("missing_fields")
        if isinstance(feasibility_result.get("missing_fields"), list)
        else []
    )

    review_flag_texts = []
    risk_flag_texts = []
    for flag in review_flags:
        if isinstance(flag, dict):
            message = _string_or_blank(flag.get("message"))
            severity = _string_or_blank(flag.get("severity"))
            if message:
                review_flag_texts.append(message)
                if severity in {"high", "medium"}:
                    risk_flag_texts.append(message)

    for item in missing_fields:
        if isinstance(item, dict) and _string_or_blank(item.get("severity")) == "high":
            reason = _string_or_blank(item.get("reason"))
            if reason:
                risk_flag_texts.append(reason)

    approval_level = "standard"
    if any(
        _string_or_blank(item.get("severity")) == "high"
        for item in missing_fields
        if isinstance(item, dict)
    ):
        approval_level = "manager"

    return {
        "review_flags": _dedupe_strings(review_flag_texts),
        "risk_flags": _dedupe_strings(risk_flag_texts),
        "approval_level": approval_level,
    }


def _build_trace(
    historical_reference: dict[str, Any], pricing_result: dict[str, Any]
) -> dict[str, Any]:
    matches = (
        historical_reference.get("matches")
        if isinstance(historical_reference.get("matches"), list)
        else []
    )
    historical_references = []
    for match in matches:
        if not isinstance(match, dict):
            continue
        historical_references.append(
            {
                "quote_id": _string_or_blank(match.get("quote_id")),
                "similarity": float(match.get("similarity", 0.0) or 0.0),
                "reason": _string_or_blank(match.get("reason")),
            }
        )

    pricing_basis = []
    quotation_options = (
        pricing_result.get("quotation_options")
        if isinstance(pricing_result.get("quotation_options"), list)
        else []
    )
    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        for section in option.get("sections", []):
            if not isinstance(section, dict):
                continue
            for group in section.get("groups", []):
                if not isinstance(group, dict):
                    continue
                for line in group.get("lines", []):
                    if not isinstance(line, dict):
                        continue
                    basis = _string_or_blank(line.get("basis"))
                    if basis:
                        pricing_basis.append(basis)

    return {
        "historical_references": historical_references,
        "pricing_basis": _dedupe_strings(pricing_basis),
        "rule_versions": ["quote_pricing_skill:v1", "quote_review_output_skill:v1"],
    }


def _empty_summary(currency: str) -> dict[str, Any]:
    return {
        "service_charge": _summary_value(
            None, "Pending", currency, "pending", "status"
        ),
        "spare_parts_fee": _summary_value(
            None, "Pending", currency, "pending", "status"
        ),
        "other": _summary_value(0.0, "0.00", currency, "chargeable", "amount"),
        "total": _summary_value(None, "Pending", currency, "pending", "status"),
    }


def _summary_value(
    amount: float | None, display: str, currency: str, status: str, value_type: str
) -> dict[str, Any]:
    return {
        "value_type": value_type,
        "amount": amount,
        "display": display,
        "currency": currency,
        "status": status,
    }


def _string_or_blank(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result
