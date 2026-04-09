from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


HEADER_FIELD_ALIASES = {
    "currency": ["currency", "currency_code"],
    "vessel_name": ["vessel_name", "ship_name"],
    "imo_no": ["imo_no", "imo", "imo_number"],
    "vessel_type": ["vessel_type", "ship_type"],
    "customer_name": ["customer_name", "client_name", "customer"],
    "service_port": ["service_port", "port", "port_name", "service_location"],
    "service_date": ["service_date", "date", "eta", "service_time"],
    "attention": ["attention", "attn", "contact_name"],
    "customer_ref_no": ["customer_ref_no", "your_ref_no", "ref_no"],
}

SERVICE_FIELD_ALIASES = {
    "service_category": ["service_category", "category", "discipline"],
    "service_mode": ["service_mode", "service_type", "job_mode"],
    "location_type": ["location_type", "work_location_type"],
    "urgency": ["urgency", "priority"],
}

CURRENCY_MAP = {
    "usd": "USD",
    "us dollar": "USD",
    "us dollars": "USD",
    "美元": "USD",
    "cny": "CNY",
    "rmb": "CNY",
    "人民币": "CNY",
    "eur": "EUR",
    "euro": "EUR",
    "sgd": "SGD",
    "singapore dollar": "SGD",
}

SERVICE_MODE_MAP = {
    "voyage repair": "voyage_repair",
    "航修": "voyage_repair",
    "dock repair": "dock_repair",
    "厂修": "dock_repair",
    "riding squad": "riding_squad",
    "随航": "riding_squad",
    "inspection": "inspection",
    "检查": "inspection",
    "troubleshooting": "troubleshooting",
    "故障排查": "troubleshooting",
}

LOCATION_TYPE_KEYWORDS = {
    "port": ["port", "码头", "港"],
    "anchorage": ["anchorage", "锚地"],
    "shipyard": ["shipyard", "船厂", "dockyard"],
    "underway": ["underway", "航行中", "随航"],
}

SERVICE_CATEGORY_MAP = {
    "轮机": "mechanical",
    "机务": "mechanical",
    "mechanical": "mechanical",
    "电气": "electrical",
    "electrical": "electrical",
    "第三方": "third_party",
    "third party": "third_party",
    "综合": "integrated",
    "integrated": "integrated",
}


def prepare_quote_request(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    assessment_report = payload.get("assessment_report")
    customer_context = payload.get("customer_context") or {}
    business_context = payload.get("business_context") or {}

    if customer_context is None:
        customer_context = {}
    if business_context is None:
        business_context = {}

    if not isinstance(customer_context, dict) or not isinstance(business_context, dict):
        raise ValueError("customer_context and business_context must be JSON objects.")

    normalization_flags: list[dict[str, Any]] = []
    missing_fields: list[dict[str, Any]] = []
    sources = [
        (
            "business_context",
            business_context if isinstance(business_context, dict) else {},
        ),
        (
            "customer_context",
            customer_context if isinstance(customer_context, dict) else {},
        ),
        (
            "assessment_report",
            assessment_report if isinstance(assessment_report, dict) else {},
        ),
    ]

    if not isinstance(assessment_report, dict):
        quote_request = _empty_quote_request()
        missing_fields.append(
            _missing_field(
                field="assessment_report",
                required_for=["prepare", "feasibility_check", "pricing"],
                severity="high",
                reason="缺少主输入 assessment_report，无法稳定提取报价事实。",
                suggested_source="upstream_assessment_agent",
            )
        )
        return {
            "quote_request": quote_request,
            "normalization_flags": normalization_flags,
            "missing_fields": missing_fields,
        }

    quote_request = _empty_quote_request()
    quote_request["request_meta"] = {
        "request_id": _build_request_id(assessment_report),
        "source": "assessment_report",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "language": "zh-CN",
    }

    header_context = quote_request["header_context"]
    for field, aliases in HEADER_FIELD_ALIASES.items():
        value = _resolve_scalar_field(field, sources, aliases, normalization_flags)
        if field == "currency" and value is not None:
            value = _normalize_currency(value, normalization_flags)
        header_context[field] = value

    service_context = quote_request["service_context"]
    explicit_service_category = _resolve_scalar_field(
        "service_category",
        sources,
        SERVICE_FIELD_ALIASES["service_category"],
        normalization_flags,
    )
    service_context["service_category"] = _normalize_service_category(
        explicit_service_category,
        normalization_flags,
    )

    explicit_service_mode = _resolve_scalar_field(
        "service_mode",
        sources,
        SERVICE_FIELD_ALIASES["service_mode"],
        normalization_flags,
    )
    service_context["service_mode"] = _normalize_service_mode(
        explicit_service_mode,
        normalization_flags,
    )

    explicit_location_type = _resolve_scalar_field(
        "location_type",
        sources,
        SERVICE_FIELD_ALIASES["location_type"],
        normalization_flags,
    )
    service_context["location_type"] = _normalize_location_type(
        explicit_location_type,
        normalization_flags,
    )
    if service_context["location_type"] is None:
        service_context["location_type"] = _infer_location_type(
            header_context.get("service_port"),
            normalization_flags,
        )

    service_context["option_hints"] = _extract_option_hints(payload)
    service_context["needs_multi_option"] = bool(
        service_context["option_hints"]
    ) or _extract_multi_option_flag(payload)

    urgency = _resolve_scalar_field(
        "urgency",
        sources,
        SERVICE_FIELD_ALIASES["urgency"],
        normalization_flags,
    )
    service_context["urgency"] = _clean_text(urgency)

    candidate_items = _extract_candidate_items(assessment_report, normalization_flags)
    quote_request["candidate_items"] = candidate_items
    if service_context["service_category"] is None and candidate_items:
        service_context["service_category"] = "service"

    quote_request["spare_parts_context"] = _extract_spare_parts_context(
        payload, normalization_flags
    )
    quote_request["risk_context"] = _extract_risk_context(payload)
    quote_request["commercial_context"] = _extract_commercial_context(
        payload, header_context.get("currency")
    )
    quote_request["source_refs"] = {
        "assessment_report_id": _first_value(
            assessment_report, ["assessment_report_id", "report_id", "id"]
        ),
        "customer_context_ref": _first_value(
            customer_context, ["customer_context_ref", "id"]
        ),
        "business_context_ref": _first_value(
            business_context, ["business_context_ref", "id"]
        ),
    }

    _populate_missing_fields(quote_request, missing_fields)

    return {
        "quote_request": quote_request,
        "normalization_flags": normalization_flags,
        "missing_fields": missing_fields,
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


def _empty_quote_request() -> dict[str, Any]:
    return {
        "request_meta": {
            "request_id": None,
            "source": "assessment_report",
            "prepared_at": None,
            "language": "zh-CN",
        },
        "header_context": {
            "currency": None,
            "vessel_name": None,
            "imo_no": None,
            "vessel_type": None,
            "customer_name": None,
            "service_port": None,
            "service_date": None,
            "attention": None,
            "customer_ref_no": None,
        },
        "service_context": {
            "service_category": None,
            "service_mode": None,
            "location_type": None,
            "needs_multi_option": False,
            "option_hints": [],
            "urgency": None,
        },
        "candidate_items": [],
        "spare_parts_context": {
            "has_spare_parts": None,
            "spare_parts_supply_mode": None,
            "spare_parts_items": [],
        },
        "risk_context": {
            "risks": [],
            "pending_confirmations": [],
            "assumptions": [],
        },
        "commercial_context": {
            "preferred_currency": None,
            "pricing_expectation": None,
            "special_terms": [],
        },
        "source_refs": {
            "assessment_report_id": None,
            "customer_context_ref": None,
            "business_context_ref": None,
        },
    }


def _build_request_id(assessment_report: dict[str, Any]) -> str:
    source_id = _first_value(
        assessment_report, ["assessment_report_id", "report_id", "id"]
    )
    if isinstance(source_id, str) and source_id.strip():
        return f"qr-{source_id.strip()}"
    return f"qr-{uuid4().hex[:8]}"


def _resolve_scalar_field(
    field_name: str,
    sources: list[tuple[str, dict[str, Any]]],
    aliases: list[str],
    normalization_flags: list[dict[str, Any]],
) -> Any:
    candidates: list[tuple[str, str, Any]] = []
    for source_name, source in sources:
        value = _first_value(source, aliases)
        if _is_present(value):
            alias = _matched_alias(source, aliases)
            candidates.append((source_name, alias or aliases[0], value))

    if not candidates:
        return None

    selected_source, selected_alias, selected_value = candidates[0]
    cleaned_value = _clean_value(selected_value)

    if selected_alias != aliases[0]:
        normalization_flags.append(
            {
                "flag_code": "normalized_input_alias",
                "field": field_name,
                "from": selected_alias,
                "to": aliases[0],
                "reason": f"统一字段别名，来源 {selected_source}。",
            }
        )

    for other_source, _, other_value in candidates[1:]:
        if _compare_values(cleaned_value, other_value):
            continue
        normalization_flags.append(
            {
                "flag_code": "resolved_input_conflict",
                "field": field_name,
                "from": {
                    selected_source: cleaned_value,
                    other_source: _clean_value(other_value),
                },
                "to": cleaned_value,
                "reason": "按 business_context > customer_context > assessment_report 优先级选取。",
            }
        )
        break

    return cleaned_value


def _extract_option_hints(payload: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for source_name in ["business_context", "customer_context", "assessment_report"]:
        source = payload.get(source_name)
        if not isinstance(source, dict):
            continue
        for key in ["option_hints", "options", "alternative_options"]:
            raw = source.get(key)
            if isinstance(raw, list):
                for item in raw:
                    text = _extract_option_hint_text(item)
                    if text:
                        values.append(text)
            else:
                text = _extract_option_hint_text(raw)
                if text:
                    values.append(text)
    return _dedupe_list(values)


def _extract_multi_option_flag(payload: dict[str, Any]) -> bool:
    for source_name in ["business_context", "customer_context", "assessment_report"]:
        source = payload.get(source_name)
        if not isinstance(source, dict):
            continue
        for key in ["needs_multi_option", "multi_option", "has_multiple_options"]:
            value = source.get(key)
            if isinstance(value, bool):
                return value
    return False


def _extract_candidate_items(
    assessment_report: dict[str, Any],
    normalization_flags: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_collections = [
        ("service_items", "service"),
        ("items", "service"),
        ("tasks", "service"),
        ("work_items", "service"),
        ("spare_parts_items", "spare_parts"),
    ]
    items: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for key, default_type in raw_collections:
        raw_items = assessment_report.get(key)
        if not isinstance(raw_items, list):
            continue
        for raw_item in raw_items:
            item = _build_candidate_item(raw_item, default_type, len(items) + 1)
            if item is None:
                continue
            identity = (item["item_type"], item["title"])
            if identity in seen:
                normalization_flags.append(
                    {
                        "flag_code": "merged_duplicate_candidate_items",
                        "field": "candidate_items",
                        "from": item["title"],
                        "to": item["title"],
                        "reason": "合并重复候选项标题。",
                    }
                )
                continue
            seen.add(identity)
            items.append(item)

    if items:
        return items

    fallback_text = _first_value(
        assessment_report, ["service_content", "work_content", "summary"]
    )
    if isinstance(fallback_text, str) and fallback_text.strip():
        return [
            {
                "item_id": "svc-1",
                "item_type": "service",
                "title": _clean_text(fallback_text),
                "description": "",
                "work_scope": [],
                "quantity_hint": None,
                "unit_hint": None,
                "labor_hint": [],
                "pricing_clues": [],
                "status_hint": None,
                "source": "assessment_report",
            }
        ]

    return []


def _build_candidate_item(
    raw_item: Any, default_type: str, index: int
) -> dict[str, Any] | None:
    if isinstance(raw_item, str):
        title = _clean_text(raw_item)
        if not title:
            return None
        return {
            "item_id": f"{_item_prefix(default_type)}-{index}",
            "item_type": default_type,
            "title": title,
            "description": "",
            "work_scope": [],
            "quantity_hint": None,
            "unit_hint": None,
            "labor_hint": [],
            "pricing_clues": [],
            "status_hint": None,
            "source": "assessment_report",
        }

    if not isinstance(raw_item, dict):
        return None

    title = _first_value(raw_item, ["title", "name", "item", "task"])
    description = _first_value(raw_item, ["description", "detail", "details"])
    details = raw_item.get("details")
    work_scope = _string_list(raw_item.get("work_scope"))
    if not work_scope and isinstance(details, list):
        cleaned_details = _string_list(details)
        if cleaned_details:
            if not title:
                title = cleaned_details[0]
                cleaned_details = cleaned_details[1:]
            elif not description:
                description = cleaned_details[0]
                cleaned_details = cleaned_details[1:]
            work_scope = cleaned_details

    title_text = _clean_text(title)
    if not title_text:
        return None

    item_type = _normalize_item_type(
        _first_value(raw_item, ["item_type", "type"]) or default_type
    )
    return {
        "item_id": f"{_item_prefix(item_type)}-{index}",
        "item_type": item_type,
        "title": title_text,
        "description": _clean_text(description) or "",
        "work_scope": work_scope,
        "quantity_hint": raw_item.get("quantity") or raw_item.get("qty"),
        "unit_hint": _clean_text(raw_item.get("unit")),
        "labor_hint": _string_list(raw_item.get("labor_hint") or raw_item.get("labor")),
        "pricing_clues": _string_list(
            raw_item.get("pricing_clues") or raw_item.get("price_hints")
        ),
        "status_hint": _clean_text(
            raw_item.get("status_hint") or raw_item.get("status")
        ),
        "source": "assessment_report",
    }


def _extract_spare_parts_context(
    payload: dict[str, Any],
    normalization_flags: list[dict[str, Any]],
) -> dict[str, Any]:
    assessment_report = (
        payload.get("assessment_report")
        if isinstance(payload.get("assessment_report"), dict)
        else {}
    )
    customer_context = (
        payload.get("customer_context")
        if isinstance(payload.get("customer_context"), dict)
        else {}
    )
    business_context = (
        payload.get("business_context")
        if isinstance(payload.get("business_context"), dict)
        else {}
    )

    raw_items = (
        assessment_report.get("spare_parts_items")
        or assessment_report.get("spare_parts")
        or customer_context.get("spare_parts_items")
        or []
    )
    spare_parts_items = []
    if isinstance(raw_items, list):
        for idx, item in enumerate(raw_items, start=1):
            built = _build_candidate_item(item, "spare_parts", idx)
            if built:
                spare_parts_items.append(built)

    supply_mode_raw = _first_value(
        business_context,
        ["spare_parts_supply_mode", "parts_supply_mode"],
    )
    if supply_mode_raw is None:
        supply_mode_raw = _first_value(
            customer_context,
            ["spare_parts_supply_mode", "parts_supply_mode"],
        )
    if supply_mode_raw is None:
        supply_mode_raw = _first_value(
            assessment_report,
            ["spare_parts_supply_mode", "parts_supply_mode"],
        )

    supply_mode = _normalize_supply_mode(supply_mode_raw, normalization_flags)
    has_spare_parts = None
    if spare_parts_items:
        has_spare_parts = True
    elif isinstance(assessment_report.get("spare_parts_needed"), bool):
        has_spare_parts = assessment_report["spare_parts_needed"]

    return {
        "has_spare_parts": has_spare_parts,
        "spare_parts_supply_mode": supply_mode,
        "spare_parts_items": spare_parts_items,
    }


def _extract_risk_context(payload: dict[str, Any]) -> dict[str, Any]:
    combined = []
    for source_name in ["assessment_report", "customer_context", "business_context"]:
        source = payload.get(source_name)
        if isinstance(source, dict):
            combined.append(source)

    risks = _dedupe_list(
        _gather_string_values(combined, ["risks", "risk_flags", "risk_points"])
    )
    pending = _dedupe_list(
        _gather_string_values(
            combined,
            ["pending_items", "pending_confirmations", "tbc_items", "questions"],
        )
    )
    assumptions = _dedupe_list(
        _gather_string_values(combined, ["assumptions", "assumption_notes"])
    )
    return {
        "risks": risks,
        "pending_confirmations": pending,
        "assumptions": assumptions,
    }


def _extract_commercial_context(
    payload: dict[str, Any], header_currency: Any
) -> dict[str, Any]:
    customer_context = (
        payload.get("customer_context")
        if isinstance(payload.get("customer_context"), dict)
        else {}
    )
    business_context = (
        payload.get("business_context")
        if isinstance(payload.get("business_context"), dict)
        else {}
    )
    preferred_currency = (
        _first_value(customer_context, ["preferred_currency", "currency"])
        or header_currency
    )
    pricing_expectation = _first_value(
        customer_context, ["pricing_expectation", "budget_hint"]
    )
    if pricing_expectation is None:
        pricing_expectation = _first_value(
            business_context, ["pricing_expectation", "budget_hint"]
        )

    special_terms = _dedupe_list(
        _gather_string_values(
            [customer_context, business_context], ["special_terms", "commercial_terms"]
        )
    )
    return {
        "preferred_currency": _clean_text(header_currency)
        or _clean_text(preferred_currency),
        "pricing_expectation": _clean_text(pricing_expectation),
        "special_terms": special_terms,
    }


def _populate_missing_fields(
    quote_request: dict[str, Any], missing_fields: list[dict[str, Any]]
) -> None:
    header = quote_request["header_context"]
    service = quote_request["service_context"]

    if not _is_present(header.get("currency")):
        missing_fields.append(
            _missing_field(
                "header_context.currency",
                ["pricing", "quote_document"],
                "medium",
                "缺少币种，影响金额展示与表头补齐。",
                "customer_context",
            )
        )
    if not _is_present(header.get("vessel_name")):
        missing_fields.append(
            _missing_field(
                "header_context.vessel_name",
                ["quote_document"],
                "high",
                "缺少船名，无法完整生成表头。",
                "assessment_report",
            )
        )
    if not _is_present(header.get("customer_name")):
        missing_fields.append(
            _missing_field(
                "header_context.customer_name",
                ["quote_document"],
                "medium",
                "缺少客户名称，影响表头完整性。",
                "assessment_report",
            )
        )
    if not _is_present(header.get("vessel_type")):
        missing_fields.append(
            _missing_field(
                "header_context.vessel_type",
                ["pricing", "quote_document"],
                "medium",
                "缺少船型，可能影响历史参考和表头完整性。",
                "assessment_report",
            )
        )
    if not _is_present(header.get("service_port")):
        missing_fields.append(
            _missing_field(
                "header_context.service_port",
                ["feasibility_check", "pricing", "quote_document"],
                "high",
                "缺少服务地点，影响附加费用和表头判断。",
                "customer_context",
            )
        )
    if not _is_present(header.get("service_date")):
        missing_fields.append(
            _missing_field(
                "header_context.service_date",
                ["pricing", "quote_document"],
                "medium",
                "缺少服务日期，影响部分费用判断和表头补齐。",
                "customer_context",
            )
        )
    if not _is_present(service.get("service_mode")):
        missing_fields.append(
            _missing_field(
                "service_context.service_mode",
                ["feasibility_check", "pricing"],
                "medium",
                "缺少服务模式，影响历史参考与定价。",
                "business_context",
            )
        )
    if not quote_request["candidate_items"]:
        missing_fields.append(
            _missing_field(
                "candidate_items",
                ["feasibility_check", "pricing"],
                "high",
                "缺少候选报价项，无法进入稳定报价链路。",
                "assessment_report",
            )
        )


def _normalize_currency(value: Any, normalization_flags: list[dict[str, Any]]) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    normalized = CURRENCY_MAP.get(text.lower(), text.upper())
    if normalized != text:
        normalization_flags.append(
            {
                "flag_code": "normalized_currency_code",
                "field": "header_context.currency",
                "from": text,
                "to": normalized,
                "reason": "统一币种编码。",
            }
        )
    return normalized


def _normalize_service_mode(
    value: Any, normalization_flags: list[dict[str, Any]]
) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    normalized = SERVICE_MODE_MAP.get(
        text.lower(), SERVICE_MODE_MAP.get(text, text.lower().replace(" ", "_"))
    )
    if normalized != text:
        normalization_flags.append(
            {
                "flag_code": "normalized_service_mode",
                "field": "service_context.service_mode",
                "from": text,
                "to": normalized,
                "reason": "统一服务模式枚举。",
            }
        )
    return normalized


def _normalize_service_category(
    value: Any, normalization_flags: list[dict[str, Any]]
) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    normalized = SERVICE_CATEGORY_MAP.get(
        text.lower(), SERVICE_CATEGORY_MAP.get(text, text.lower().replace(" ", "_"))
    )
    if normalized != text:
        normalization_flags.append(
            {
                "flag_code": "normalized_service_category",
                "field": "service_context.service_category",
                "from": text,
                "to": normalized,
                "reason": "统一服务类别表达。",
            }
        )
    return normalized


def _normalize_location_type(
    value: Any, normalization_flags: list[dict[str, Any]]
) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    for normalized, keywords in LOCATION_TYPE_KEYWORDS.items():
        if any(keyword in lowered or keyword in text for keyword in keywords):
            if normalized != text:
                normalization_flags.append(
                    {
                        "flag_code": "normalized_location_type",
                        "field": "service_context.location_type",
                        "from": text,
                        "to": normalized,
                        "reason": "统一地点类型表达。",
                    }
                )
            return normalized
    return lowered.replace(" ", "_")


def _infer_location_type(value: Any, normalization_flags: list[dict[str, Any]]) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    for normalized, keywords in LOCATION_TYPE_KEYWORDS.items():
        if any(keyword in lowered or keyword in text for keyword in keywords):
            normalization_flags.append(
                {
                    "flag_code": "normalized_location_type",
                    "field": "service_context.location_type",
                    "from": text,
                    "to": normalized,
                    "reason": "基于显式地点文本推断地点类型。",
                }
            )
            return normalized
    return None


def _normalize_supply_mode(
    value: Any, normalization_flags: list[dict[str, Any]]
) -> Any:
    text = _clean_text(value)
    if not text:
        return None
    lowered = text.lower()
    mapping = {
        "owner supply": "owner_supply",
        "owner supplied": "owner_supply",
        "船东提供": "owner_supply",
        "甲供": "owner_supply",
        "shipside supply": "owner_supply",
        "shipside": "owner_supply",
        "company supply": "company_supply",
        "自供": "company_supply",
    }
    normalized = mapping.get(lowered, mapping.get(text, lowered.replace(" ", "_")))
    if normalized != text:
        normalization_flags.append(
            {
                "flag_code": "normalized_supply_mode",
                "field": "spare_parts_context.spare_parts_supply_mode",
                "from": text,
                "to": normalized,
                "reason": "统一备件供货方式表达。",
            }
        )
    return normalized


def _normalize_item_type(value: Any) -> str:
    text = _clean_text(value) or "service"
    lowered = text.lower()
    if lowered in {"service", "spare_parts", "other"}:
        return lowered
    if lowered in {"spares", "spare parts", "parts"}:
        return "spare_parts"
    return "service"


def _item_prefix(item_type: str) -> str:
    return {
        "service": "svc",
        "spare_parts": "spr",
        "other": "oth",
    }.get(item_type, "svc")


def _first_value(source: dict[str, Any], aliases: list[str]) -> Any:
    for alias in aliases:
        value = source.get(alias)
        if _is_present(value):
            return value
    return None


def _matched_alias(source: dict[str, Any], aliases: list[str]) -> str | None:
    for alias in aliases:
        if _is_present(source.get(alias)):
            return alias
    return None


def _extract_option_hint_text(item: Any) -> str | None:
    if isinstance(item, str):
        return _clean_text(item)
    if isinstance(item, dict):
        return _clean_text(_first_value(item, ["title", "name", "option_id"]))
    return None


def _gather_string_values(sources: list[dict[str, Any]], keys: list[str]) -> list[str]:
    values: list[str] = []
    for source in sources:
        for key in keys:
            raw = source.get(key)
            values.extend(_string_list(raw))
    return values


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [text for text in (_clean_text(item) for item in value) if text]
    if isinstance(value, str):
        cleaned = _clean_text(value)
        return [cleaned] if cleaned else []
    return []


def _dedupe_list(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value)
    return result


def _clean_value(value: Any) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    return value


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(_clean_text(value))
    if isinstance(value, list):
        return len(value) > 0
    return True


def _compare_values(left: Any, right: Any) -> bool:
    return _clean_value(left) == _clean_value(right)


def _missing_field(
    field: str,
    required_for: list[str],
    severity: str,
    reason: str,
    suggested_source: str,
) -> dict[str, Any]:
    return {
        "field": field,
        "required_for": required_for,
        "severity": severity,
        "reason": reason,
        "suggested_source": suggested_source,
    }
