from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TABLE_COLUMNS = [
    {"key": "item", "label": "Item"},
    {"key": "description", "label": "Description"},
    {"key": "unit_price", "label": "Unit Price"},
    {"key": "unit", "label": "Unit"},
    {"key": "qty", "label": "Qty"},
    {"key": "discount", "label": "Discount"},
    {"key": "amount", "label": "Amount"},
]


def build_pricing_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_request = payload.get("quote_request")
    feasibility_result = payload.get("feasibility_result")
    historical_reference = payload.get("historical_reference") or {}
    pricing_rules = payload.get("pricing_rules") or {}

    if not isinstance(quote_request, dict) or not isinstance(feasibility_result, dict):
        return {"quotation_options": []}

    currency = _pick_currency(quote_request, pricing_rules, historical_reference)
    option = _build_option(quote_request, feasibility_result, pricing_rules, currency)
    if option is None:
        return {"quotation_options": []}
    return {"quotation_options": [option]}


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


def _build_option(
    quote_request: dict[str, Any],
    feasibility_result: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
) -> dict[str, Any] | None:
    quotable_items = (
        feasibility_result.get("quotable_items")
        if isinstance(feasibility_result.get("quotable_items"), list)
        else []
    )
    tbc_items = (
        feasibility_result.get("tbc_items")
        if isinstance(feasibility_result.get("tbc_items"), list)
        else []
    )
    exclusions = (
        feasibility_result.get("exclusions")
        if isinstance(feasibility_result.get("exclusions"), list)
        else []
    )

    sections = []
    sections.extend(
        _build_sections_for_items(
            quotable_items, quote_request, pricing_rules, currency, decision="quotable"
        )
    )
    sections.extend(
        _build_sections_for_items(
            tbc_items, quote_request, pricing_rules, currency, decision="tbc"
        )
    )
    sections.extend(
        _build_sections_for_items(
            exclusions, quote_request, pricing_rules, currency, decision="excluded"
        )
    )

    if not sections:
        return None

    return {
        "option_id": "option-1",
        "title": "Option 1",
        "sections": sections,
        "summary": _build_summary(sections, currency),
        "remarks": _build_option_remarks(pricing_rules),
    }


def _build_sections_for_items(
    items: list[Any],
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "service": [],
        "spare_parts": [],
        "other": [],
    }
    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = (
            item.get("item_type") if item.get("item_type") in grouped else "other"
        )
        grouped[item_type].append(item)

    sections = []
    for section_type, section_items in grouped.items():
        if not section_items:
            continue
        groups = []
        for index, item in enumerate(section_items, start=1):
            groups.append(
                _build_group(
                    section_type,
                    item,
                    index,
                    quote_request,
                    pricing_rules,
                    currency,
                    decision,
                )
            )
        sections.append(
            {
                "section_id": f"section-{section_type}",
                "section_type": section_type,
                "title": _section_title(section_type),
                "groups": groups,
            }
        )
    return sections


def _build_group(
    section_type: str,
    item: dict[str, Any],
    index: int,
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
) -> dict[str, Any]:
    item_id = str(item.get("item_id") or f"{section_type}-{index}")
    title = str(item.get("title") or "")
    description = str(item.get("reason") or title)
    line = _build_line(
        section_type, item, quote_request, pricing_rules, currency, decision, index
    )
    return {
        "group_id": f"group-{item_id}",
        "group_no": str(index),
        "title": title,
        "description": description,
        "lines": [line],
    }


def _build_line(
    section_type: str,
    item: dict[str, Any],
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
    index: int,
) -> dict[str, Any]:
    item_id = str(item.get("item_id") or f"line-{index}")
    title = str(item.get("title") or "")
    amount, line_type, pricing_mode, status, amount_display = _price_line(
        item, pricing_rules, currency, decision
    )
    unit_price = amount if amount is not None and pricing_mode == "lump_sum" else None
    unit_price_display = _format_amount(unit_price) if unit_price is not None else ""
    qty = (
        1 if amount is not None and pricing_mode in {"lump_sum", "unit_price"} else None
    )
    qty_display = "1" if qty is not None else ""
    return {
        "line_id": f"line-{item_id}",
        "item": str(index),
        "line_no": str(index),
        "line_type": line_type,
        "description": title,
        "pricing_mode": pricing_mode,
        "unit_price": unit_price,
        "unit_price_display": unit_price_display,
        "unit": "LS" if pricing_mode in {"lump_sum", "pending", "text_only"} else "",
        "qty": qty,
        "qty_display": qty_display,
        "discount": None,
        "amount": amount,
        "amount_display": amount_display,
        "currency": currency,
        "status": status,
        "basis": _basis_text(item, pricing_rules),
        "conditions": _conditions_for(item, decision),
        "notes": _notes_for(item, quote_request),
    }


def _price_line(
    item: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
) -> tuple[float | None, str, str, str, str]:
    item_id = str(item.get("item_id") or "")
    item_type = str(item.get("item_type") or "other")
    suggested_status = str(item.get("suggested_status") or "")

    if decision == "tbc" or suggested_status == "pending":
        return None, "pending", "pending", "pending", "Pending"
    if suggested_status == "by_owner":
        return None, "note", "text_only", "by_owner", "By owner"
    if suggested_status == "excluded" or decision == "excluded":
        return None, "note", "text_only", "excluded", "Excluded"
    if suggested_status == "if_needed":
        return None, "optional", "conditional", "if_needed", "If needed"
    if suggested_status == "extra":
        return None, "extra", "text_only", "extra", "Extra"
    if suggested_status == "as_actual":
        return None, "conditional", "rate_as_actual", "as_actual", "As actual"

    lump_sum_overrides = (
        pricing_rules.get("lump_sum_overrides")
        if isinstance(pricing_rules.get("lump_sum_overrides"), dict)
        else {}
    )
    service_rates = (
        pricing_rules.get("service_rates")
        if isinstance(pricing_rules.get("service_rates"), dict)
        else {}
    )

    amount = lump_sum_overrides.get(item_id)
    if not isinstance(amount, (int, float)):
        amount = service_rates.get(item_type)
    if not isinstance(amount, (int, float)):
        return None, "pending", "pending", "pending", "Pending"

    numeric_amount = float(amount)
    return (
        numeric_amount,
        "priced",
        "lump_sum",
        "chargeable",
        _format_amount(numeric_amount),
    )


def _build_summary(sections: list[dict[str, Any]], currency: str) -> dict[str, Any]:
    section_totals = {"service": 0.0, "spare_parts": 0.0, "other": 0.0}
    section_pending = {"service": False, "spare_parts": False, "other": False}

    for section in sections:
        section_type = section["section_type"]
        for group in section["groups"]:
            for line in group["lines"]:
                if line["status"] == "chargeable" and isinstance(
                    line["amount"], (int, float)
                ):
                    section_totals[section_type] += float(line["amount"])
                elif line["status"] != "excluded":
                    section_pending[section_type] = True

    service_charge = _summary_value(
        section_totals["service"], currency, section_pending["service"]
    )
    spare_parts_fee = _summary_value(
        section_totals["spare_parts"], currency, section_pending["spare_parts"]
    )
    other = _summary_value(section_totals["other"], currency, section_pending["other"])

    if any(section_pending.values()):
        total = {
            "value_type": "status",
            "amount": None,
            "display": "Pending",
            "currency": currency,
            "status": "pending",
        }
    else:
        total_amount = (
            section_totals["service"]
            + section_totals["spare_parts"]
            + section_totals["other"]
        )
        total = {
            "value_type": "amount",
            "amount": total_amount,
            "display": _format_amount(total_amount),
            "currency": currency,
            "status": "chargeable",
        }

    return {
        "service_charge": service_charge,
        "spare_parts_fee": spare_parts_fee,
        "other": other,
        "total": total,
    }


def _summary_value(amount: float, currency: str, pending: bool) -> dict[str, Any]:
    if pending:
        return {
            "value_type": "status",
            "amount": None,
            "display": "Pending",
            "currency": currency,
            "status": "pending",
        }
    return {
        "value_type": "amount",
        "amount": amount,
        "display": _format_amount(amount),
        "currency": currency,
        "status": "chargeable",
    }


def _build_option_remarks(pricing_rules: dict[str, Any]) -> list[dict[str, Any]]:
    remark_hints = (
        pricing_rules.get("remark_hints")
        if isinstance(pricing_rules.get("remark_hints"), list)
        else []
    )
    remarks = []
    for text in remark_hints:
        cleaned = str(text).strip()
        if not cleaned:
            continue
        remarks.append({"type": "commercial", "text": cleaned})
    return remarks


def _basis_text(item: dict[str, Any], pricing_rules: dict[str, Any]) -> str:
    item_id = str(item.get("item_id") or "")
    if (
        isinstance(pricing_rules.get("lump_sum_overrides"), dict)
        and item_id in pricing_rules["lump_sum_overrides"]
    ):
        return "lump_sum_override"
    return "default_rule"


def _conditions_for(item: dict[str, Any], decision: str) -> list[str]:
    if decision == "tbc":
        return ["Subject to confirmation"]
    if decision == "excluded":
        return ["Not included in current quote scope"]
    return []


def _notes_for(item: dict[str, Any], quote_request: dict[str, Any]) -> list[str]:
    notes = []
    reason = str(item.get("reason") or "").strip()
    if reason:
        notes.append(reason)
    pending_confirmations = []
    risk_context = quote_request.get("risk_context")
    if isinstance(risk_context, dict) and isinstance(
        risk_context.get("pending_confirmations"), list
    ):
        pending_confirmations = [
            str(text).strip()
            for text in risk_context["pending_confirmations"]
            if str(text).strip()
        ]
    if pending_confirmations and str(item.get("item_type") or "") == "spare_parts":
        notes.extend(pending_confirmations[:1])
    return notes


def _pick_currency(
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    historical_reference: dict[str, Any],
) -> str:
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )
    if (
        isinstance(pricing_rules.get("currency"), str)
        and pricing_rules["currency"].strip()
    ):
        return pricing_rules["currency"].strip()
    if (
        isinstance(header_context.get("currency"), str)
        and header_context["currency"].strip()
    ):
        return header_context["currency"].strip()
    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
    price_range_hint = (
        reference_summary.get("price_range_hint")
        if isinstance(reference_summary.get("price_range_hint"), dict)
        else {}
    )
    if (
        isinstance(price_range_hint.get("currency"), str)
        and price_range_hint["currency"].strip()
    ):
        return price_range_hint["currency"].strip()
    return "USD"


def _section_title(section_type: str) -> str:
    return {
        "service": "Service",
        "spare_parts": "Spare Parts",
        "other": "Other",
    }.get(section_type, "Other")


def _format_amount(amount: float | None) -> str:
    if amount is None:
        return ""
    return f"{amount:,.2f}"
