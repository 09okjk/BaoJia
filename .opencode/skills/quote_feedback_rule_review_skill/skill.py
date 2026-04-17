from __future__ import annotations

import json
from datetime import datetime, timezone
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


def review_rule_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Rule review payload must be an object.")

    memory_dir = _resolve_memory_dir(payload.get("memory_dir"))
    candidate_id = _text(payload.get("rule_candidate_id"))
    decision = _text(payload.get("decision")).lower() or "approve"
    reviewer = (
        payload.get("reviewer") if isinstance(payload.get("reviewer"), dict) else {}
    )
    review_note = _text(payload.get("review_note"))

    candidate_path = memory_dir / "rule-candidates" / f"{candidate_id}.json"
    candidate = _load_json_if_exists(candidate_path)
    if not candidate:
        raise ValueError(f"Rule candidate not found: {candidate_id}")

    review_time = _now_iso()
    updated_candidate = dict(candidate)
    updated_candidate["reviewed_at"] = review_time
    updated_candidate["reviewed_by"] = (
        _text(reviewer.get("user_id")) or "unknown_reviewer"
    )
    updated_candidate["review_note"] = review_note

    approved_rule = {}
    approved_rule_path = None
    if decision == "approve":
        updated_candidate["status"] = "approved"
        approved_rule = _build_approved_rule(
            updated_candidate, reviewer, review_note, review_time
        )
        approved_rule_path = (
            memory_dir / "approved-rules" / f"{approved_rule['approved_rule_id']}.json"
        )
        _write_json(approved_rule_path, approved_rule)
    elif decision == "reject":
        updated_candidate["status"] = "rejected"
    else:
        raise ValueError("decision must be 'approve' or 'reject'")

    _write_json(candidate_path, updated_candidate)

    return {
        "rule_candidate": updated_candidate,
        "approved_rule": approved_rule,
        "memory_write_result": {
            "memory_dir": str(memory_dir.resolve()),
            "candidate_path": str(candidate_path.resolve()),
            "approved_rule_path": str(approved_rule_path.resolve())
            if approved_rule_path
            else None,
            "decision": decision,
        },
    }


def _build_approved_rule(
    candidate: dict[str, Any],
    reviewer: dict[str, Any],
    review_note: str,
    review_time: str,
) -> dict[str, Any]:
    proposed_rule = (
        candidate.get("proposed_rule")
        if isinstance(candidate.get("proposed_rule"), dict)
        else {}
    )
    approved_rule_id = f"approved-{_text(candidate.get('rule_candidate_id'))}"
    return {
        "approved_rule_id": approved_rule_id,
        "source_rule_candidate_id": _text(candidate.get("rule_candidate_id")),
        "candidate_type": _text(candidate.get("candidate_type")),
        "scope_type": _text(candidate.get("scope_type")),
        "scope_key": _text(candidate.get("scope_key")),
        "condition": candidate.get("condition", {}),
        "rule_action": {
            "target_type": _text(proposed_rule.get("target_type")),
            "target_id": _text(proposed_rule.get("target_id")),
            "action_type": _text(proposed_rule.get("action_type")),
        },
        "evidence_feedback_ids": candidate.get("evidence_feedback_ids", []),
        "observation_count": candidate.get("observation_count", 0),
        "confidence": candidate.get("confidence", 0),
        "approved_by": _text(reviewer.get("user_id")) or "unknown_reviewer",
        "approved_at": review_time,
        "review_note": review_note,
        "status": "active",
    }


def _resolve_memory_dir(raw: Any) -> Path:
    if isinstance(raw, str) and raw.strip():
        return (ROOT_DIR / raw).resolve()
    return DEFAULT_MEMORY_DIR.resolve()


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
