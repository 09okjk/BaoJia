from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "historical_quotes.sample.json"

REMARK_TYPE_RULES = {
    "warranty": ["warranty", "guarantee", "质保", "保修"],
    "waiting": ["waiting", "delay", "standby", "等待"],
    "safety": ["safety", "safe", "安全"],
    "payment_term": ["payment", "invoice", "付款"],
    "exclusion": ["exclude", "excluded", "not included", "不含", "除外"],
}

CHARGE_ITEM_RULES = {
    "transportation": ["transport", "travel", "ticket", "交通"],
    "accommodation": ["hotel", "accommodation", "meal", "食宿", "住宿"],
    "dockyard_management": ["dockyard", "shipyard", "management fee", "厂修管理"],
    "maritime_reporting": ["maritime", "permit", "reporting", "报备", "动火"],
    "freight": ["freight", "air freight", "运费"],
    "delivery": ["delivery", "agency", "供船"],
}

OPTION_STYLE_RULES = {
    "standard_vs_discount": ["discount", "折扣"],
    "service_only": ["service only", "labor only", "without spares"],
    "owner_supply_spares": ["shipside", "owner supply", "owner supplied"],
    "spares_tbc": ["tbc", "to be confirmed", "subject to confirmation"],
}


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

    summary = _build_reference_summary(top_matches, quotable_items)
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
            "item_clusters": [],
            "remark_blocks": [],
            "charge_item_hints": [],
            "option_style_hints": [],
            "history_quality_flags": [],
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


def _build_reference_summary(
    matches: list[dict[str, Any]], quotable_items: list[Any]
) -> dict[str, Any]:
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
    all_items: list[str] = []
    all_remarks: list[str] = []
    for record in selected_records:
        record_items = _string_list(record.get("items"))
        record_remarks = _string_list(record.get("remarks"))
        common_items_counter.update(record_items)
        remark_counter.update(record_remarks)
        all_items.extend(record_items)
        all_remarks.extend(record_remarks)

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
        "item_clusters": _build_item_clusters(all_items),
        "remark_blocks": _build_remark_blocks(all_remarks),
        "charge_item_hints": _build_charge_item_hints(all_items, all_remarks),
        "option_style_hints": _build_option_style_hints(all_items, all_remarks),
        "history_quality_flags": _build_history_quality_flags(
            matches, amounts, quotable_items
        ),
    }


def _build_item_clusters(items: list[str]) -> list[dict[str, Any]]:
    counters: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for item in items:
        cluster_key = _cluster_key(item)
        if not cluster_key:
            continue
        counters[cluster_key] += 1
        examples.setdefault(cluster_key, [])
        if item not in examples[cluster_key] and len(examples[cluster_key]) < 3:
            examples[cluster_key].append(item)

    result = []
    for cluster_key, count in counters.most_common(5):
        result.append(
            {
                "cluster_key": cluster_key,
                "sample_size": count,
                "examples": examples.get(cluster_key, []),
            }
        )
    return result


def _build_remark_blocks(remarks: list[str]) -> list[dict[str, Any]]:
    grouped: dict[str, Counter[str]] = {}
    for remark in remarks:
        remark_type = _remark_type(remark)
        grouped.setdefault(remark_type, Counter())
        grouped[remark_type][remark] += 1

    result = []
    for remark_type, counter in grouped.items():
        most_common = counter.most_common(3)
        result.append(
            {
                "remark_type": remark_type,
                "texts": [text for text, _ in most_common],
                "sample_size": sum(counter.values()),
            }
        )
    result.sort(key=lambda item: item["sample_size"], reverse=True)
    return result


def _build_charge_item_hints(
    items: list[str], remarks: list[str]
) -> list[dict[str, Any]]:
    source_texts = items + remarks
    result = []
    for hint_type, keywords in CHARGE_ITEM_RULES.items():
        matches = _matched_texts(source_texts, keywords)
        if not matches:
            continue
        result.append(
            {
                "hint_type": hint_type,
                "source": "history_text",
                "sample_size": len(matches),
                "examples": matches[:3],
            }
        )
    return result


def _build_option_style_hints(
    items: list[str], remarks: list[str]
) -> list[dict[str, Any]]:
    source_texts = items + remarks
    result = []
    for style_type, keywords in OPTION_STYLE_RULES.items():
        matches = _matched_texts(source_texts, keywords)
        if not matches:
            continue
        result.append(
            {
                "style_type": style_type,
                "source": "history_text",
                "sample_size": len(matches),
                "examples": matches[:3],
            }
        )
    return result


def _build_history_quality_flags(
    matches: list[dict[str, Any]], amounts: list[float], quotable_items: list[Any]
) -> list[str]:
    flags: list[str] = []
    if len(matches) < 2:
        flags.append("low_sample_size")
    if matches and matches[0]["similarity"] < 0.5:
        flags.append("weak_top_match")
    if quotable_items and not any(
        any(
            feature.startswith("item_title:")
            for feature in match.get("matched_features", [])
        )
        for match in matches
        if isinstance(match, dict)
    ):
        flags.append("weak_item_overlap")
    if len(amounts) >= 2 and min(amounts) > 0 and max(amounts) / min(amounts) >= 2:
        flags.append("broad_price_range")
    if matches and all(
        not any(
            feature.startswith("item_title:")
            for feature in match.get("matched_features", [])
        )
        for match in matches
        if isinstance(match, dict)
    ):
        flags.append("context_only_match")
    return flags


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


def _cluster_key(value: str) -> str:
    normalized = _normalize_text(value)
    tokens = [token for token in normalized.split() if len(token) > 2]
    return " ".join(tokens[:4])


def _remark_type(text: str) -> str:
    lowered = text.lower()
    for remark_type, keywords in REMARK_TYPE_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return remark_type
    return "commercial"


def _matched_texts(values: list[str], keywords: list[str]) -> list[str]:
    result = []
    for value in values:
        lowered = value.lower()
        if any(keyword in lowered for keyword in keywords):
            result.append(value)
    return _dedupe_list(result)


def _normalize_text(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", value.lower())
    return " ".join(cleaned.split())


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
