from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parents[2]
DEFAULT_MEMORY_DIR = ROOT_DIR / ".opencode" / "memory"


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


def build_feedback_reference_result(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Feedback reference payload must be an object.")

    quote_request = payload.get("quote_request")
    if not isinstance(quote_request, dict):
        quote_request = {}
    feedback_context = payload.get("feedback_context")
    if not isinstance(feedback_context, dict):
        feedback_context = {}

    memory_dir = _memory_dir(payload)
    feedback_events = _load_json_records(memory_dir / "feedback-events")
    preference_records = _load_json_records(memory_dir / "preference-memory")
    approved_rules = _load_json_records(memory_dir / "approved-rules")

    query = _build_query_context(quote_request, feedback_context)
    matches = _match_feedback_events(feedback_events, query)
    applicable_preferences = _match_preferences(preference_records, query)
    applicable_rules = _match_approved_rules(approved_rules, query)
    forbidden_patterns = _build_forbidden_patterns(
        matches, applicable_preferences, applicable_rules
    )
    recommended_adjustments = _build_recommended_adjustments(
        matches, applicable_preferences, applicable_rules
    )
    review_alerts = _build_review_alerts(
        matches, applicable_preferences, applicable_rules
    )
    confidence = _confidence(matches, applicable_preferences, applicable_rules)

    return {
        "matches": matches,
        "applicable_preferences": applicable_preferences,
        "applicable_rules": applicable_rules,
        "forbidden_patterns": forbidden_patterns,
        "recommended_adjustments": recommended_adjustments,
        "review_alerts": review_alerts,
        "confidence": confidence,
    }


def _memory_dir(payload: dict[str, Any]) -> Path:
    feedback_context = payload.get("feedback_context")
    if isinstance(feedback_context, dict):
        raw = feedback_context.get("memory_dir")
        if isinstance(raw, str) and raw.strip():
            return (ROOT_DIR / raw).resolve()
    return DEFAULT_MEMORY_DIR


def _load_json_records(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists() or not directory.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def _build_query_context(
    quote_request: dict[str, Any], feedback_context: dict[str, Any]
) -> dict[str, str]:
    header_context = quote_request.get("header_context")
    if not isinstance(header_context, dict):
        header_context = {}
    service_context = quote_request.get("service_context")
    if not isinstance(service_context, dict):
        service_context = {}
    return {
        "customer_name": _text(
            feedback_context.get("customer_name") or header_context.get("customer_name")
        ),
        "sales_owner": _text(feedback_context.get("sales_owner")),
        "template_type": _text(
            feedback_context.get("template_type")
            or service_context.get("template_type")
            or "engineering-service"
        ),
        "service_mode": _text(service_context.get("service_mode")),
        "location_type": _text(service_context.get("location_type")),
        "vessel_type": _text(header_context.get("vessel_type")),
    }


def _match_feedback_events(
    feedback_events: list[dict[str, Any]], query: dict[str, str]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for event in feedback_events:
        score = _feedback_event_score(event, query)
        if score <= 0:
            continue
        matches.append(
            {
                "feedback_id": _text(event.get("feedback_id")),
                "score": round(score, 3),
                "reason": _feedback_match_reason(event, query),
                "target": event.get("target", {}),
                "action": event.get("action", {}),
                "scope": event.get("scope", {}),
                "reason_detail": event.get("reason", {}),
            }
        )
    matches.sort(key=lambda item: item.get("score", 0), reverse=True)
    return matches[:10]


def _feedback_event_score(event: dict[str, Any], query: dict[str, str]) -> float:
    score = 0.0
    scope = event.get("scope")
    if isinstance(scope, dict):
        scope_key = _text(scope.get("scope_key"))
        if query["customer_name"] and scope_key == _customer_scope_key(
            query["customer_name"]
        ):
            score += 0.55
        if query["sales_owner"] and scope_key == f"sales_owner:{query['sales_owner']}":
            score += 0.45
        if (
            query["template_type"]
            and scope_key == f"template_type:{query['template_type']}"
        ):
            score += 0.25
        if (
            query["service_mode"]
            and scope_key == f"service_pattern:{query['service_mode']}"
        ):
            score += 0.2

    context_tags = event.get("context_tags")
    if isinstance(context_tags, dict):
        if (
            _text(context_tags.get("service_mode")) == query["service_mode"]
            and query["service_mode"]
        ):
            score += 0.1
        if (
            _text(context_tags.get("location_type")) == query["location_type"]
            and query["location_type"]
        ):
            score += 0.05
        if (
            _text(context_tags.get("vessel_type")) == query["vessel_type"]
            and query["vessel_type"]
        ):
            score += 0.05

    if event.get("accepted") is True:
        score += 0.05
    return score


def _feedback_match_reason(event: dict[str, Any], query: dict[str, str]) -> str:
    scope = event.get("scope")
    scope_key = _text(scope.get("scope_key")) if isinstance(scope, dict) else ""
    if scope_key == _customer_scope_key(query["customer_name"]):
        return "matched customer-level feedback memory"
    if scope_key == f"sales_owner:{query['sales_owner']}":
        return "matched sales-owner-level feedback memory"
    if scope_key == f"template_type:{query['template_type']}":
        return "matched template-level feedback memory"
    if scope_key == f"service_pattern:{query['service_mode']}":
        return "matched service-pattern feedback memory"
    return "matched context-related feedback memory"


def _match_preferences(
    preference_records: list[dict[str, Any]], query: dict[str, str]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for record in preference_records:
        scope_type = _text(record.get("scope_type"))
        scope_key = _text(record.get("scope_key"))
        matched = False
        if scope_type == "customer" and scope_key == _customer_scope_key(
            query["customer_name"]
        ):
            matched = True
        elif (
            scope_type == "sales_owner"
            and scope_key == f"sales_owner:{query['sales_owner']}"
        ):
            matched = True
        elif (
            scope_type == "template_type"
            and scope_key == f"template_type:{query['template_type']}"
        ):
            matched = True
        elif (
            scope_type == "service_pattern"
            and scope_key == f"service_pattern:{query['service_mode']}"
        ):
            matched = True
        if not matched:
            continue
        matches.append(record)
    return matches[:10]


def _match_approved_rules(
    approved_rules: list[dict[str, Any]], query: dict[str, str]
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for record in approved_rules:
        scope_type = _text(record.get("scope_type"))
        scope_key = _text(record.get("scope_key"))
        condition = (
            record.get("condition") if isinstance(record.get("condition"), dict) else {}
        )
        matched = False
        if scope_type == "customer" and scope_key == _customer_scope_key(
            query["customer_name"]
        ):
            matched = True
        elif (
            scope_type == "template_type"
            and scope_key == f"template_type:{query['template_type']}"
        ):
            matched = True
        elif (
            scope_type == "service_pattern"
            and scope_key == f"service_pattern:{query['service_mode']}"
        ):
            matched = True
        if not matched:
            continue
        service_mode = _text(condition.get("service_mode"))
        template_type = _text(condition.get("template_type"))
        if service_mode and service_mode != query["service_mode"]:
            continue
        if template_type and template_type != query["template_type"]:
            continue
        matches.append(record)
    return matches[:10]


def _build_forbidden_patterns(
    matches: list[dict[str, Any]],
    applicable_preferences: list[dict[str, Any]],
    applicable_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in matches:
        action = match.get("action")
        target = match.get("target")
        if not isinstance(action, dict) or not isinstance(target, dict):
            continue
        if _text(action.get("action_type")) != "remove":
            continue
        key = _text(target.get("target_id"))
        if not key or key in seen:
            continue
        seen.add(key)
        patterns.append(
            {
                "pattern_type": _text(target.get("target_type")) or "line",
                "pattern_key": key,
                "reason": _text(match.get("reason")),
            }
        )
    for record in applicable_preferences:
        if _text(record.get("preference_type")) != "negative_pattern":
            continue
        key = _text(record.get("pattern_key"))
        if not key or key in seen:
            continue
        seen.add(key)
        patterns.append(
            {
                "pattern_type": _text(record.get("topic")) or "line",
                "pattern_key": key,
                "reason": _text(record.get("preference_value", {}).get("explanation"))
                if isinstance(record.get("preference_value"), dict)
                else "negative pattern preference",
            }
        )
    for record in applicable_rules:
        rule_action = (
            record.get("rule_action")
            if isinstance(record.get("rule_action"), dict)
            else {}
        )
        if _text(rule_action.get("action_type")) != "remove":
            continue
        key = _text(rule_action.get("target_id"))
        if not key or key in seen:
            continue
        seen.add(key)
        patterns.append(
            {
                "pattern_type": _text(rule_action.get("target_type")) or "line",
                "pattern_key": key,
                "reason": "matched approved rule",
            }
        )
    return patterns


def _build_recommended_adjustments(
    matches: list[dict[str, Any]],
    applicable_preferences: list[dict[str, Any]],
    applicable_rules: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    adjustments: list[dict[str, Any]] = []
    for match in matches[:5]:
        action = match.get("action")
        target = match.get("target")
        if not isinstance(action, dict) or not isinstance(target, dict):
            continue
        adjustments.append(
            {
                "adjustment_type": _text(action.get("action_type")) or "review",
                "target_type": _text(target.get("target_type")) or "line",
                "target_id": _text(target.get("target_id")),
                "reason": _text(match.get("reason")),
            }
        )
    for record in applicable_preferences[:5]:
        preference_value = record.get("preference_value")
        if not isinstance(preference_value, dict):
            continue
        adjustments.append(
            {
                "adjustment_type": _text(preference_value.get("default_action"))
                or "review",
                "target_type": _text(record.get("topic")) or "line",
                "target_id": _text(record.get("pattern_key")),
                "reason": _text(preference_value.get("explanation")),
            }
        )
    for record in applicable_rules[:5]:
        rule_action = (
            record.get("rule_action")
            if isinstance(record.get("rule_action"), dict)
            else {}
        )
        adjustments.append(
            {
                "adjustment_type": _text(rule_action.get("action_type")) or "review",
                "target_type": _text(rule_action.get("target_type")) or "line",
                "target_id": _text(rule_action.get("target_id")),
                "reason": "matched approved rule",
            }
        )
    return adjustments[:10]


def _build_review_alerts(
    matches: list[dict[str, Any]],
    applicable_preferences: list[dict[str, Any]],
    applicable_rules: list[dict[str, Any]],
) -> list[str]:
    alerts: list[str] = []
    for match in matches[:3]:
        target = match.get("target")
        target_id = (
            _text(target.get("target_id")) if isinstance(target, dict) else "unknown"
        )
        alerts.append(
            f"Past feedback suggests reviewing target '{target_id}' before finalizing this draft."
        )
    for record in applicable_preferences[:3]:
        topic = _text(record.get("topic")) or "draft element"
        alerts.append(
            f"Matched stored preference on '{topic}' for the current quote context."
        )
    for record in applicable_rules[:3]:
        rule_action = (
            record.get("rule_action")
            if isinstance(record.get("rule_action"), dict)
            else {}
        )
        target_id = _text(rule_action.get("target_id")) or "unknown"
        alerts.append(
            f"Matched approved rule for target '{target_id}' in the current quote context."
        )
    return _dedupe_strings(alerts)


def _confidence(
    matches: list[dict[str, Any]],
    applicable_preferences: list[dict[str, Any]],
    applicable_rules: list[dict[str, Any]],
) -> float:
    if not matches and not applicable_preferences and not applicable_rules:
        return 0.0
    top_match = matches[0]["score"] if matches else 0.0
    preference_bonus = min(0.25, len(applicable_preferences) * 0.05)
    approved_rule_bonus = min(0.35, len(applicable_rules) * 0.12)
    return round(min(1.0, top_match + preference_bonus + approved_rule_bonus), 3)


def _customer_scope_key(customer_name: str) -> str:
    if not customer_name:
        return ""
    return f"customer:{customer_name.lower().replace(' ', '-')}"


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(value.strip())
    return result


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
