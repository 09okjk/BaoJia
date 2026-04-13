from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DEFAULT_DISCOUNT_PERCENTAGE = 5.0
DEFAULT_SERVICE_RATES = {
    "mechanical_supervisor_hourly": 55.0,
    "mechanical_technician_hourly": 35.0,
    "electrical_supervisor_hourly": 60.0,
    "electrical_assistant_hourly": 40.0,
}


def build_pricing_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_request = payload.get("quote_request")
    feasibility_result = payload.get("feasibility_result")
    historical_reference = payload.get("historical_reference") or {}
    pricing_rules = payload.get("pricing_rules") or {}

    if not isinstance(quote_request, dict) or not isinstance(feasibility_result, dict):
        return {"quotation_options": []}

    if not isinstance(historical_reference, dict):
        historical_reference = {}
    if not isinstance(pricing_rules, dict):
        pricing_rules = {}

    feasibility_result = _augment_feasibility_with_history(
        quote_request, feasibility_result, historical_reference
    )
    currency = _pick_currency(quote_request, pricing_rules, historical_reference)
    option_strategies = _build_option_strategies(
        quote_request, pricing_rules, historical_reference
    )

    quotation_options = []
    for option_index, option_strategy in enumerate(option_strategies, start=1):
        option = _build_option(
            quote_request,
            feasibility_result,
            historical_reference,
            pricing_rules,
            currency,
            option_strategy,
            option_index,
        )
        if option is not None:
            quotation_options.append(option)

    return {"quotation_options": quotation_options}


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
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    option_strategy: dict[str, Any],
    option_index: int,
) -> dict[str, Any] | None:
    quotable_items = _decision_items(feasibility_result, "quotable_items")
    tbc_items = _decision_items(feasibility_result, "tbc_items")
    exclusions = _decision_items(feasibility_result, "exclusions")

    sections = []
    sections.extend(
        _build_sections_for_items(
            quotable_items,
            quote_request,
            historical_reference,
            pricing_rules,
            currency,
            decision="quotable",
            option_strategy=option_strategy,
        )
    )
    sections.extend(
        _build_sections_for_items(
            tbc_items,
            quote_request,
            historical_reference,
            pricing_rules,
            currency,
            decision="tbc",
            option_strategy=option_strategy,
        )
    )
    sections.extend(
        _build_sections_for_items(
            exclusions,
            quote_request,
            historical_reference,
            pricing_rules,
            currency,
            decision="excluded",
            option_strategy=option_strategy,
        )
    )

    if not sections:
        return None

    if option_strategy.get("include_spare_parts") is False:
        sections = [
            section
            for section in sections
            if section.get("section_type") != "spare_parts"
        ]
        if not sections:
            return None

    return {
        "option_id": option_strategy["option_id"],
        "title": option_strategy["title"],
        "sections": sections,
        "summary": _build_summary(sections, currency),
        "remarks": _build_option_remarks(
            pricing_rules, historical_reference, option_strategy
        ),
    }


def _decision_items(
    feasibility_result: dict[str, Any], key: str
) -> list[dict[str, Any]]:
    value = feasibility_result.get(key)
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _augment_feasibility_with_history(
    quote_request: dict[str, Any],
    feasibility_result: dict[str, Any],
    historical_reference: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(feasibility_result, dict):
        return feasibility_result

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
    charge_item_hints = _history_charge_item_hints(historical_reference)
    if not charge_item_hints or "context_only_match" in history_quality_flags:
        return feasibility_result

    quotable_items = _decision_items(feasibility_result, "quotable_items")
    existing_titles = {
        str(item.get("title") or "").strip().lower()
        for item in quotable_items
        if isinstance(item, dict)
    }

    auto_items = []
    for hint_type in charge_item_hints:
        auto_item = _history_hint_to_other_item(
            hint_type, quote_request, existing_titles
        )
        if auto_item is not None:
            auto_items.append(auto_item)
            existing_titles.add(str(auto_item.get("title") or "").strip().lower())

    if not auto_items:
        return feasibility_result

    augmented = dict(feasibility_result)
    augmented["quotable_items"] = quotable_items + auto_items
    return augmented


def _history_hint_to_other_item(
    hint_type: str, quote_request: dict[str, Any], existing_titles: set[str]
) -> dict[str, Any] | None:
    risk_context = (
        quote_request.get("risk_context")
        if isinstance(quote_request.get("risk_context"), dict)
        else {}
    )
    pending_confirmations = (
        risk_context.get("pending_confirmations")
        if isinstance(risk_context.get("pending_confirmations"), list)
        else []
    )
    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    service_mode = str(service_context.get("service_mode") or "").strip().lower()

    mapping = {
        "dockyard_management": {
            "title": "Dockyard management fee",
            "description": "Historical cases often include dockyard management related charges.",
            "keywords": ["dockyard", "shipyard", "厂修"],
            "reason": "历史相似报价中常见厂修管理相关费用，建议保守纳入报价结构。",
            "suggested_status": "as_actual",
        },
        "maritime_reporting": {
            "title": "Maritime reporting / safety permit",
            "description": "Historical cases often include maritime reporting or safety permit related charges.",
            "keywords": ["maritime", "permit", "报备", "动火", "安全"],
            "reason": "历史相似报价中存在报备或安全许可线索，建议保守纳入结构。",
            "suggested_status": "if_needed",
        },
        "transportation": {
            "title": "Transportation",
            "description": "Historical cases often include transportation charges.",
            "keywords": ["travel", "交通", "ticket"],
            "reason": "历史相似报价中常见交通费，建议保守纳入结构。",
            "suggested_status": "as_actual",
        },
        "accommodation": {
            "title": "Accommodation",
            "description": "Historical cases often include accommodation charges.",
            "keywords": ["hotel", "住宿", "食宿"],
            "reason": "历史相似报价中常见住宿或食宿费，建议保守纳入结构。",
            "suggested_status": "if_needed",
        },
    }
    config = mapping.get(hint_type)
    if not config:
        return None

    title_key = config["title"].lower()
    if title_key in existing_titles:
        return None
    if (
        hint_type == "dockyard_management"
        and "dock" not in service_mode
        and "yard" not in service_mode
    ):
        return None
    if hint_type == "maritime_reporting" and not any(
        any(keyword in str(text).lower() for keyword in config["keywords"])
        for text in pending_confirmations
    ):
        return None

    return {
        "item_id": f"hist-other-{hint_type}",
        "item_type": "other",
        "title": config["title"],
        "decision": "quotable",
        "reason": config["reason"],
        "blocking_fields": [],
        "suggested_status": config["suggested_status"],
        "source": "historical_reference",
    }


def _build_option_strategies(
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    historical_reference: dict[str, Any],
) -> list[dict[str, Any]]:
    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    option_hints = service_context.get("option_hints")
    option_titles = (
        [str(item).strip() for item in option_hints if str(item).strip()]
        if isinstance(option_hints, list)
        else []
    )
    option_titles = _dedupe_strings(option_titles)

    multi_option = bool(service_context.get("needs_multi_option")) or bool(
        pricing_rules.get("multi_option_mode")
    )
    discount_percentage = _default_discount_percentage(pricing_rules)
    option_style_hints = _history_option_style_hints(historical_reference)

    if not multi_option and "service_only" in option_style_hints:
        multi_option = True

    if not multi_option:
        title = option_titles[0] if option_titles else "Option 1"
        return [
            {
                "option_id": "option-1",
                "title": title,
                "discount_percentage": 0.0,
                "is_recommended": True,
                "alternative_to_option_id": None,
            }
        ]

    if not option_titles:
        if "service_only" in option_style_hints or "spares_tbc" in option_style_hints:
            option_titles = [
                "Option A Standard quotation",
                "Option B Service only quotation",
            ]
        else:
            option_titles = [
                "Option A Standard quotation",
                f"Option B {discount_percentage:.0f}% discount quotation",
            ]
    elif len(option_titles) == 1:
        if "service_only" in option_style_hints or "spares_tbc" in option_style_hints:
            option_titles.append("Option B Service only quotation")
        else:
            option_titles.append(
                f"Option B {discount_percentage:.0f}% discount quotation"
            )

    strategies = []
    for index, title in enumerate(option_titles, start=1):
        normalized_title = title.lower()
        apply_discount = False
        include_spare_parts = True
        if index == 2 and discount_percentage > 0:
            apply_discount = True
        if any(keyword in normalized_title for keyword in ["discount", "折扣"]):
            apply_discount = discount_percentage > 0
        if any(
            keyword in normalized_title for keyword in ["service only", "service-only"]
        ):
            include_spare_parts = False

        option_id = f"option-{chr(96 + index)}"
        strategies.append(
            {
                "option_id": option_id,
                "title": title,
                "discount_percentage": discount_percentage if apply_discount else 0.0,
                "is_recommended": index == 1,
                "alternative_to_option_id": "option-a" if index > 1 else None,
                "include_spare_parts": include_spare_parts,
            }
        )
    return strategies


def _build_sections_for_items(
    items: list[dict[str, Any]],
    quote_request: dict[str, Any],
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
    option_strategy: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "service": [],
        "spare_parts": [],
        "other": [],
    }
    for item in items:
        item_type = (
            item.get("item_type") if item.get("item_type") in grouped else "other"
        )
        if (
            item_type == "spare_parts"
            and option_strategy.get("include_spare_parts") is False
        ):
            continue
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
                    historical_reference,
                    pricing_rules,
                    currency,
                    decision,
                    option_strategy,
                )
            )
        sections.append(
            {
                "section_id": f"{option_strategy['option_id']}-section-{section_type}",
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
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
    option_strategy: dict[str, Any],
) -> dict[str, Any]:
    item_id = str(item.get("item_id") or f"{section_type}-{index}")
    title = str(item.get("title") or "")
    candidate_item = _candidate_item_lookup(quote_request).get(item_id, {})
    description = _group_description(item, candidate_item)
    lines = _build_group_lines(
        section_type,
        item,
        candidate_item,
        index,
        quote_request,
        historical_reference,
        pricing_rules,
        currency,
        decision,
        option_strategy,
    )
    return {
        "group_id": f"{option_strategy['option_id']}-group-{item_id}",
        "group_no": str(index),
        "title": title,
        "description": description,
        "lines": lines,
    }


def _build_group_lines(
    section_type: str,
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    index: int,
    quote_request: dict[str, Any],
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
    option_strategy: dict[str, Any],
) -> list[dict[str, Any]]:
    item_id = str(item.get("item_id") or f"line-{index}")
    main_line = _build_line(
        section_type,
        item,
        candidate_item,
        quote_request,
        historical_reference,
        pricing_rules,
        currency,
        decision,
        index,
        option_strategy,
    )
    lines = [main_line]

    scope_lines = _scope_note_lines(
        candidate_item, currency, item_id, option_strategy["option_id"]
    )
    lines.extend(scope_lines)

    if main_line["discount"] is not None:
        lines.append(
            {
                "line_id": f"{option_strategy['option_id']}-line-{item_id}-discount-note",
                "item": "",
                "line_no": "",
                "line_type": "commercial_note",
                "description": f"Commercial discount {main_line['discount']['display']} applied within approved authority.",
                "pricing_mode": "text_only",
                "unit_price": None,
                "unit_price_display": "",
                "unit": "",
                "qty": None,
                "qty_display": "",
                "discount": None,
                "amount": None,
                "amount_display": "",
                "currency": currency,
                "status": "chargeable",
                "basis": "discount_authority",
                "conditions": [],
                "notes": [],
            }
        )

    return lines


def _build_line(
    section_type: str,
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    quote_request: dict[str, Any],
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
    index: int,
    option_strategy: dict[str, Any],
) -> dict[str, Any]:
    item_id = str(item.get("item_id") or f"line-{index}")
    base_amount, line_type, pricing_mode, status, amount_display = _price_line(
        section_type,
        item,
        candidate_item,
        quote_request,
        historical_reference,
        pricing_rules,
        currency,
        decision,
    )

    discount = None
    final_amount = base_amount
    if isinstance(base_amount, (int, float)) and status == "chargeable":
        discount_percentage = _resolve_discount_percentage(
            item, pricing_rules, option_strategy
        )
        if discount_percentage > 0:
            discount = {
                "type": "percentage",
                "value": discount_percentage,
                "display": _format_percentage(discount_percentage),
            }
            final_amount = round(
                float(base_amount) * (1 - discount_percentage / 100), 2
            )
            amount_display = _format_amount(final_amount)

    relation = None
    if option_strategy.get("alternative_to_option_id"):
        relation = {
            "type": "alternative_to",
            "target_line_id": f"{option_strategy['alternative_to_option_id']}-line-{item_id}",
        }

    return {
        "line_id": f"{option_strategy['option_id']}-line-{item_id}",
        "item": str(index),
        "line_no": str(index),
        "line_type": line_type,
        "description": _line_description(item, candidate_item),
        "pricing_mode": pricing_mode,
        "unit_price": float(base_amount)
        if isinstance(base_amount, (int, float))
        else None,
        "unit_price_display": _format_amount(base_amount)
        if isinstance(base_amount, (int, float))
        else "",
        "unit": _line_unit(candidate_item, pricing_mode),
        "qty": _line_qty(candidate_item, pricing_mode),
        "qty_display": _line_qty_display(candidate_item, pricing_mode),
        "discount": discount,
        "amount": float(final_amount)
        if isinstance(final_amount, (int, float))
        else None,
        "amount_display": amount_display,
        "currency": currency,
        "status": status,
        "basis": _basis_text(
            item, candidate_item, pricing_rules, historical_reference, discount
        ),
        "conditions": _conditions_for(item, decision),
        "notes": _notes_for(item, candidate_item, quote_request),
        **({"relation": relation} if relation is not None else {}),
    }


def _price_line(
    section_type: str,
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    quote_request: dict[str, Any],
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
    decision: str,
) -> tuple[float | None, str, str, str, str]:
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

    amount = _resolve_amount(
        section_type,
        item,
        candidate_item,
        quote_request,
        historical_reference,
        pricing_rules,
        currency,
    )
    if not isinstance(amount, (int, float)):
        return None, "pending", "pending", "pending", "Pending"

    numeric_amount = round(float(amount), 2)
    return (
        numeric_amount,
        "priced",
        "lump_sum",
        "chargeable",
        _format_amount(numeric_amount),
    )


def _resolve_amount(
    section_type: str,
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    quote_request: dict[str, Any],
    historical_reference: dict[str, Any],
    pricing_rules: dict[str, Any],
    currency: str,
) -> float | None:
    item_id = str(item.get("item_id") or "")
    service_rates = (
        pricing_rules.get("service_rates")
        if isinstance(pricing_rules.get("service_rates"), dict)
        else {}
    )
    lump_sum_overrides = (
        pricing_rules.get("lump_sum_overrides")
        if isinstance(pricing_rules.get("lump_sum_overrides"), dict)
        else {}
    )

    override = lump_sum_overrides.get(item_id)
    if isinstance(override, (int, float)):
        return float(override)

    workflow_amount = _workflow_charge_amount(
        section_type,
        item,
        candidate_item,
        quote_request,
        pricing_rules,
        historical_reference,
    )
    if workflow_amount is not None:
        return workflow_amount

    estimated_service_amount = _estimate_service_amount(
        candidate_item, quote_request, pricing_rules
    )
    if estimated_service_amount is not None:
        return estimated_service_amount

    if isinstance(service_rates.get(section_type), (int, float)):
        return float(service_rates[section_type])
    if isinstance(service_rates.get(str(item.get("item_type") or "")), (int, float)):
        return float(service_rates[str(item.get("item_type") or "")])

    historical_amount = _historical_mid_amount(historical_reference, currency)
    if historical_amount is not None and section_type == "service":
        return historical_amount

    return None


def _workflow_charge_amount(
    section_type: str,
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
    historical_reference: dict[str, Any],
) -> float | None:
    multipliers = _pricing_multipliers(pricing_rules)
    bases = _charge_bases(pricing_rules)
    item_text = " ".join(_candidate_texts(candidate_item)).lower()
    historical_charge_hints = _history_charge_item_hints(historical_reference)

    if section_type == "spare_parts":
        supply_mode = _spare_parts_supply_mode(quote_request)
        if supply_mode == "owner_supply":
            return None
        if any(
            keyword in item_text
            for keyword in ["freight", "运费", "air", "dhl", "delivery"]
        ):
            return round(bases["freight_base"] * multipliers["freight"], 2)
        if any(keyword in item_text for keyword in ["供船", "delivery", "agency"]):
            return round(bases["delivery_base"] * multipliers["delivery"], 2)
        if any(keyword in item_text for keyword in ["alternative", "替代"]):
            return round(
                bases["third_party_base"] * multipliers["spare_parts_alternative"], 2
            )
        return round(bases["third_party_base"] * multipliers["spare_parts_oem"], 2)

    if section_type == "other":
        quantity = _numeric_quantity(candidate_item.get("quantity_hint")) or 1.0
        if not _is_supported_other_charge(item_text, historical_charge_hints):
            return None
        if any(keyword in item_text for keyword in ["travel", "交通", "ticket"]):
            return round(
                bases["transportation_base"] * multipliers["boarding_travel"], 2
            )
        if any(
            keyword in item_text
            for keyword in ["hotel", "住宿", "accommodation", "meal", "食宿"]
        ):
            return round(bases["accommodation_daily"] * quantity, 2)
        if any(
            keyword in item_text for keyword in ["port service", "进港", "安全培训"]
        ):
            return round(
                bases["port_service_base"] * multipliers["dock_port_service"], 2
            )
        if any(
            keyword in item_text for keyword in ["maritime", "海事", "报备", "hot work"]
        ):
            return round(bases["maritime_reporting_base"], 2)
        if any(
            keyword in item_text
            for keyword in ["dockyard", "船厂管理", "management fee"]
        ):
            return round(
                bases["dockyard_management_base"] * multipliers["dockyard_management"],
                2,
            )
        if any(keyword in item_text for keyword in ["boarding", "上下船", "gangway"]):
            return round(
                bases["boarding_travel_base"] * multipliers["boarding_travel"], 2
            )

    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    if service_context.get("service_category") == "third_party":
        return round(bases["third_party_base"] * multipliers["third_party"], 2)

    if any(
        keyword in item_text for keyword in ["third party", "第三方", "maker service"]
    ):
        return round(bases["third_party_base"] * multipliers["third_party"], 2)

    return None


def _estimate_service_amount(
    candidate_item: dict[str, Any],
    quote_request: dict[str, Any],
    pricing_rules: dict[str, Any],
) -> float | None:
    if (
        not isinstance(candidate_item, dict)
        or candidate_item.get("item_type") != "service"
    ):
        return None

    hours = _extract_service_hours(candidate_item)
    if hours is None:
        return None

    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    discipline = _service_discipline(candidate_item, service_context)
    rate_catalog = _service_rate_catalog(pricing_rules)

    if discipline == "electrical":
        supervisor_count = (
            _extract_role_count(candidate_item, ["主管", "supervisor", "lead"]) or 1
        )
        assistant_count = (
            _extract_role_count(candidate_item, ["助理", "assistant"]) or 0
        )
        amount = (
            supervisor_count * rate_catalog["electrical_supervisor_hourly"] * hours
            + assistant_count * rate_catalog["electrical_assistant_hourly"] * hours
        )
        return round(amount, 2)

    supervisor_count = (
        _extract_role_count(candidate_item, ["主管", "supervisor", "chief"]) or 1
    )
    technician_count = (
        _extract_role_count(
            candidate_item, ["钳工", "焊工", "fitter", "welder", "technician"]
        )
        or 0
    )
    amount = (
        supervisor_count * rate_catalog["mechanical_supervisor_hourly"] * hours
        + technician_count * rate_catalog["mechanical_technician_hourly"] * hours
    )
    return round(amount, 2)


def _extract_service_hours(candidate_item: dict[str, Any]) -> float | None:
    texts = _candidate_texts(candidate_item)
    quantity_multiplier = _numeric_quantity(candidate_item.get("quantity_hint")) or 1.0
    combined = " ".join(texts)

    hour_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|小时)", combined, re.IGNORECASE
    )
    if hour_match:
        hours = float(hour_match.group(1))
        if "per unit" in combined.lower() or "each unit" in combined.lower():
            hours *= quantity_multiplier
        return hours

    day_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:days?|天)", combined, re.IGNORECASE)
    if day_match:
        hours = float(day_match.group(1)) * 8.0
        if "per unit" in combined.lower() or "each unit" in combined.lower():
            hours *= quantity_multiplier
        return hours

    return None


def _extract_role_count(candidate_item: dict[str, Any], keywords: list[str]) -> int:
    for text in _candidate_texts(candidate_item):
        lowered = text.lower()
        if not any(keyword.lower() in lowered for keyword in keywords):
            continue
        count_match = re.search(r"(\d+)", text)
        if count_match:
            return int(count_match.group(1))
        return 1
    return 0


def _service_discipline(
    candidate_item: dict[str, Any], service_context: dict[str, Any]
) -> str:
    explicit_category = (
        str(service_context.get("service_category") or "").strip().lower()
    )
    if explicit_category == "electrical":
        return "electrical"
    if explicit_category == "mechanical":
        return "mechanical"

    text = " ".join(_candidate_texts(candidate_item)).lower()
    electrical_keywords = ["electrical", "电气", "switchboard", "control", "automation"]
    if any(keyword in text for keyword in electrical_keywords):
        return "electrical"
    return "mechanical"


def _service_rate_catalog(pricing_rules: dict[str, Any]) -> dict[str, float]:
    service_rates = (
        pricing_rules.get("service_rates")
        if isinstance(pricing_rules.get("service_rates"), dict)
        else {}
    )
    catalog = dict(DEFAULT_SERVICE_RATES)
    for key in catalog:
        value = service_rates.get(key)
        if isinstance(value, (int, float)):
            catalog[key] = float(value)
    return catalog


def _resolve_discount_percentage(
    item: dict[str, Any],
    pricing_rules: dict[str, Any],
    option_strategy: dict[str, Any],
) -> float:
    discount_overrides = (
        pricing_rules.get("discount_overrides")
        if isinstance(pricing_rules.get("discount_overrides"), dict)
        else {}
    )
    override = discount_overrides.get(str(item.get("item_id") or ""))
    if isinstance(override, (int, float)) and override > 0:
        return round(float(override), 2)

    strategy_discount = option_strategy.get("discount_percentage")
    if isinstance(strategy_discount, (int, float)) and strategy_discount > 0:
        return round(float(strategy_discount), 2)
    return 0.0


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
                elif line["status"] != "excluded" and line["line_type"] not in {
                    "scope_note",
                    "technical_note",
                    "commercial_note",
                    "header",
                }:
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


def _build_option_remarks(
    pricing_rules: dict[str, Any],
    historical_reference: dict[str, Any],
    option_strategy: dict[str, Any],
) -> list[dict[str, Any]]:
    remarks = []
    seen: set[str] = set()

    remark_hints = (
        pricing_rules.get("remark_hints")
        if isinstance(pricing_rules.get("remark_hints"), list)
        else []
    )
    for text in remark_hints:
        cleaned = str(text).strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        remarks.append({"type": "commercial", "text": cleaned})

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
        remark_type = (
            str(block.get("remark_type") or "commercial").strip() or "commercial"
        )
        texts = block.get("texts") if isinstance(block.get("texts"), list) else []
        for text in texts[:2]:
            cleaned = str(text).strip()
            key = cleaned.lower()
            if not cleaned or key in seen:
                continue
            seen.add(key)
            remarks.append(
                {"type": _remark_type_for_output(remark_type), "text": cleaned}
            )

    remark_patterns = (
        reference_summary.get("remark_patterns")
        if isinstance(reference_summary.get("remark_patterns"), list)
        else []
    )
    for text in remark_patterns[:2]:
        cleaned = str(text).strip()
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        remarks.append({"type": "commercial", "text": cleaned})

    discount_percentage = option_strategy.get("discount_percentage")
    if isinstance(discount_percentage, (int, float)) and discount_percentage > 0:
        remarks.append(
            {
                "type": "commercial",
                "text": f"Commercial discount {_format_percentage(float(discount_percentage))} applied within operator authority.",
            }
        )
    if option_strategy.get("include_spare_parts") is False:
        remarks.append(
            {
                "type": "tbc",
                "text": "Spare parts are excluded from this option and remain subject to separate confirmation.",
            }
        )
    return remarks


def _basis_text(
    item: dict[str, Any],
    candidate_item: dict[str, Any],
    pricing_rules: dict[str, Any],
    historical_reference: dict[str, Any],
    discount: dict[str, Any] | None,
) -> str:
    item_id = str(item.get("item_id") or "")
    item_text = " ".join(_candidate_texts(candidate_item)).lower()
    if (
        isinstance(pricing_rules.get("lump_sum_overrides"), dict)
        and item_id in pricing_rules["lump_sum_overrides"]
    ):
        return "lump_sum_override"
    if any(keyword in item_text for keyword in ["travel", "交通", "hotel", "食宿"]):
        return "workflow_logistics_rule"
    if any(keyword in item_text for keyword in ["maritime", "海事", "报备"]):
        return "workflow_maritime_reporting_rule"
    if any(keyword in item_text for keyword in ["dockyard", "船厂管理"]):
        return "workflow_dockyard_management_rule"
    if any(keyword in item_text for keyword in ["third party", "第三方"]):
        return "workflow_third_party_rule"
    if _extract_service_hours(candidate_item) is not None:
        return "workflow_service_rate"
    if _historical_mid_amount(historical_reference, "") is not None:
        return "historical_price_range"
    if discount is not None:
        return "discount_authority"
    return "default_rule"


def _conditions_for(item: dict[str, Any], decision: str) -> list[str]:
    if decision == "tbc":
        return ["Subject to confirmation"]
    if decision == "excluded":
        return ["Not included in current quote scope"]
    if str(item.get("suggested_status") or "") == "if_needed":
        return ["Only chargeable if actually required during attendance"]
    return []


def _notes_for(
    item: dict[str, Any], candidate_item: dict[str, Any], quote_request: dict[str, Any]
) -> list[str]:
    notes = []
    reason = str(item.get("reason") or "").strip()
    if reason:
        notes.append(reason)

    candidate_description = str(candidate_item.get("description") or "").strip()
    if candidate_description:
        notes.append(candidate_description)

    item_title = str(item.get("title") or candidate_item.get("title") or "").strip()

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
            matched_confirmation = None
            if item_title:
                normalized_title = _normalize_match_text(item_title)
                for confirmation in pending_confirmations:
                    lowered_confirmation = _normalize_match_text(confirmation)
                    if normalized_title and normalized_title == lowered_confirmation:
                        matched_confirmation = confirmation
                        break
            notes.extend(
                [matched_confirmation]
                if matched_confirmation
                else pending_confirmations[:1]
            )

    return _dedupe_strings(notes)


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


def _historical_mid_amount(
    historical_reference: dict[str, Any], currency: str
) -> float | None:
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
    min_value = price_range_hint.get("min")
    max_value = price_range_hint.get("max")
    if isinstance(min_value, (int, float)) and isinstance(max_value, (int, float)):
        return round((float(min_value) + float(max_value)) / 2, 2)
    return None


def _candidate_item_lookup(quote_request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for key in ["candidate_items"]:
        items = quote_request.get(key)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and isinstance(item.get("item_id"), str):
                    lookup[item["item_id"]] = item

    spare_parts_context = (
        quote_request.get("spare_parts_context")
        if isinstance(quote_request.get("spare_parts_context"), dict)
        else {}
    )
    spare_parts_items = spare_parts_context.get("spare_parts_items")
    if isinstance(spare_parts_items, list):
        for item in spare_parts_items:
            if isinstance(item, dict) and isinstance(item.get("item_id"), str):
                lookup[item["item_id"]] = item
    return lookup


def _group_description(item: dict[str, Any], candidate_item: dict[str, Any]) -> str:
    reason = str(item.get("reason") or "").strip()
    if reason:
        return reason
    description = str(candidate_item.get("description") or "").strip()
    if description:
        return description
    return str(item.get("title") or "")


def _line_description(item: dict[str, Any], candidate_item: dict[str, Any]) -> str:
    title = str(item.get("title") or "").strip()
    description = str(candidate_item.get("description") or "").strip()
    if title and description:
        return f"{title} {description}".strip()
    return title or description


def _line_unit(candidate_item: dict[str, Any], pricing_mode: str) -> str:
    unit_hint = str(candidate_item.get("unit_hint") or "").strip()
    if unit_hint:
        return unit_hint
    if pricing_mode in {"lump_sum", "pending", "text_only"}:
        return "LS"
    return ""


def _line_qty(candidate_item: dict[str, Any], pricing_mode: str) -> int | float | None:
    quantity = _numeric_quantity(candidate_item.get("quantity_hint"))
    if quantity is not None:
        return quantity
    if pricing_mode in {"lump_sum", "unit_price"}:
        return 1
    return None


def _line_qty_display(candidate_item: dict[str, Any], pricing_mode: str) -> str:
    quantity = _line_qty(candidate_item, pricing_mode)
    if quantity is None:
        return ""
    if int(quantity) == quantity:
        return str(int(quantity))
    return str(quantity)


def _scope_note_lines(
    candidate_item: dict[str, Any], currency: str, item_id: str, option_id: str
) -> list[dict[str, Any]]:
    work_scope = candidate_item.get("work_scope")
    if not isinstance(work_scope, list):
        return []

    scope_lines = []
    for index, text in enumerate(work_scope, start=1):
        cleaned = str(text).strip()
        if not cleaned:
            continue
        scope_lines.append(
            {
                "line_id": f"{option_id}-line-{item_id}-scope-{index}",
                "item": "",
                "line_no": "",
                "line_type": "scope_note",
                "description": cleaned,
                "pricing_mode": "text_only",
                "unit_price": None,
                "unit_price_display": "",
                "unit": "",
                "qty": None,
                "qty_display": "",
                "discount": None,
                "amount": None,
                "amount_display": "",
                "currency": currency,
                "status": "chargeable",
                "basis": "included_scope",
                "conditions": [],
                "notes": [],
            }
        )
    return scope_lines


def _candidate_texts(candidate_item: dict[str, Any]) -> list[str]:
    values = [
        str(candidate_item.get("title") or "").strip(),
        str(candidate_item.get("description") or "").strip(),
    ]
    for key in ["work_scope", "labor_hint", "pricing_clues"]:
        raw = candidate_item.get(key)
        if isinstance(raw, list):
            values.extend(str(item).strip() for item in raw if str(item).strip())
    return [value for value in values if value]


def _numeric_quantity(value: Any) -> int | float | None:
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            numeric = float(stripped)
        except ValueError:
            return None
        return int(numeric) if numeric.is_integer() else numeric
    return None


def _default_discount_percentage(pricing_rules: dict[str, Any]) -> float:
    value = pricing_rules.get("default_discount_percentage")
    if isinstance(value, (int, float)) and value > 0:
        return round(float(value), 2)
    return DEFAULT_DISCOUNT_PERCENTAGE


def _history_option_style_hints(historical_reference: dict[str, Any]) -> set[str]:
    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
    option_style_hints = (
        reference_summary.get("option_style_hints")
        if isinstance(reference_summary.get("option_style_hints"), list)
        else []
    )
    result = set()
    for hint in option_style_hints:
        if isinstance(hint, dict):
            style_type = str(hint.get("style_type") or "").strip()
            if style_type:
                result.add(style_type)
    return result


def _history_charge_item_hints(historical_reference: dict[str, Any]) -> set[str]:
    reference_summary = (
        historical_reference.get("reference_summary")
        if isinstance(historical_reference.get("reference_summary"), dict)
        else {}
    )
    charge_item_hints = (
        reference_summary.get("charge_item_hints")
        if isinstance(reference_summary.get("charge_item_hints"), list)
        else []
    )
    result = set()
    for hint in charge_item_hints:
        if isinstance(hint, dict):
            hint_type = str(hint.get("hint_type") or "").strip()
            if hint_type:
                result.add(hint_type)
    return result


def _is_supported_other_charge(
    item_text: str, historical_charge_hints: set[str]
) -> bool:
    direct_mapping = {
        "transportation": ["travel", "交通", "ticket"],
        "accommodation": ["hotel", "住宿", "accommodation", "meal", "食宿"],
        "dockyard_management": ["dockyard", "船厂管理", "management fee"],
        "maritime_reporting": ["maritime", "海事", "报备", "hot work"],
    }
    for hint_type, keywords in direct_mapping.items():
        if hint_type in historical_charge_hints and any(
            keyword in item_text for keyword in keywords
        ):
            return True
    return any(
        keyword in item_text
        for keyword in [
            "travel",
            "交通",
            "hotel",
            "住宿",
            "dockyard",
            "船厂管理",
            "maritime",
            "海事",
            "报备",
        ]
    )


def _remark_type_for_output(remark_type: str) -> str:
    allowed_types = {
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
    }
    return remark_type if remark_type in allowed_types else "commercial"


def _pricing_multipliers(pricing_rules: dict[str, Any]) -> dict[str, float]:
    raw = (
        pricing_rules.get("pricing_multipliers")
        if isinstance(pricing_rules.get("pricing_multipliers"), dict)
        else {}
    )
    defaults = {
        "spare_parts_oem": 1.25,
        "spare_parts_alternative": 1.5,
        "freight": 1.35,
        "delivery": 1.35,
        "third_party": 1.4,
        "dock_port_service": 1.3,
        "dockyard_management": 1.2,
        "boarding_travel": 1.2,
    }
    for key, default in list(defaults.items()):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            defaults[key] = float(value)
    return defaults


def _charge_bases(pricing_rules: dict[str, Any]) -> dict[str, float]:
    raw = (
        pricing_rules.get("charge_bases")
        if isinstance(pricing_rules.get("charge_bases"), dict)
        else {}
    )
    defaults = {
        "third_party_base": 1200.0,
        "freight_base": 300.0,
        "delivery_base": 260.0,
        "transportation_base": 450.0,
        "accommodation_daily": 45.0,
        "port_service_base": 150.0,
        "maritime_reporting_base": 150.0,
        "dockyard_management_base": 200.0,
        "boarding_travel_base": 180.0,
    }
    for key, default in list(defaults.items()):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            defaults[key] = float(value)
    return defaults


def _spare_parts_supply_mode(quote_request: dict[str, Any]) -> str:
    spare_parts_context = (
        quote_request.get("spare_parts_context")
        if isinstance(quote_request.get("spare_parts_context"), dict)
        else {}
    )
    return str(spare_parts_context.get("spare_parts_supply_mode") or "").strip().lower()


def _section_title(section_type: str) -> str:
    return {
        "service": "Service",
        "spare_parts": "Spare Parts",
        "other": "Other",
    }.get(section_type, "Other")


def _format_amount(amount: float | None) -> str:
    if amount is None:
        return ""
    return f"{float(amount):,.2f}"


def _format_percentage(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value)}%"
    return f"{value:.2f}%"


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


def _normalize_match_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(cleaned.split())
