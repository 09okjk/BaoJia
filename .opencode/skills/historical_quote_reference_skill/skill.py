from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "historical_quotes.sample.json"


def build_historical_reference(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    quote_request = payload.get("quote_request")
    quotable_items = payload.get("quotable_items")
    if not isinstance(quote_request, dict):
        return _empty_reference_result()
    if not isinstance(quotable_items, list):
        quotable_items = []

    history_records = _load_history_records()
    if not history_records:
        return _empty_reference_result()

    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    header_context = (
        quote_request.get("header_context")
        if isinstance(quote_request.get("header_context"), dict)
        else {}
    )

    matches: list[dict[str, Any]] = []
    for record in history_records:
        match = _score_record(record, service_context, header_context, quotable_items)
        if match is not None:
            matches.append(match)

    matches.sort(key=lambda item: item["similarity"], reverse=True)
    top_matches = matches[:3]

    summary = _build_reference_summary(top_matches)
    confidence = _build_confidence(top_matches, quotable_items)

    return {
        "matches": top_matches,
        "reference_summary": summary,
        "confidence": confidence,
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


def _empty_reference_result() -> dict[str, Any]:
    return {
        "matches": [],
        "reference_summary": {
            "price_range_hint": {
                "currency": None,
                "min": None,
                "max": None,
                "sample_size": 0,
            },
            "common_items": [],
            "remark_patterns": [],
            "recommended_reference_ids": [],
        },
        "confidence": 0.0,
    }


def _load_history_records() -> list[dict[str, Any]]:
    if not DEFAULT_HISTORY_PATH.exists():
        return []
    data = json.loads(DEFAULT_HISTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _score_record(
    record: dict[str, Any],
    service_context: dict[str, Any],
    header_context: dict[str, Any],
    quotable_items: list[Any],
) -> dict[str, Any] | None:
    similarity = 0.0
    matched_features: list[str] = []

    if _match_text(
        record.get("service_category"), service_context.get("service_category")
    ):
        similarity += 0.15
        matched_features.append(f"service_category: {record.get('service_category')}")

    if _match_text(record.get("service_mode"), service_context.get("service_mode")):
        similarity += 0.30
        matched_features.append(f"service_mode: {record.get('service_mode')}")

    if _match_text(record.get("location_type"), service_context.get("location_type")):
        similarity += 0.20
        matched_features.append(f"location_type: {record.get('location_type')}")

    if _match_text(record.get("vessel_type"), header_context.get("vessel_type")):
        similarity += 0.10
        matched_features.append(f"vessel_type: {record.get('vessel_type')}")

    item_bonus = _item_similarity_bonus(record.get("items"), quotable_items)
    similarity += item_bonus["score"]
    matched_features.extend(item_bonus["features"])

    similarity = round(min(similarity, 1.0), 2)
    if similarity <= 0:
        return None

    return {
        "quote_id": str(record.get("quote_id") or ""),
        "similarity": similarity,
        "reason": _build_reason(matched_features),
        "matched_features": matched_features,
        "reference_items": _string_list(record.get("items")),
        "reference_remarks": _string_list(record.get("remarks")),
    }


def _item_similarity_bonus(
    record_items: Any, quotable_items: list[Any]
) -> dict[str, Any]:
    record_texts = [item.lower() for item in _string_list(record_items)]
    score = 0.0
    features: list[str] = []
    for item in quotable_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        lowered_title = title.lower()
        for record_text in record_texts:
            if lowered_title in record_text or record_text in lowered_title:
                score += 0.25
                features.append(f"item_title: {title}")
                break
            overlap = _token_overlap(lowered_title, record_text)
            if overlap >= 0.5:
                score += 0.15
                features.append(f"item_title: {title}")
                break
    return {
        "score": min(score, 0.40),
        "features": _dedupe_list(features),
    }


def _build_reason(matched_features: list[str]) -> str:
    if not matched_features:
        return "存在少量弱特征匹配。"
    if len(matched_features) >= 3:
        return "服务模式、地点类型和核心服务项高度相似。"
    if len(matched_features) == 2:
        return "存在多个关键特征匹配。"
    return "存在单个关键特征匹配。"


def _build_reference_summary(matches: list[dict[str, Any]]) -> dict[str, Any]:
    history_records = {record["quote_id"]: record for record in _load_history_records()}
    selected_records = [
        history_records[match["quote_id"]]
        for match in matches
        if match["quote_id"] in history_records
    ]

    currencies = _dedupe_list(
        [
            str(record.get("currency"))
            for record in selected_records
            if record.get("currency")
        ]
    )
    amounts = [
        float(record["total_amount"])
        for record in selected_records
        if isinstance(record.get("total_amount"), (int, float))
    ]

    common_items_counter: Counter[str] = Counter()
    remark_counter: Counter[str] = Counter()
    for record in selected_records:
        common_items_counter.update(_string_list(record.get("items")))
        remark_counter.update(_string_list(record.get("remarks")))

    return {
        "price_range_hint": {
            "currency": currencies[0] if currencies else None,
            "min": min(amounts) if amounts else None,
            "max": max(amounts) if amounts else None,
            "sample_size": len(amounts),
        },
        "common_items": [item for item, _ in common_items_counter.most_common(5)],
        "remark_patterns": [item for item, _ in remark_counter.most_common(5)],
        "recommended_reference_ids": [match["quote_id"] for match in matches],
    }


def _build_confidence(
    matches: list[dict[str, Any]], quotable_items: list[Any]
) -> float:
    if not matches:
        return 0.0
    top_similarity = matches[0]["similarity"]
    sample_bonus = min(len(matches) * 0.05, 0.15)
    quotable_penalty = 0.0 if quotable_items else 0.15
    confidence = max(0.0, min(top_similarity + sample_bonus - quotable_penalty, 1.0))
    return round(confidence, 2)


def _match_text(left: Any, right: Any) -> bool:
    if not left or not right:
        return False
    return str(left).strip().lower() == str(right).strip().lower()


def _token_overlap(left: str, right: str) -> float:
    left_tokens = {token for token in left.replace("-", " ").split() if token}
    right_tokens = {token for token in right.replace("-", " ").split() if token}
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
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
