from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from memory_store import persist_feedback_memory


BASE_DIR = Path(__file__).resolve().parent


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be an object.")
    return data


def dump_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_feedback_capture_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Feedback capture payload must be an object.")

    quote_context = payload.get("quote_context")
    if not isinstance(quote_context, dict):
        quote_context = {}
    quote_request = quote_context.get("quote_request")
    if not isinstance(quote_request, dict):
        quote_request = {}
    quote_document = quote_context.get("quote_document")
    if not isinstance(quote_document, dict):
        quote_document = {}

    actor = payload.get("feedback_actor")
    if not isinstance(actor, dict):
        actor = {}
    memory_options = payload.get("memory_options")
    if not isinstance(memory_options, dict):
        memory_options = {}

    raw_feedback = payload.get("user_feedback")
    feedback_items = raw_feedback if isinstance(raw_feedback, list) else []

    feedback_events: list[dict[str, Any]] = []
    preference_candidates: list[dict[str, Any]] = []
    rule_candidates: list[dict[str, Any]] = []
    review_flags: list[str] = []

    quote_id = _quote_id(quote_context, quote_document)
    quote_version = str(quote_context.get("quote_version") or "draft-v1")
    context_tags = _context_tags(quote_request)

    for index, item in enumerate(feedback_items, start=1):
        if not isinstance(item, dict):
            review_flags.append(
                f"feedback item {index} skipped because it is not an object"
            )
            continue
        event = _build_feedback_event(
            item=item,
            index=index,
            quote_id=quote_id,
            quote_version=quote_version,
            context_tags=context_tags,
            actor=actor,
        )
        feedback_events.append(event)

        preference_candidate = _build_preference_candidate(event)
        if preference_candidate is not None:
            preference_candidates.append(preference_candidate)

        rule_candidate = _build_rule_candidate(event)
        if rule_candidate is not None:
            rule_candidates.append(rule_candidate)

    case_memory_patch = {
        "quote_id": quote_id,
        "quote_version": quote_version,
        "feedback_ids": [event["feedback_id"] for event in feedback_events],
        "feedback_count": len(feedback_events),
        "latest_feedback_at": _now_iso() if feedback_events else None,
    }

    write_result = {
        "enabled": False,
        "memory_dir": None,
        "written_files": [],
        "feedback_events_written": 0,
        "preference_candidates_written": 0,
        "rule_candidates_written": 0,
        "case_memory_written": False,
    }
    if memory_options.get("persist") is True and feedback_events:
        write_result = {
            "enabled": True,
            **persist_feedback_memory(
                feedback_events=feedback_events,
                preference_candidates=preference_candidates,
                rule_candidates=rule_candidates,
                case_memory_patch=case_memory_patch,
                memory_dir=memory_options.get("memory_dir"),
            ),
        }

    return {
        "feedback_events": feedback_events,
        "case_memory_patch": case_memory_patch,
        "preference_candidates": preference_candidates,
        "rule_candidates": rule_candidates,
        "review_flags": review_flags,
        "memory_write_result": write_result,
    }


def _build_feedback_event(
    item: dict[str, Any],
    index: int,
    quote_id: str,
    quote_version: str,
    context_tags: dict[str, Any],
    actor: dict[str, Any],
) -> dict[str, Any]:
    target_type = _text(item.get("target_type")) or "line"
    target_id = _text(item.get("target_id")) or f"unknown-target-{index}"
    stage = _text(item.get("stage")) or _default_stage(target_type)
    action_type = _text(item.get("action_type")) or "replace"
    reason_text = _text(item.get("reason_text")) or "No detailed reason provided."
    reason_code = _text(item.get("reason_code")) or _infer_reason_code(
        action_type, reason_text
    )
    scope_type = _text(item.get("scope_type")) or "this_quote_only"
    scope_key = _scope_key(scope_type, actor, context_tags)
    feedback_id = f"fb-{quote_id}-{index:03d}"

    return {
        "feedback_id": feedback_id,
        "quote_id": quote_id,
        "quote_version": quote_version,
        "target": {
            "target_type": target_type,
            "target_id": target_id,
            "stage": stage,
        },
        "action": {
            "action_type": action_type,
            "before_value": item.get("before_value"),
            "after_value": item.get("after_value"),
        },
        "reason": {
            "reason_code": reason_code,
            "reason_text": reason_text,
        },
        "scope": {
            "scope_type": scope_type,
            "scope_key": scope_key,
        },
        "context_tags": context_tags,
        "accepted": bool(item.get("accepted", True)),
        "created_by": _text(actor.get("user_id")) or "unknown_user",
        "created_at": _now_iso(),
    }


def _build_preference_candidate(event: dict[str, Any]) -> dict[str, Any] | None:
    scope = event.get("scope")
    reason = event.get("reason")
    target = event.get("target")
    action = event.get("action")
    if not isinstance(scope, dict) or not isinstance(reason, dict):
        return None
    scope_type = _text(scope.get("scope_type"))
    if scope_type not in {
        "customer",
        "sales_owner",
        "template_type",
        "service_pattern",
    }:
        return None

    preference_type = "negative_pattern"
    action_type = _text(action.get("action_type")) if isinstance(action, dict) else ""
    if action_type in {"replace", "change_text", "change_amount"}:
        preference_type = "soft_preference"

    return {
        "preference_id": f"pref-{event['feedback_id']}",
        "scope_type": scope_type,
        "scope_key": _text(scope.get("scope_key")),
        "preference_type": preference_type,
        "topic": _text(target.get("target_type"))
        if isinstance(target, dict)
        else "unknown",
        "pattern_key": _text(target.get("target_id"))
        if isinstance(target, dict)
        else "unknown",
        "preference_value": {
            "default_action": action_type or "review",
            "explanation": _text(reason.get("reason_text")),
        },
        "evidence_feedback_ids": [event["feedback_id"]],
        "confidence": 0.6,
        "status": "candidate",
    }


def _build_rule_candidate(event: dict[str, Any]) -> dict[str, Any] | None:
    scope = event.get("scope")
    target = event.get("target")
    action = event.get("action")
    if (
        not isinstance(scope, dict)
        or not isinstance(target, dict)
        or not isinstance(action, dict)
    ):
        return None
    scope_type = _text(scope.get("scope_type"))
    if scope_type not in {
        "customer",
        "template_type",
        "service_pattern",
        "global_candidate",
    }:
        return None

    return {
        "rule_candidate_id": f"rule-{event['feedback_id']}",
        "candidate_type": _rule_candidate_type(
            _text(target.get("target_type")), _text(action.get("action_type"))
        ),
        "scope_type": scope_type,
        "scope_key": _text(scope.get("scope_key")),
        "condition": {
            "service_mode": event.get("context_tags", {}).get("service_mode"),
            "template_type": event.get("context_tags", {}).get("template_type"),
        },
        "proposed_rule": {
            "target_type": _text(target.get("target_type")),
            "target_id": _text(target.get("target_id")),
            "action_type": _text(action.get("action_type")),
        },
        "evidence_feedback_ids": [event["feedback_id"]],
        "confidence": 0.55,
        "status": "pending_review",
    }


def _quote_id(quote_context: dict[str, Any], quote_document: dict[str, Any]) -> str:
    direct = _text(quote_context.get("quote_id"))
    if direct:
        return direct
    header = quote_document.get("header")
    if isinstance(header, dict):
        wk_offer_no = _text(header.get("wk_offer_no"))
        if wk_offer_no:
            return wk_offer_no
    return f"quote-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _context_tags(quote_request: dict[str, Any]) -> dict[str, Any]:
    header_context = quote_request.get("header_context")
    if not isinstance(header_context, dict):
        header_context = {}
    service_context = quote_request.get("service_context")
    if not isinstance(service_context, dict):
        service_context = {}
    return {
        "customer_name": header_context.get("customer_name"),
        "vessel_type": header_context.get("vessel_type"),
        "service_port": header_context.get("service_port"),
        "service_mode": service_context.get("service_mode"),
        "location_type": service_context.get("location_type"),
        "template_type": service_context.get("template_type") or "engineering-service",
    }


def _scope_key(
    scope_type: str, actor: dict[str, Any], context_tags: dict[str, Any]
) -> str:
    if scope_type == "customer":
        customer_name = _text(context_tags.get("customer_name")) or "unknown-customer"
        return f"customer:{customer_name.lower().replace(' ', '-')}"
    if scope_type == "sales_owner":
        user_id = _text(actor.get("user_id")) or "unknown-user"
        return f"sales_owner:{user_id}"
    if scope_type == "template_type":
        template_type = (
            _text(context_tags.get("template_type")) or "engineering-service"
        )
        return f"template_type:{template_type}"
    if scope_type == "service_pattern":
        service_mode = _text(context_tags.get("service_mode")) or "unknown-service-mode"
        return f"service_pattern:{service_mode}"
    if scope_type == "global_candidate":
        return "global_candidate:all"
    return "this_quote_only"


def _default_stage(target_type: str) -> str:
    if target_type in {"line", "option", "section", "group"}:
        return "pricing"
    if target_type in {"footer_remark", "payment_term", "review_flag"}:
        return "review_output"
    return "prepare"


def _infer_reason_code(action_type: str, reason_text: str) -> str:
    lowered = reason_text.lower()
    if "customer" in lowered:
        return "customer_preference"
    if "history" in lowered or "historical" in lowered:
        return "historical_noise"
    if action_type in {"mark_pending", "mark_owner_supply"}:
        return "should_be_pending"
    if action_type == "change_amount":
        return "pricing_too_high"
    if action_type == "remove":
        return "not_applicable"
    return "business_preference"


def _rule_candidate_type(target_type: str, action_type: str) -> str:
    if target_type == "footer_remark":
        return "remark_filter"
    if target_type == "payment_term":
        return "payment_term_template"
    if action_type == "remove":
        return "line_suppression"
    return "draft_preference"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
