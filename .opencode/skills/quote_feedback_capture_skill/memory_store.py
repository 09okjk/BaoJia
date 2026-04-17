from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MEMORY_DIR = ROOT_DIR / ".opencode" / "memory"
PREFERENCE_ACTIVE_THRESHOLD = 2
RULE_REVIEW_READY_THRESHOLD = 3


def persist_feedback_memory(
    feedback_events: list[dict[str, Any]],
    preference_candidates: list[dict[str, Any]],
    rule_candidates: list[dict[str, Any]],
    case_memory_patch: dict[str, Any],
    memory_dir: str | Path | None = None,
) -> dict[str, Any]:
    target_dir = _resolve_memory_dir(memory_dir)
    feedback_dir = target_dir / "feedback-events"
    preference_dir = target_dir / "preference-memory"
    rule_dir = target_dir / "rule-candidates"
    case_dir = target_dir / "case-memory"

    written_files: list[str] = []

    for record in feedback_events:
        file_path, merged_record = _upsert_feedback_event(feedback_dir, record)
        _write_json(file_path, merged_record)
        written_files.append(str(file_path.resolve()))

    for record in preference_candidates:
        file_path, merged_record = _upsert_preference_candidate(preference_dir, record)
        _write_json(file_path, merged_record)
        written_files.append(str(file_path.resolve()))

    for record in rule_candidates:
        file_path, merged_record = _upsert_rule_candidate(rule_dir, record)
        _write_json(file_path, merged_record)
        written_files.append(str(file_path.resolve()))

    if case_memory_patch:
        case_id = _record_id(case_memory_patch, "quote_id", "case-memory")
        file_path = case_dir / f"{case_id}.json"
        existing = _load_json_if_exists(file_path)
        merged = _merge_case_memory(existing, case_memory_patch)
        _write_json(file_path, merged)
        written_files.append(str(file_path.resolve()))

    return {
        "memory_dir": str(target_dir.resolve()),
        "written_files": written_files,
        "feedback_events_written": len(feedback_events),
        "preference_candidates_written": len(preference_candidates),
        "rule_candidates_written": len(rule_candidates),
        "case_memory_written": bool(case_memory_patch),
    }


def _upsert_feedback_event(
    feedback_dir: Path, record: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    signature = _feedback_signature(record)
    existing_path, existing_record = _find_existing_record(
        feedback_dir, "feedback_signature", signature
    )
    if existing_path is None or not existing_record:
        new_record = dict(record)
        new_record["feedback_signature"] = signature
        new_record["evidence_count"] = 1
        new_record["observation_count"] = 1
        new_record["linked_quote_ids"] = _dedupe_strings(
            [_text(record.get("quote_id"))]
        )
        file_path = (
            feedback_dir
            / f"{_record_id(new_record, 'feedback_id', 'feedback-event')}.json"
        )
        return file_path, new_record

    merged = dict(existing_record)
    merged.setdefault("feedback_signature", signature)
    merged["evidence_count"] = int(existing_record.get("evidence_count") or 1) + 1
    merged["observation_count"] = int(existing_record.get("observation_count") or 1) + 1
    merged["linked_quote_ids"] = _merge_string_lists(
        existing_record.get("linked_quote_ids"), [_text(record.get("quote_id"))]
    )
    merged["last_seen_at"] = record.get("created_at")
    if record.get("accepted") is True:
        merged["accepted"] = True
    return existing_path, merged


def _upsert_preference_candidate(
    preference_dir: Path, record: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    aggregate_id = _preference_aggregate_id(record)
    file_path = preference_dir / f"{aggregate_id}.json"
    existing = _load_json_if_exists(file_path)
    if not existing:
        merged = dict(record)
        merged["preference_id"] = aggregate_id
        evidence_ids = (
            record.get("evidence_feedback_ids")
            if isinstance(record.get("evidence_feedback_ids"), list)
            else []
        )
        merged["evidence_feedback_ids"] = _merge_string_lists([], evidence_ids)
        merged["evidence_count"] = len(merged["evidence_feedback_ids"])
        merged["observation_count"] = 1
        merged["status"] = _preference_status(merged["observation_count"])
        merged["confidence"] = _preference_confidence(merged["observation_count"])
        return file_path, merged

    merged = dict(existing)
    merged["evidence_feedback_ids"] = _merge_string_lists(
        existing.get("evidence_feedback_ids"), record.get("evidence_feedback_ids")
    )
    merged["evidence_count"] = len(merged["evidence_feedback_ids"])
    merged["observation_count"] = int(existing.get("observation_count") or 1) + 1
    merged["status"] = _preference_status(merged["observation_count"])
    merged["confidence"] = _preference_confidence(merged["observation_count"])
    if isinstance(record.get("preference_value"), dict):
        merged["preference_value"] = record["preference_value"]
    return file_path, merged


def _upsert_rule_candidate(
    rule_dir: Path, record: dict[str, Any]
) -> tuple[Path, dict[str, Any]]:
    aggregate_id = _rule_aggregate_id(record)
    file_path = rule_dir / f"{aggregate_id}.json"
    existing = _load_json_if_exists(file_path)
    if not existing:
        merged = dict(record)
        merged["rule_candidate_id"] = aggregate_id
        evidence_ids = (
            record.get("evidence_feedback_ids")
            if isinstance(record.get("evidence_feedback_ids"), list)
            else []
        )
        merged["evidence_feedback_ids"] = _merge_string_lists([], evidence_ids)
        merged["evidence_count"] = len(merged["evidence_feedback_ids"])
        merged["observation_count"] = 1
        merged["status"] = _rule_status(merged["observation_count"])
        merged["confidence"] = _rule_confidence(merged["observation_count"])
        return file_path, merged

    merged = dict(existing)
    merged["evidence_feedback_ids"] = _merge_string_lists(
        existing.get("evidence_feedback_ids"), record.get("evidence_feedback_ids")
    )
    merged["evidence_count"] = len(merged["evidence_feedback_ids"])
    merged["observation_count"] = int(existing.get("observation_count") or 1) + 1
    merged["status"] = _rule_status(merged["observation_count"])
    merged["confidence"] = _rule_confidence(merged["observation_count"])
    if isinstance(record.get("proposed_rule"), dict):
        merged["proposed_rule"] = record["proposed_rule"]
    return file_path, merged


def _resolve_memory_dir(memory_dir: str | Path | None) -> Path:
    if isinstance(memory_dir, Path):
        return memory_dir.resolve()
    if isinstance(memory_dir, str) and memory_dir.strip():
        return (ROOT_DIR / memory_dir).resolve()
    return DEFAULT_MEMORY_DIR.resolve()


def _record_id(record: dict[str, Any], key: str, fallback_prefix: str) -> str:
    value = record.get(key)
    if isinstance(value, str) and value.strip():
        return _safe_filename(value)
    return _safe_filename(fallback_prefix)


def _merge_case_memory(
    existing: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    if not existing:
        merged = dict(patch)
        merged["observation_count"] = 1
        return merged
    merged = dict(existing)
    merged.update({key: value for key, value in patch.items() if key != "feedback_ids"})

    old_feedback_ids = (
        existing.get("feedback_ids")
        if isinstance(existing.get("feedback_ids"), list)
        else []
    )
    new_feedback_ids = (
        patch.get("feedback_ids") if isinstance(patch.get("feedback_ids"), list) else []
    )
    feedback_ids = []
    seen: set[str] = set()
    for item in [*old_feedback_ids, *new_feedback_ids]:
        if not isinstance(item, str):
            continue
        key = item.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        feedback_ids.append(key)
    merged["feedback_ids"] = feedback_ids
    merged["feedback_count"] = len(feedback_ids)
    merged["observation_count"] = int(existing.get("observation_count") or 1) + 1
    return merged


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _find_existing_record(
    directory: Path, key: str, expected: str
) -> tuple[Path | None, dict[str, Any]]:
    if not directory.exists() or not directory.is_dir() or not expected:
        return None, {}
    for path in directory.glob("*.json"):
        record = _load_json_if_exists(path)
        if _text(record.get(key)) == expected:
            return path, record
    return None, {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_filename(value: str) -> str:
    cleaned = value.strip().replace("/", "-").replace("\\", "-").replace(":", "-")
    cleaned = "-".join(part for part in cleaned.split() if part)
    return cleaned or "record"


def _feedback_signature(record: dict[str, Any]) -> str:
    target = record.get("target") if isinstance(record.get("target"), dict) else {}
    action = record.get("action") if isinstance(record.get("action"), dict) else {}
    reason = record.get("reason") if isinstance(record.get("reason"), dict) else {}
    scope = record.get("scope") if isinstance(record.get("scope"), dict) else {}
    parts = [
        _text(scope.get("scope_key")).lower(),
        _text(target.get("target_type")).lower(),
        _text(target.get("target_id")).lower(),
        _text(action.get("action_type")).lower(),
        _text(reason.get("reason_code")).lower(),
    ]
    return "|".join(parts)


def _preference_aggregate_id(record: dict[str, Any]) -> str:
    parts = [
        _text(record.get("scope_type")).lower(),
        _text(record.get("scope_key")).lower(),
        _text(record.get("preference_type")).lower(),
        _text(record.get("topic")).lower(),
        _text(record.get("pattern_key")).lower(),
    ]
    return _safe_filename("pref-agg-" + "-".join(parts))


def _rule_aggregate_id(record: dict[str, Any]) -> str:
    proposed_rule = (
        record.get("proposed_rule")
        if isinstance(record.get("proposed_rule"), dict)
        else {}
    )
    parts = [
        _text(record.get("scope_type")).lower(),
        _text(record.get("scope_key")).lower(),
        _text(record.get("candidate_type")).lower(),
        _text(proposed_rule.get("target_type")).lower(),
        _text(proposed_rule.get("target_id")).lower(),
        _text(proposed_rule.get("action_type")).lower(),
    ]
    return _safe_filename("rule-agg-" + "-".join(parts))


def _preference_status(evidence_count: int) -> str:
    return "active" if evidence_count >= PREFERENCE_ACTIVE_THRESHOLD else "candidate"


def _rule_status(evidence_count: int) -> str:
    return (
        "ready_for_review"
        if evidence_count >= RULE_REVIEW_READY_THRESHOLD
        else "pending_review"
    )


def _preference_confidence(evidence_count: int) -> float:
    return min(0.95, round(0.55 + 0.1 * max(0, evidence_count - 1), 2))


def _rule_confidence(evidence_count: int) -> float:
    return min(0.95, round(0.5 + 0.12 * max(0, evidence_count - 1), 2))


def _merge_string_lists(existing: Any, incoming: Any) -> list[str]:
    left = existing if isinstance(existing, list) else []
    right = incoming if isinstance(incoming, list) else []
    return _dedupe_strings(
        [
            *(item for item in left if isinstance(item, str)),
            *(item for item in right if isinstance(item, str)),
        ]
    )


def _dedupe_strings(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
