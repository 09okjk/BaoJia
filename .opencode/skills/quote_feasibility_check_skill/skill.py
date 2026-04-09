from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_quote_feasibility(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_request = payload.get("quote_request")
    if not isinstance(quote_request, dict):
        return {
            "can_quote": False,
            "quote_scope": "not_ready",
            "quotable_items": [],
            "tbc_items": [],
            "exclusions": [],
            "missing_fields": [
                _missing_field(
                    field="quote_request",
                    required_for=["feasibility_check", "pricing"],
                    severity="high",
                    reason="缺少 quote_request，无法进行可报价判断。",
                    suggested_source="quote_request_prepare_skill",
                )
            ],
            "questions_for_user": [],
            "review_flags": [
                _review_flag(
                    flag_code="missing_quote_request",
                    severity="high",
                    message="缺少标准化报价请求对象，当前无法进入可报价判断。",
                    related_item_ids=[],
                )
            ],
        }

    candidate_items = quote_request.get("candidate_items")
    if not isinstance(candidate_items, list):
        candidate_items = []

    spare_parts_context = quote_request.get("spare_parts_context")
    if not isinstance(spare_parts_context, dict):
        spare_parts_context = {}

    header_context = quote_request.get("header_context")
    if not isinstance(header_context, dict):
        header_context = {}

    service_context = quote_request.get("service_context")
    if not isinstance(service_context, dict):
        service_context = {}

    quotable_items: list[dict[str, Any]] = []
    tbc_items: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    missing_fields: list[dict[str, Any]] = []
    questions_for_user: list[dict[str, Any]] = []
    review_flags: list[dict[str, Any]] = []

    _append_global_missing_fields(quote_request, missing_fields)

    for item in candidate_items:
        if not isinstance(item, dict):
            continue
        decision = _classify_item(item, quote_request)
        if decision["decision"] == "quotable":
            quotable_items.append(decision)
        elif decision["decision"] == "tbc":
            tbc_items.append(decision)
            for field in decision["blocking_fields"]:
                _append_missing_field_if_absent(
                    missing_fields,
                    _missing_field(
                        field=field,
                        required_for=["feasibility_check", "pricing"],
                        severity="medium",
                        reason=_missing_reason_for(field),
                        suggested_source=_suggested_source_for(field),
                    ),
                )
            generated_question = _question_for_tbc_item(decision, quote_request)
            if generated_question is not None:
                questions_for_user.append(generated_question)
        else:
            exclusions.append(decision)

    can_quote = bool(quotable_items)
    quote_scope = _determine_quote_scope(
        quotable_items, tbc_items, exclusions, candidate_items
    )

    if not candidate_items:
        review_flags.append(
            _review_flag(
                flag_code="no_candidate_items",
                severity="high",
                message="当前缺少候选报价项，无法进入稳定报价链路。",
                related_item_ids=[],
            )
        )

    if quote_scope == "partial":
        review_flags.append(
            _review_flag(
                flag_code="partial_quote_scope",
                severity="medium",
                message="当前仅部分项目具备报价条件。",
                related_item_ids=_related_ids(quotable_items + tbc_items + exclusions),
            )
        )
    elif quote_scope == "not_ready":
        review_flags.append(
            _review_flag(
                flag_code="quote_not_ready",
                severity="high",
                message="当前关键条件不足，暂不建议进入正式报价。",
                related_item_ids=_related_ids(tbc_items + exclusions),
            )
        )

    if tbc_items and len(tbc_items) >= len(candidate_items) and candidate_items:
        review_flags.append(
            _review_flag(
                flag_code="majority_items_tbc",
                severity="medium",
                message="当前多数项目仍处于待确认状态。",
                related_item_ids=_related_ids(tbc_items),
            )
        )

    if _is_blank(service_context.get("service_mode")) or _is_blank(
        header_context.get("service_port")
    ):
        review_flags.append(
            _review_flag(
                flag_code="critical_context_missing",
                severity="high",
                message="服务模式或服务地点等关键上下文缺失，影响可报价判断稳定性。",
                related_item_ids=[],
            )
        )

    return {
        "can_quote": can_quote,
        "quote_scope": quote_scope,
        "quotable_items": quotable_items,
        "tbc_items": tbc_items,
        "exclusions": exclusions,
        "missing_fields": _dedupe_missing_fields(missing_fields),
        "questions_for_user": _dedupe_questions(questions_for_user),
        "review_flags": _dedupe_review_flags(review_flags),
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


def _classify_item(
    item: dict[str, Any], quote_request: dict[str, Any]
) -> dict[str, Any]:
    item_id = str(item.get("item_id") or "")
    item_type = str(item.get("item_type") or "other")
    title = str(item.get("title") or "")
    work_scope = (
        item.get("work_scope") if isinstance(item.get("work_scope"), list) else []
    )
    status_hint = str(item.get("status_hint") or "").strip().lower()
    spare_parts_context = quote_request.get("spare_parts_context")
    if not isinstance(spare_parts_context, dict):
        spare_parts_context = {}

    if status_hint in {"excluded", "by_owner"}:
        return _decision_item(
            item_id=item_id,
            item_type=item_type,
            title=title,
            decision="excluded",
            reason="输入已明确该项不纳入当前报价范围。",
            blocking_fields=[],
            suggested_status="excluded" if status_hint == "excluded" else "by_owner",
        )

    if item_type == "spare_parts":
        supply_mode = spare_parts_context.get("spare_parts_supply_mode")
        if _is_blank(supply_mode):
            return _decision_item(
                item_id=item_id,
                item_type=item_type,
                title=title,
                decision="tbc",
                reason="备件供货责任未确认，当前只能待确认。",
                blocking_fields=["spare_parts_context.spare_parts_supply_mode"],
                suggested_status="pending",
            )
        if str(supply_mode).strip().lower() == "owner_supply":
            return _decision_item(
                item_id=item_id,
                item_type=item_type,
                title=title,
                decision="excluded",
                reason="备件已明确由船东提供，当前不纳入我司供货报价。",
                blocking_fields=[],
                suggested_status="by_owner",
            )

    if _is_blank(title):
        return _decision_item(
            item_id=item_id,
            item_type=item_type,
            title=title,
            decision="tbc",
            reason="项目标题缺失，无法稳定判断报价范围。",
            blocking_fields=["candidate_items.title"],
            suggested_status="pending",
        )

    if not work_scope:
        return _decision_item(
            item_id=item_id,
            item_type=item_type,
            title=title,
            decision="tbc",
            reason="工作范围不明确，当前只能待确认。",
            blocking_fields=[f"candidate_items[{item_id}].work_scope"],
            suggested_status="pending",
        )

    return _decision_item(
        item_id=item_id,
        item_type=item_type,
        title=title,
        decision="quotable",
        reason="服务项标题和范围已基本明确，可进入报价。",
        blocking_fields=[],
        suggested_status="chargeable",
    )


def _append_global_missing_fields(
    quote_request: dict[str, Any], missing_fields: list[dict[str, Any]]
) -> None:
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )
    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    candidate_items = (
        quote_request.get("candidate_items")
        if isinstance(quote_request.get("candidate_items"), list)
        else []
    )

    if not candidate_items:
        missing_fields.append(
            _missing_field(
                field="candidate_items",
                required_for=["feasibility_check", "pricing"],
                severity="high",
                reason="缺少候选报价项，无法做稳定的可报价判断。",
                suggested_source="quote_request_prepare_skill",
            )
        )
    if _is_blank(service_context.get("service_mode")):
        missing_fields.append(
            _missing_field(
                field="service_context.service_mode",
                required_for=["feasibility_check", "pricing"],
                severity="medium",
                reason="缺少服务模式，影响是否可报价及后续定价。",
                suggested_source="business_context",
            )
        )
    if _is_blank(header_context.get("service_port")):
        missing_fields.append(
            _missing_field(
                field="header_context.service_port",
                required_for=["feasibility_check", "pricing", "quote_document"],
                severity="high",
                reason="缺少服务地点，影响场景判断和后续费用判断。",
                suggested_source="customer_context",
            )
        )


def _determine_quote_scope(
    quotable_items: list[dict[str, Any]],
    tbc_items: list[dict[str, Any]],
    exclusions: list[dict[str, Any]],
    candidate_items: list[Any],
) -> str:
    if not candidate_items or not quotable_items:
        return "not_ready"
    if tbc_items or exclusions:
        return "partial"
    return "full"


def _question_for_tbc_item(
    item: dict[str, Any], quote_request: dict[str, Any]
) -> dict[str, Any] | None:
    blocking_fields = (
        item.get("blocking_fields")
        if isinstance(item.get("blocking_fields"), list)
        else []
    )
    if "spare_parts_context.spare_parts_supply_mode" in blocking_fields:
        return {
            "question_id": f"q-{item['item_id']}",
            "target": "customer",
            "topic": "spare_parts_supply_mode",
            "question": f"{item['title']} 由船东提供还是由我司供货？",
            "related_item_ids": [item["item_id"]],
        }
    if any(field.endswith("work_scope") for field in blocking_fields):
        return {
            "question_id": f"q-{item['item_id']}",
            "target": "customer",
            "topic": "work_scope",
            "question": f"请进一步确认 {item['title']} 的具体工作范围是否已完整列明。",
            "related_item_ids": [item["item_id"]],
        }
    return None


def _missing_reason_for(field: str) -> str:
    if field == "spare_parts_context.spare_parts_supply_mode":
        return "备件供货责任未确认，影响是否纳入报价。"
    if field == "service_context.service_mode":
        return "服务模式未确认，影响可报价判断。"
    if field == "header_context.service_port":
        return "服务地点未确认，影响可报价判断和后续费用估算。"
    if ".work_scope" in field:
        return "项目工作范围未确认，当前无法稳定报价。"
    return "存在影响可报价判断的关键缺失信息。"


def _suggested_source_for(field: str) -> str:
    if field == "spare_parts_context.spare_parts_supply_mode":
        return "customer_context"
    if field == "service_context.service_mode":
        return "business_context"
    if field == "header_context.service_port":
        return "customer_context"
    if ".work_scope" in field:
        return "assessment_report"
    return "quote_request_prepare_skill"


def _decision_item(
    item_id: str,
    item_type: str,
    title: str,
    decision: str,
    reason: str,
    blocking_fields: list[str],
    suggested_status: str,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "item_type": item_type
        if item_type in {"service", "spare_parts", "other"}
        else "other",
        "title": title,
        "decision": decision,
        "reason": reason,
        "blocking_fields": blocking_fields,
        "suggested_status": suggested_status,
        "source": "quote_request.candidate_items",
    }


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


def _review_flag(
    flag_code: str,
    severity: str,
    message: str,
    related_item_ids: list[str],
) -> dict[str, Any]:
    return {
        "flag_code": flag_code,
        "severity": severity,
        "message": message,
        "related_item_ids": related_item_ids,
    }


def _append_missing_field_if_absent(
    target: list[dict[str, Any]], item: dict[str, Any]
) -> None:
    key = (item["field"], item["severity"])
    for existing in target:
        if (existing["field"], existing["severity"]) == key:
            return
    target.append(item)


def _dedupe_missing_fields(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item["field"], item["severity"])
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_questions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = item["question_id"]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _dedupe_review_flags(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        key = item["flag_code"]
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _related_ids(items: list[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        item_id = str(item.get("item_id") or "")
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        result.append(item_id)
    return result


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return len(value) == 0
    return False
