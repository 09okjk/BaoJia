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
    prepare_result = (
        payload.get("prepare_result")
        if isinstance(payload.get("prepare_result"), dict)
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
    feedback_reference = (
        payload.get("feedback_reference")
        if isinstance(payload.get("feedback_reference"), dict)
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
    footer = _build_footer(quote_request, quotation_options, historical_reference)
    review_result = _build_review_result(
        feasibility_result,
        quotation_options,
        historical_reference,
        prepare_result,
        feedback_reference,
    )
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

    service_date = _string_or_blank(header_context.get("service_date"))
    quote_date = date.today().isoformat()
    date_value = service_date if _looks_like_iso_date(service_date) else quote_date
    your_ref_no = _string_or_blank(header_context.get("customer_ref_no"))
    if service_date and not _looks_like_iso_date(service_date):
        your_ref_no = (
            f"{your_ref_no} | Service window: {service_date}"
            if your_ref_no
            else f"Service window: {service_date}"
        )

    return {
        "currency": _string_or_blank(
            header_context.get("currency")
            or commercial_context.get("preferred_currency")
        ),
        "vessel_name": _string_or_blank(header_context.get("vessel_name")),
        "date": date_value,
        "imo_no": _string_or_blank(header_context.get("imo_no")),
        "vessel_type": _string_or_blank(header_context.get("vessel_type")),
        "customer_name": _string_or_blank(header_context.get("customer_name")),
        "service_port": _string_or_blank(header_context.get("service_port")),
        "attention": _string_or_blank(header_context.get("attention")),
        "wk_offer_no": _build_offer_no(quote_request),
        "your_ref_no": your_ref_no,
        "quotation_validity": _quotation_validity(quote_request),
        "po_no": "",
        "pic_of_winkong": _pic_of_winkong(quote_request),
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
    quote_request: dict[str, Any],
    quotation_options: list[Any],
    historical_reference: dict[str, Any],
) -> dict[str, Any]:
    currency = _footer_currency(quote_request, quotation_options)
    summary = _build_footer_summary(quotation_options, currency)
    remarks = _build_footer_remarks(
        quote_request, quotation_options, historical_reference
    )
    return {
        "summary": summary,
        "remark": {
            "title": "Remark",
            "items": remarks,
        },
        "service_payment_terms": {
            "title": "Service Payment Terms",
            "content": _service_payment_terms(quote_request),
        },
    }


def _build_footer_summary(
    quotation_options: list[Any], currency: str
) -> dict[str, Any]:
    valid_options = [option for option in quotation_options if isinstance(option, dict)]
    if not valid_options:
        return _empty_summary(currency)
    if len(valid_options) == 1:
        return valid_options[0]["summary"]

    recommended = _recommended_option(valid_options)
    if recommended is not None:
        return recommended["summary"]

    return {
        "service_charge": _summary_value(
            None, "Refer to selected option", currency, "pending", "text"
        ),
        "spare_parts_fee": _summary_value(
            None, "Refer to selected option", currency, "pending", "text"
        ),
        "other": _summary_value(
            None, "Refer to selected option", currency, "pending", "text"
        ),
        "total": _summary_value(
            None, "Refer to selected option", currency, "pending", "text"
        ),
    }


def _recommended_option(
    quotation_options: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for option in quotation_options:
        option_id = _string_or_blank(option.get("option_id")).lower()
        title = _string_or_blank(option.get("title")).lower()
        if option_id in {"option-a", "option-1"}:
            return option
        if "standard" in title or "recommended" in title or "base" in title:
            return option
    return quotation_options[0] if quotation_options else None


def _build_footer_remarks(
    quote_request: dict[str, Any],
    quotation_options: list[Any],
    historical_reference: dict[str, Any],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
    remark_blocks = (
        reference_summary.get("remark_blocks")
        if isinstance(reference_summary.get("remark_blocks"), list)
        else []
    )
    for block in remark_blocks:
        if not isinstance(block, dict):
            continue
        remark_type = _string_or_blank(block.get("remark_type")) or "commercial"
        texts = block.get("texts") if isinstance(block.get("texts"), list) else []
        for text in texts[:2]:
            cleaned = _string_or_blank(text)
            if not cleaned:
                continue
            if _should_skip_historical_footer_remark(cleaned, quote_request):
                continue
            normalized_type = _remark_type(remark_type, cleaned)
            key = _remark_identity(normalized_type, cleaned)
            if key in seen:
                continue
            seen.add(key)
            items.append({"type": normalized_type, "text": cleaned})

    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        for remark in option.get("remarks", []):
            if not isinstance(remark, dict):
                continue
            remark_type = _remark_type(
                _string_or_blank(remark.get("type")),
                _string_or_blank(remark.get("text")),
            )
            text = _string_or_blank(remark.get("text"))
            if not text:
                continue
            if _should_skip_historical_footer_remark(text, quote_request):
                continue
            key = _remark_identity(remark_type, text)
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
        if _should_skip_historical_footer_remark(text, quote_request):
            continue
        remark_type = _remark_type("commercial", text)
        key = _remark_identity(remark_type, text)
        if key in seen:
            continue
        seen.add(key)
        items.append({"type": remark_type, "text": text})

    draft_remarks = _draft_footer_remarks(quote_request, quotation_options)
    for item in draft_remarks:
        key = _remark_identity(item["type"], item["text"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    default_remarks = _default_footer_remarks(quotation_options)
    for item in default_remarks:
        if _should_skip_historical_footer_remark(item["text"], quote_request):
            continue
        key = _remark_identity(item["type"], item["text"])
        if key in seen:
            continue
        seen.add(key)
        items.append(item)

    return items


def _default_footer_remarks(quotation_options: list[Any]) -> list[dict[str, str]]:
    has_service = False
    has_spare_parts = False
    has_voyage_or_riding = False
    has_troubleshooting = False

    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        for section in option.get("sections", []):
            if not isinstance(section, dict):
                continue
            section_type = _string_or_blank(section.get("section_type"))
            if section_type == "service":
                has_service = True
            if section_type == "spare_parts":
                has_spare_parts = True
            for group in section.get("groups", []):
                if not isinstance(group, dict):
                    continue
                text = (
                    _string_or_blank(group.get("title"))
                    + " "
                    + _string_or_blank(group.get("description"))
                ).lower()
                if any(
                    keyword in text for keyword in ["voyage", "航修", "riding", "随航"]
                ):
                    has_voyage_or_riding = True
                if any(
                    keyword in text
                    for keyword in ["inspection", "检查", "troubleshooting", "排查"]
                ):
                    has_troubleshooting = True

    remarks = []
    if has_spare_parts:
        remarks.append(
            {
                "type": "warranty",
                "text": "Spare parts warranty period shall follow supplier confirmation.",
            }
        )
    if has_service:
        warranty_text = (
            "Inspection and troubleshooting items carry no service warranty."
            if has_troubleshooting
            else "Service warranty is 6 months from completion unless otherwise agreed."
        )
        remarks.append({"type": "warranty", "text": warranty_text})
        remarks.append(
            {
                "type": "compensation",
                "text": "Warranty Compensate Amount: 5 times of the service cost at max.",
            }
        )
    if has_voyage_or_riding:
        remarks.append(
            {
                "type": "waiting",
                "text": "Waiting cost caused by weather or vessel delay shall be negotiated amicably, normally 300-500 USD per person per day.",
            }
        )
        remarks.append(
            {
                "type": "safety",
                "text": "Safety environment/measures on board shall be arranged by owner side.",
            }
        )
    if not remarks:
        remarks.append(
            {
                "type": "commercial",
                "text": "Quoted scope is subject to final onboard condition.",
            }
        )
    return remarks


def _draft_footer_remarks(
    quote_request: dict[str, Any], quotation_options: list[Any]
) -> list[dict[str, str]]:
    if not _is_internal_draft(quote_request, quotation_options):
        return []
    return [
        {
            "type": "tbc",
            "text": "Internal draft only. This quotation still contains pending confirmations and is not ready for final external release.",
        }
    ]


def _build_review_result(
    feasibility_result: dict[str, Any],
    quotation_options: list[Any],
    historical_reference: dict[str, Any],
    prepare_result: dict[str, Any] | None = None,
    feedback_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    review_flags = (
        feasibility_result.get("review_flags")
        if isinstance(feasibility_result.get("review_flags"), list)
        else []
    )
    missing_fields = []
    feasibility_missing_fields = (
        feasibility_result.get("missing_fields")
        if isinstance(feasibility_result.get("missing_fields"), list)
        else []
    )
    prepare_missing_fields = []
    if isinstance(prepare_result, dict):
        prepare_missing_fields = (
            prepare_result.get("missing_fields")
            if isinstance(prepare_result.get("missing_fields"), list)
            else []
        )
    missing_fields.extend(
        item for item in feasibility_missing_fields if isinstance(item, dict)
    )
    missing_fields.extend(
        item for item in prepare_missing_fields if isinstance(item, dict)
    )

    review_flag_texts = []
    risk_flag_texts = []
    has_high_risk = False
    tbc_option_exists = _has_pending_or_tbc_content(quotation_options)
    multi_option = (
        len([option for option in quotation_options if isinstance(option, dict)]) > 1
    )

    for flag in review_flags:
        if isinstance(flag, dict):
            message = _string_or_blank(flag.get("message"))
            severity = _string_or_blank(flag.get("severity"))
            if message:
                review_flag_texts.append(message)
                if severity in {"high", "medium"}:
                    risk_flag_texts.append(message)
                if severity == "high":
                    has_high_risk = True

    for item in missing_fields:
        if isinstance(item, dict):
            severity = _string_or_blank(item.get("severity"))
            reason = _string_or_blank(item.get("reason"))
            if severity == "high":
                has_high_risk = True
            if reason and severity in {"high", "medium"}:
                risk_flag_texts.append(reason)

    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
    history_quality_flags = (
        reference_summary.get("history_quality_flags")
        if isinstance(reference_summary.get("history_quality_flags"), list)
        else []
    )
    quality_flag_messages = {
        "low_sample_size": "历史参考样本数量不足，请谨慎参考历史报价。",
        "weak_top_match": "当前项目与历史案例最高匹配度偏弱，请人工复核。",
        "weak_item_overlap": "当前项目与历史案例的明细项重合度较低，请人工确认。",
        "broad_price_range": "历史价格区间较宽，不能直接据此判断最终价格。",
        "context_only_match": "当前历史参考主要依赖上下文匹配，缺少强明细项支撑。",
    }
    for flag in history_quality_flags:
        message = quality_flag_messages.get(str(flag).strip())
        if not message:
            continue
        review_flag_texts.append(message)
        if flag in {"weak_top_match", "weak_item_overlap", "context_only_match"}:
            risk_flag_texts.append(message)

    if isinstance(feedback_reference, dict):
        review_alerts = (
            feedback_reference.get("review_alerts")
            if isinstance(feedback_reference.get("review_alerts"), list)
            else []
        )
        for alert in review_alerts:
            text = _string_or_blank(alert)
            if text:
                review_flag_texts.append(text)

    if multi_option:
        review_flag_texts.append("当前报价包含多方案，提交审核时需确认推荐方案。")
    if tbc_option_exists:
        review_flag_texts.append(
            "当前报价包含待确认或按条件收费内容，提交前需再次核对。"
        )

    approval_level = "standard"
    if has_high_risk:
        approval_level = "manager"
    elif multi_option or tbc_option_exists:
        approval_level = "manager"

    return {
        "review_flags": _dedupe_strings(review_flag_texts),
        "risk_flags": _dedupe_strings(risk_flag_texts),
        "approval_level": approval_level,
    }


def _has_pending_or_tbc_content(quotation_options: list[Any]) -> bool:
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
                    if _string_or_blank(line.get("status")) in {
                        "pending",
                        "if_needed",
                        "as_actual",
                    }:
                        return True
    return False


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
    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
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

    if isinstance(
        reference_summary.get("remark_blocks"), list
    ) and reference_summary.get("remark_blocks"):
        pricing_basis.append("historical_remark_block")
    if isinstance(
        reference_summary.get("charge_item_hints"), list
    ) and reference_summary.get("charge_item_hints"):
        pricing_basis.append("historical_charge_item_hint")
    if isinstance(
        reference_summary.get("option_style_hints"), list
    ) and reference_summary.get("option_style_hints"):
        pricing_basis.append("historical_option_style_hint")
    history_quality_flags = (
        reference_summary.get("history_quality_flags")
        if isinstance(reference_summary.get("history_quality_flags"), list)
        else []
    )
    if history_quality_flags:
        pricing_basis.extend(
            [f"history_quality:{flag}" for flag in history_quality_flags]
        )

    rule_versions = ["quote_pricing_skill:v2", "quote_review_output_skill:v2"]
    if len([option for option in quotation_options if isinstance(option, dict)]) > 1:
        rule_versions.append("multi_option_footer_strategy:v1")
    if isinstance(
        reference_summary.get("remark_blocks"), list
    ) and reference_summary.get("remark_blocks"):
        rule_versions.append("historical_remark_blocks:v1")
    if isinstance(
        reference_summary.get("charge_item_hints"), list
    ) and reference_summary.get("charge_item_hints"):
        rule_versions.append("historical_charge_item_hints:v1")
    if isinstance(
        reference_summary.get("option_style_hints"), list
    ) and reference_summary.get("option_style_hints"):
        rule_versions.append("historical_option_style_hints:v1")

    return {
        "historical_references": historical_references,
        "pricing_basis": _dedupe_strings(pricing_basis),
        "rule_versions": rule_versions,
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


def _footer_currency(
    quote_request: dict[str, Any], quotation_options: list[Any]
) -> str:
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )
    currency = _string_or_blank(header_context.get("currency"))
    if currency:
        return currency
    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        summary = option.get("summary")
        if isinstance(summary, dict):
            total = summary.get("total")
            if isinstance(total, dict):
                value = _string_or_blank(total.get("currency"))
                if value:
                    return value
    return "USD"


def _quotation_validity(quote_request: dict[str, Any]) -> str:
    if _is_internal_draft(quote_request):
        return "Internal draft - pending confirmation"
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
        if "validity" in text.lower() or "有效期" in text:
            return text
    return "30 days"


def _service_payment_terms(quote_request: dict[str, Any]) -> str:
    if _is_internal_draft(quote_request):
        return "Draft only. Final payment terms shall be confirmed after pending scope and supply responsibility are closed."
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
        lowered = text.lower()
        if "payment" in lowered or "付款" in text:
            return text
    return "Payment within 30 days upon invoice date."


def _pic_of_winkong(quote_request: dict[str, Any]) -> str:
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )
    attention = _string_or_blank(header_context.get("attention"))
    return attention or "Winkong"


def _remark_type(default_type: str, text: str) -> str:
    lowered = text.lower()
    if "warranty" in lowered or "质保" in text:
        return "warranty"
    if "compensate" in lowered or "赔偿" in text:
        return "compensation"
    if "waiting" in lowered or "等待" in text:
        return "waiting"
    if "safety" in lowered or "安全" in text:
        return "safety"
    if "exclude" in lowered or "not included" in lowered:
        return "exclusion"
    if "payment" in lowered or "付款" in text:
        return "payment_term"
    if default_type in {
        "warranty",
        "compensation",
        "commercial",
        "cost_clause",
        "tax",
        "waiting",
        "safety",
        "exclusion",
        "tbc",
        "payment_term",
    }:
        return default_type
    return "commercial"


def _should_skip_historical_footer_remark(
    text: str, quote_request: dict[str, Any]
) -> bool:
    lowered = text.lower()
    if _is_internal_draft(quote_request) and any(
        keyword in lowered
        for keyword in [
            "including the repair kits",
            "all bearings",
            "renewal with the new pump",
            "price as below",
            "repair kits",
        ]
    ):
        return True
    if not any(
        keyword in lowered
        for keyword in ["shipside", "owner supply", "owner supplied", "船东提供"]
    ):
        return False

    spare_parts_context = (
        quote_request.get("spare_parts_context")
        if isinstance(quote_request.get("spare_parts_context"), dict)
        else {}
    )
    supply_mode = _string_or_blank(
        spare_parts_context.get("spare_parts_supply_mode")
    ).lower()
    return supply_mode not in {"owner_supply", "shipside"}


def _string_or_blank(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


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


def _normalize_remark_text(value: str) -> str:
    normalized = value.strip().lower()
    normalized = normalized.replace("5times", "5 times")
    normalized = " ".join(normalized.split())
    return normalized


def _remark_identity(remark_type: str, text: str) -> tuple[str, str]:
    normalized_text = _normalize_remark_text(text)
    normalized_type = _remark_type(remark_type, normalized_text)
    return (normalized_type, normalized_text)


def _looks_like_iso_date(value: str) -> bool:
    if not value:
        return False
    return len(value) == 10 and value[4] == "-" and value[7] == "-"


def _is_internal_draft(
    quote_request: dict[str, Any], quotation_options: list[Any] | None = None
) -> bool:
    risk_context = (
        quote_request.get("risk_context")
        if isinstance(quote_request.get("risk_context"), dict)
        else {}
    )
    pending_confirmations = risk_context.get("pending_confirmations")
    if isinstance(pending_confirmations, list) and pending_confirmations:
        return True

    if not isinstance(quotation_options, list):
        return False
    for option in quotation_options:
        if not isinstance(option, dict):
            continue
        summary = option.get("summary")
        if not isinstance(summary, dict):
            continue
        total = summary.get("total")
        if (
            isinstance(total, dict)
            and _string_or_blank(total.get("status")) == "pending"
        ):
            return True
    return False
