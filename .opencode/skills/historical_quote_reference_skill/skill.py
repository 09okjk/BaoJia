from __future__ import annotations

import json
import math
import re
import hashlib
import os
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any

from embedding_provider import EmbeddingProviderError, embed_texts, load_config_from_env

try:
    import psycopg
except ImportError:  # pragma: no cover - optional dependency
    psycopg = None


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_PATH = BASE_DIR / "data" / "historical_quotes.sample.json"
DEFAULT_EMBEDDING_CACHE_PATH = BASE_DIR / "data" / "historical_embeddings.cache.json"
DEFAULT_ENV_PATH = BASE_DIR.parents[1] / ".env"
DEFAULT_DB_CONNECT_TIMEOUT_SECONDS = 5

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

VESSEL_TYPE_RULES = {
    "bulk_carrier": ["bulk carrier", "kamsarmax", "supramax", "handysize"],
    "tanker": ["tanker", "oil chemical", "chemical tanker", "oil tanker"],
    "container": ["container", "containership"],
    "general_cargo": ["general cargo", "cargo vessel"],
    "offshore": ["offshore", "platform supply", "anchor handling"],
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

    service_context = _dict(quote_request.get("service_context"))
    header_context = _dict(quote_request.get("header_context"))
    spare_parts_context = _dict(quote_request.get("spare_parts_context"))
    enriched_query_items = _enrich_query_items(quote_request, quotable_items)

    normalized_query_vessel_type = _normalize_vessel_type(
        header_context.get("vessel_type")
    )
    query_spare_parts_supply_mode = (
        str(spare_parts_context.get("spare_parts_supply_mode") or "").strip().lower()
    )

    prefiltered: list[dict[str, Any]] = []
    for record in history_records:
        prefilter = _prefilter_record(
            record,
            service_context,
            normalized_query_vessel_type,
            enriched_query_items,
        )
        if prefilter["passed"]:
            prefiltered.append({"record": record, "prefilter": prefilter})

    if not prefiltered:
        for record in history_records:
            prefilter = _prefilter_record(
                record,
                service_context,
                normalized_query_vessel_type,
                enriched_query_items,
            )
            if prefilter["score"] > 0:
                prefiltered.append({"record": record, "prefilter": prefilter})

    if not prefiltered:
        return _empty_reference_result()

    query_text = _query_text_blob(
        service_context,
        header_context,
        spare_parts_context,
        enriched_query_items,
    )
    record_texts = {
        str(item["record"].get("quote_id") or ""): _record_text_blob(item["record"])
        for item in prefiltered
    }
    semantic_result = _semantic_scores(query_text, record_texts)
    semantic_scores = semantic_result["scores"]

    matches: list[dict[str, Any]] = []
    for item in prefiltered:
        record = item["record"]
        prefilter = item["prefilter"]
        semantic_score = semantic_scores.get(str(record.get("quote_id") or ""), 0.0)
        match = _score_record(
            record,
            service_context,
            normalized_query_vessel_type,
            enriched_query_items,
            query_spare_parts_supply_mode,
            prefilter,
            semantic_score,
        )
        if match is not None:
            matches.append(match)

    matches.sort(key=lambda item: item["similarity"], reverse=True)
    top_matches = matches[:3]

    history_lookup = {
        str(record.get("quote_id") or ""): record for record in history_records
    }
    summary = _build_reference_summary(
        top_matches, enriched_query_items, history_lookup
    )
    summary["retrieval_strategy"] = semantic_result["strategy"]
    confidence = _build_confidence(top_matches, enriched_query_items)

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
            "item_price_hints": [],
            "retrieval_strategy": "rule_prefilter+tfidf_fallback",
        },
        "confidence": 0.0,
    }


def _load_history_records() -> list[dict[str, Any]]:
    db_records = _load_history_records_from_db()
    if db_records:
        return db_records

    if not DEFAULT_HISTORY_PATH.exists():
        return []
    data = json.loads(DEFAULT_HISTORY_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _load_history_records_from_db() -> list[dict[str, Any]]:
    if psycopg is None:
        return []

    _load_env_file(DEFAULT_ENV_PATH)
    required = ["PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD"]
    if not all(str(os.getenv(key) or "").strip() for key in required):
        return []

    try:
        conn = psycopg.connect(
            host=os.environ["PGHOST"],
            port=os.environ["PGPORT"],
            dbname=os.environ["PGDATABASE"],
            user=os.environ["PGUSER"],
            password=os.environ["PGPASSWORD"],
            connect_timeout=DEFAULT_DB_CONNECT_TIMEOUT_SECONDS,
        )
    except Exception:
        return []

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    quote_no,
                    currency,
                    total_amount,
                    payment_terms,
                    vessel_name,
                    imo_no,
                    vessel_type,
                    service_port,
                    remarks,
                    remarks_json,
                    standard_json,
                    summary_json,
                    keyword_text,
                    long_summary,
                    short_summary,
                    deal_status,
                    parse_status,
                    quality_score,
                    created_at
                from quote_document
                where doc_type = 'quotation'
                  and coalesce(parse_status, 'accept') = 'accept'
                order by created_at desc, id desc
                limit 500
                """
            )
            rows = cur.fetchall()
            columns = [desc.name for desc in cur.description]
    except Exception:
        conn.close()
        return []
    finally:
        conn.close()

    result = []
    for row in rows:
        payload = dict(zip(columns, row, strict=False))
        mapped = _map_quote_document_row(payload)
        if mapped is not None:
            result.append(mapped)
    return _dedupe_history_records(result)


def _map_quote_document_row(row: dict[str, Any]) -> dict[str, Any] | None:
    standard_json = (
        row.get("standard_json") if isinstance(row.get("standard_json"), dict) else {}
    )
    if not standard_json:
        return None

    lines = _list(standard_json.get("lines"))
    line_items = [item for item in lines if isinstance(item, dict)]
    remarks_json = (
        row.get("remarks_json") if isinstance(row.get("remarks_json"), list) else []
    )
    summary_json = (
        row.get("summary_json") if isinstance(row.get("summary_json"), dict) else {}
    )

    remark_texts = _extract_remark_texts(remarks_json, row.get("remarks"))
    item_details = _map_item_details(str(row.get("id") or ""), line_items)
    if not item_details:
        return None

    keyword_text = " ".join(
        [
            str(row.get("keyword_text") or ""),
            str(row.get("long_summary") or ""),
            str(row.get("short_summary") or ""),
        ]
    )

    record = {
        "quote_id": str(row.get("quote_no") or row.get("id") or "").strip(),
        "service_category": _infer_service_category(row, line_items, keyword_text),
        "service_mode": _infer_service_mode(row, line_items, keyword_text),
        "location_type": _infer_location_type_from_port(
            str(row.get("service_port") or ""), keyword_text
        ),
        "vessel_type": str(
            row.get("vessel_type") or standard_json.get("vessel_type") or ""
        ).strip(),
        "vessel_type_normalized": _normalize_vessel_type(
            row.get("vessel_type") or standard_json.get("vessel_type")
        ),
        "service_port_region": _service_port_region(str(row.get("service_port") or "")),
        "spare_parts_supply_mode": _infer_supply_mode_from_remarks(remark_texts),
        "currency": str(
            row.get("currency") or standard_json.get("currency") or ""
        ).strip()
        or None,
        "total_amount": _coalesce_number(
            row.get("total_amount"),
            standard_json.get("total_amount"),
            summary_json.get("total_amount"),
        ),
        "items": [item["title"] for item in item_details],
        "remarks": remark_texts,
        "commercial_terms": _dedupe_list(
            _string_list(row.get("payment_terms"))
            + _string_list(standard_json.get("payment_terms"))
        ),
        "option_style_tags": _option_style_tags_from_record(
            remark_texts, row, standard_json
        ),
        "charge_item_tags": _charge_item_tags_from_lines(item_details, remark_texts),
        "item_details": item_details,
        "source": "postgres_quote_document",
        "source_document_id": row.get("id"),
        "quality_score": _coalesce_number(row.get("quality_score")),
        "created_at": str(row.get("created_at") or ""),
    }
    if not record["quote_id"]:
        return None
    return record


def _map_item_details(
    document_id: str, line_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    result = []
    for index, line in enumerate(line_items, start=1):
        if not _should_include_line(line):
            continue
        title = str(line.get("product_name") or "").strip()
        if not title:
            continue
        item_type = _normalize_item_type(line.get("section_type") or "service")
        result.append(
            {
                "item_id": f"doc-{document_id}-line-{line.get('id') or index}",
                "item_type": item_type,
                "title": title,
                "description": _line_description(line),
                "work_scope": _line_work_scope(line),
                "labor_hint": _infer_labor_hints(title, line),
                "pricing_clues": _pricing_clues_from_line(title, line),
                "amount": _line_amount(line),
                "currency": None,
                "status": str(line.get("status") or "").strip() or "chargeable",
            }
        )
    return result


def _should_include_line(line: dict[str, Any]) -> bool:
    title = str(line.get("product_name") or "").strip()
    if not title:
        return False

    line_type = str(line.get("line_type") or "").strip().lower()
    status = str(line.get("status") or "").strip().lower()
    pricing_mode = str(line.get("pricing_mode") or "").strip().lower()
    title_lower = title.lower()

    if line_type == "group":
        return False

    if any(
        phrase in title_lower
        for phrase in [
            "work hour charge rate",
            "normal working hour charge rate",
            "overtime working hour charge rate",
            "travelling & waiting time charge rate",
            "waiting & travelling time",
            "tools needed as below",
            "option b ",
            "cooperative makers",
        ]
    ):
        return False

    if pricing_mode == "unit_price" and not _coalesce_number(
        line.get("line_amount"), line.get("qty")
    ):
        if any(
            token in title_lower
            for token in [
                "engineer",
                "technician",
                "mechanical technician",
                "welding technician",
            ]
        ):
            return False

    if status == "pending" and not _coalesce_number(
        line.get("line_amount"), line.get("unit_price")
    ):
        if not any(
            token in title_lower
            for token in [
                "overhaul",
                "repair",
                "renewal",
                "bearing",
                "crankshaft",
                "valve",
                "pump",
            ]
        ):
            return False

    return True


def _line_description(line: dict[str, Any]) -> str:
    return (
        str(line.get("spec") or "").strip()
        or str(line.get("product_model") or "").strip()
        or str(line.get("unit") or "").strip()
    )


def _line_work_scope(line: dict[str, Any]) -> list[str]:
    values = []
    spec = str(line.get("spec") or "").strip()
    product_model = str(line.get("product_model") or "").strip()
    remark = str(line.get("line_remark") or line.get("remark") or "").strip()
    if remark:
        values.append(remark)
    if spec and len(spec) > 20:
        values.append(spec)
    if product_model and len(product_model) > 12:
        values.append(product_model)
    return _dedupe_list(values)


def _line_amount(line: dict[str, Any]) -> float | None:
    line_amount = _coalesce_number(line.get("line_amount"))
    if line_amount is not None:
        return line_amount
    unit_price = _coalesce_number(line.get("unit_price"))
    qty = _coalesce_number(line.get("qty"))
    if unit_price is not None and qty is not None:
        return round(unit_price * qty, 2)
    if (
        str(line.get("pricing_mode") or "").strip().lower() == "lump_sum"
        and unit_price is not None
    ):
        return unit_price
    return None


def _extract_remark_texts(remarks_json: list[Any], fallback_remarks: Any) -> list[str]:
    texts = []
    for item in remarks_json:
        if isinstance(item, dict):
            text = str(item.get("text") or item.get("remark_text") or "").strip()
            if text:
                texts.append(text)
    if texts:
        return _dedupe_list(texts)
    return _split_remarks_text(fallback_remarks)


def _split_remarks_text(value: Any) -> list[str]:
    if not isinstance(value, str) or not value.strip():
        return []
    normalized = value.replace("��", "|").replace("；", "|").replace(";", "|")
    return [part.strip() for part in normalized.split("|") if part.strip()]


def _infer_service_category(
    row: dict[str, Any], line_items: list[dict[str, Any]], keyword_text: str
) -> str:
    text = " ".join(
        [keyword_text] + [str(item.get("product_name") or "") for item in line_items]
    ).lower()
    if any(
        keyword in text
        for keyword in ["electrical", "switchboard", "motor", "sensor", "cable"]
    ):
        return "electrical"
    if any(
        keyword in text
        for keyword in [
            "mechanical",
            "welding",
            "repair",
            "overhaul",
            "pump",
            "valve",
            "bearing",
            "crankshaft",
            "scrubber",
            "damper",
        ]
    ):
        return "mechanical"
    return "service"


def _infer_service_mode(
    row: dict[str, Any], line_items: list[dict[str, Any]], keyword_text: str
) -> str:
    text = " ".join(
        [str(row.get("service_port") or ""), keyword_text]
        + [str(item.get("product_name") or "") for item in line_items]
    ).lower()
    if any(
        keyword in text
        for keyword in ["shipyard", "dockyard", "sy", "dry dock", "drydock"]
    ):
        return "dock_repair"
    if "inspection" in text:
        return "inspection"
    if any(keyword in text for keyword in ["troubleshooting", "fault finding"]):
        return "troubleshooting"
    if any(keyword in text for keyword in ["riding squad", "underway", "on voyage"]):
        return "riding_squad"
    if any(
        keyword in text
        for keyword in [
            "sailing repair",
            "from china to singapore",
            "from singapore to china",
        ]
    ):
        return "riding_squad"
    return "voyage_repair"


def _infer_location_type_from_port(service_port: str, keyword_text: str) -> str:
    text = f"{service_port} {keyword_text}".lower()
    if any(
        keyword in text
        for keyword in ["shipyard", "dockyard", "sy", "dry dock", "drydock"]
    ):
        return "shipyard"
    if "anchorage" in text:
        return "anchorage"
    return "port"


def _service_port_region(service_port: str) -> str:
    text = service_port.lower()
    if any(
        keyword in text for keyword in ["jingtang", "tianjin", "qingdao", "xingang"]
    ):
        return "china_north"
    if any(keyword in text for keyword in ["shanghai", "zhapu", "ningbo"]):
        return "china_east"
    if any(keyword in text for keyword in ["guangzhou", "shenzhen", "xiamen"]):
        return "china_south"
    return "unknown"


def _infer_supply_mode_from_remarks(remarks: list[str]) -> str | None:
    text = " ".join(remarks).lower()
    if any(
        keyword in text
        for keyword in ["owner supply", "owner supplied", "shipside", "船东提供"]
    ):
        return "owner_supply"
    if any(keyword in text for keyword in ["company supply", "winkong supply"]):
        return "company_supply"
    return None


def _option_style_tags_from_record(
    remarks: list[str], row: dict[str, Any], standard_json: dict[str, Any]
) -> list[str]:
    source_texts = (
        remarks
        + _string_list(row.get("valid_until"))
        + _string_list(standard_json.get("valid_until"))
    )
    return [
        item["style_type"] for item in _build_option_style_hints([], source_texts, [])
    ]


def _charge_item_tags_from_lines(
    item_details: list[dict[str, Any]], remarks: list[str]
) -> list[str]:
    source_texts = [item["title"] for item in item_details] + remarks
    hints = _build_charge_item_hints(source_texts, [], [])
    return [item["hint_type"] for item in hints]


def _pricing_clues_from_line(title: str, line: dict[str, Any]) -> list[str]:
    text = f"{title} {line.get('spec') or ''} {line.get('product_model') or ''}".lower()
    clues = []
    if any(
        keyword in text
        for keyword in ["mechanical", "pump", "valve", "bearing", "repair", "overhaul"]
    ):
        clues.append("mechanical")
    if any(
        keyword in text
        for keyword in ["electrical", "switch", "sensor", "motor", "cable"]
    ):
        clues.append("electrical")
    if any(
        keyword in text
        for keyword in ["travel", "transportation", "accommodation", "hotel", "flight"]
    ):
        clues.append("travel")
    if any(keyword in text for keyword in ["shipyard", "dockyard"]):
        clues.append("dock repair")
    return _dedupe_list(clues)


def _infer_labor_hints(title: str, line: dict[str, Any]) -> list[str]:
    text = f"{title} {line.get('spec') or ''} {line.get('line_remark') or ''}".lower()
    hints = []
    if "mechanical technician" in text:
        hints.append("mechanical technician")
    if "welding technician" in text or "welder" in text:
        hints.append("welding technician")
    if "supervisor" in text:
        hints.append("supervisor")
    return _dedupe_list(hints)


def _coalesce_number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _dedupe_history_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        quote_id = str(record.get("quote_id") or "").strip()
        if not quote_id or quote_id.lower() in {"rev.1", "rev.2", "wk offer no."}:
            continue
        grouped.setdefault(quote_id, []).append(record)

    result = []
    for items in grouped.values():
        best = sorted(items, key=_history_record_rank, reverse=True)[0]
        result.append(best)
    result.sort(key=_history_record_rank, reverse=True)
    return result


def _history_record_rank(record: dict[str, Any]) -> tuple[float, float, int]:
    quality_score = _coalesce_number(record.get("quality_score")) or 0.0
    total_amount = _coalesce_number(record.get("total_amount")) or 0.0
    item_count = len(_list(record.get("item_details")))
    return quality_score, total_amount, item_count


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env_key = key.strip()
        if not env_key or env_key in os.environ:
            continue
        os.environ[env_key] = value.strip().strip('"').strip("'")


def _enrich_query_items(
    quote_request: dict[str, Any], quotable_items: list[Any]
) -> list[dict[str, Any]]:
    lookup = _candidate_item_lookup(quote_request)
    enriched: list[dict[str, Any]] = []
    for item in quotable_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "").strip()
        candidate_item = lookup.get(item_id, {})
        merged = dict(candidate_item)
        merged.update(item)
        merged.setdefault("description", str(candidate_item.get("description") or ""))
        merged.setdefault("work_scope", candidate_item.get("work_scope") or [])
        merged.setdefault("labor_hint", candidate_item.get("labor_hint") or [])
        merged.setdefault("pricing_clues", candidate_item.get("pricing_clues") or [])
        enriched.append(merged)
    return enriched


def _prefilter_record(
    record: dict[str, Any],
    service_context: dict[str, Any],
    normalized_query_vessel_type: str,
    query_items: list[dict[str, Any]],
) -> dict[str, Any]:
    score = 0.0
    reasons: list[str] = []

    if _match_text(record.get("service_mode"), service_context.get("service_mode")):
        score += 0.30
        reasons.append("service_mode")
    if _match_text(
        record.get("service_category"), service_context.get("service_category")
    ):
        score += 0.10
        reasons.append("service_category")
    if _match_text(record.get("location_type"), service_context.get("location_type")):
        score += 0.10
        reasons.append("location_type")

    normalized_record_vessel_type = str(
        record.get("vessel_type_normalized")
        or _normalize_vessel_type(record.get("vessel_type"))
    ).strip()
    if (
        normalized_query_vessel_type
        and normalized_record_vessel_type == normalized_query_vessel_type
    ):
        score += 0.10
        reasons.append("vessel_type_normalized")

    query_item_types = {
        str(item.get("item_type") or "").strip()
        for item in query_items
        if isinstance(item, dict)
    }
    record_item_types = {
        str(item.get("item_type") or "").strip()
        for item in _list(record.get("item_details"))
        if isinstance(item, dict)
    }
    if query_item_types and record_item_types and query_item_types & record_item_types:
        score += 0.10
        reasons.append("item_type_overlap")

    title_overlap = 0.0
    for item in query_items:
        query_title = str(item.get("title") or "").strip()
        if not query_title:
            continue
        for reference_title in _reference_items(record):
            title_overlap = max(
                title_overlap,
                _token_overlap(
                    _normalize_text(query_title), _normalize_text(reference_title)
                ),
            )
    if title_overlap >= 0.25:
        score += 0.15
        reasons.append("title_overlap")

    passed = score >= 0.25 or (
        _match_text(record.get("service_mode"), service_context.get("service_mode"))
        and title_overlap >= 0.15
    )
    if not query_items:
        passed = score >= 0.20

    return {
        "score": round(min(score, 1.0), 2),
        "passed": passed,
        "reasons": reasons,
    }


def _score_record(
    record: dict[str, Any],
    service_context: dict[str, Any],
    normalized_query_vessel_type: str,
    query_items: list[dict[str, Any]],
    query_spare_parts_supply_mode: str,
    prefilter: dict[str, Any],
    semantic_score: float,
) -> dict[str, Any] | None:
    rule_score = 0.0
    matched_features: list[str] = []

    if _match_text(
        record.get("service_category"), service_context.get("service_category")
    ):
        rule_score += 0.05
        matched_features.append(f"service_category: {record.get('service_category')}")

    if _match_text(record.get("service_mode"), service_context.get("service_mode")):
        rule_score += 0.15
        matched_features.append(f"service_mode: {record.get('service_mode')}")

    if _match_text(record.get("location_type"), service_context.get("location_type")):
        rule_score += 0.05
        matched_features.append(f"location_type: {record.get('location_type')}")

    normalized_record_vessel_type = str(
        record.get("vessel_type_normalized")
        or _normalize_vessel_type(record.get("vessel_type"))
    ).strip()
    if (
        normalized_query_vessel_type
        and normalized_record_vessel_type == normalized_query_vessel_type
    ):
        rule_score += 0.10
        matched_features.append(
            f"vessel_type_normalized: {normalized_record_vessel_type}"
        )

    item_match = _best_item_matches(record, query_items)
    rule_score += item_match["score"]
    matched_features.extend(item_match["features"])

    commercial_fit = _commercial_fit(record, query_spare_parts_supply_mode)
    if commercial_fit["spare_parts_supply_mode_match"]:
        rule_score += 0.05
        matched_features.append("spare_parts_supply_mode: matched")
    if commercial_fit["option_style_overlap"]:
        rule_score += 0.05
        matched_features.extend(
            [
                f"option_style: {style}"
                for style in commercial_fit["option_style_overlap"]
            ]
        )

    if not item_match["matched_item_pairs"] and prefilter["score"] <= 0.15:
        return None

    semantic_weight = 0.25 if item_match["matched_item_pairs"] else 0.10
    final_similarity = min(
        1.0,
        0.60 * rule_score
        + 0.15 * prefilter["score"]
        + semantic_weight * semantic_score,
    )
    final_similarity = round(final_similarity, 2)
    if final_similarity <= 0:
        return None

    return {
        "quote_id": str(record.get("quote_id") or ""),
        "similarity": final_similarity,
        "reason": _build_reason(
            matched_features,
            item_match["matched_item_pairs"],
            semantic_score,
            prefilter["reasons"],
        ),
        "matched_features": _dedupe_list(matched_features),
        "reference_items": _reference_items(record),
        "reference_remarks": _string_list(record.get("remarks")),
        "match_level": _match_level(
            final_similarity, item_match["matched_item_pairs"], semantic_score
        ),
        "matched_item_pairs": item_match["matched_item_pairs"],
        "commercial_fit": commercial_fit,
        "prefilter_score": round(prefilter["score"], 2),
        "semantic_score": round(semantic_score, 2),
        "rerank_stage": "hybrid",
    }


def _best_item_matches(
    record: dict[str, Any], query_items: list[dict[str, Any]]
) -> dict[str, Any]:
    record_item_details = _list(record.get("item_details"))

    score = 0.0
    features: list[str] = []
    matched_item_pairs: list[dict[str, Any]] = []

    for query_item in query_items:
        if not isinstance(query_item, dict):
            continue
        query_item_id = str(query_item.get("item_id") or "").strip()
        query_title = str(query_item.get("title") or "").strip()
        query_item_type = str(query_item.get("item_type") or "").strip()
        if not query_item_id or not query_title:
            continue

        best_pair: dict[str, Any] | None = None
        best_pair_score = 0.0
        best_pair_features: list[str] = []
        for reference_item in record_item_details:
            if not isinstance(reference_item, dict):
                continue
            pair_score, pair_features = _item_match_score(
                query_item, query_item_type, query_title, reference_item
            )
            if pair_score > best_pair_score:
                best_pair_score = pair_score
                best_pair_features = pair_features
                best_pair = {
                    "query_item_id": query_item_id,
                    "query_title": query_title,
                    "reference_item_id": str(
                        reference_item.get("item_id") or ""
                    ).strip(),
                    "reference_title": str(reference_item.get("title") or "").strip(),
                    "similarity": round(min(pair_score, 1.0), 2),
                    "matched_signals": pair_features,
                }

        if best_pair is None or best_pair_score < 0.2:
            continue

        matched_item_pairs.append(best_pair)
        score += min(best_pair_score, 0.25)
        if query_item_type:
            features.append(f"item_type: {query_item_type}")
        features.extend(best_pair_features)

    return {
        "score": min(score, 0.50),
        "features": _dedupe_list(features),
        "matched_item_pairs": matched_item_pairs,
    }


def _item_match_score(
    query_item: dict[str, Any],
    query_item_type: str,
    query_title: str,
    reference_item: dict[str, Any],
) -> tuple[float, list[str]]:
    score = 0.0
    features: list[str] = []

    reference_item_type = str(reference_item.get("item_type") or "").strip()
    if (
        query_item_type
        and reference_item_type
        and query_item_type == reference_item_type
    ):
        score += 0.10
        features.append(f"item_type_match: {query_item_type}")

    reference_title = str(reference_item.get("title") or "").strip()
    if _match_text(query_title, reference_title):
        score += 0.25
        features.append(f"item_title: {query_title}")
    else:
        title_overlap = _token_overlap(
            _normalize_text(query_title), _normalize_text(reference_title)
        )
        if title_overlap >= 0.5:
            score += 0.18
            features.append(f"item_title: {query_title}")

    query_text = _item_text_blob(query_item)
    reference_text = _item_text_blob(reference_item)
    blob_overlap = _token_overlap(query_text, reference_text)
    if blob_overlap >= 0.35:
        score += 0.18
        features.append(f"work_scope_match: {reference_title or query_title}")

    query_pricing_clues = _string_list(query_item.get("pricing_clues"))
    reference_pricing_clues = _string_list(reference_item.get("pricing_clues"))
    clue_overlap = _list_overlap(query_pricing_clues, reference_pricing_clues)
    if clue_overlap > 0:
        score += 0.08
        features.append(f"pricing_clue_match: {reference_title or query_title}")

    query_labor = _string_list(query_item.get("labor_hint"))
    reference_labor = _string_list(reference_item.get("labor_hint"))
    labor_overlap = _list_overlap(query_labor, reference_labor)
    if labor_overlap > 0:
        score += 0.04
        features.append(f"labor_hint_match: {reference_title or query_title}")

    return score, _dedupe_list(features)


def _commercial_fit(
    record: dict[str, Any], query_spare_parts_supply_mode: str
) -> dict[str, Any]:
    record_supply_mode = (
        str(record.get("spare_parts_supply_mode") or "").strip().lower()
    )
    spare_parts_supply_mode_match = bool(
        query_spare_parts_supply_mode
        and record_supply_mode
        and query_spare_parts_supply_mode == record_supply_mode
    )

    option_style_overlap = _dedupe_list(_string_list(record.get("option_style_tags")))
    if not option_style_overlap:
        derived_hints = _build_option_style_hints(
            _reference_items(record), _string_list(record.get("remarks")), [record]
        )
        option_style_overlap = _dedupe_list(
            [
                str(hint.get("style_type") or "").strip()
                for hint in derived_hints
                if isinstance(hint, dict) and str(hint.get("style_type") or "").strip()
            ]
        )
    return {
        "spare_parts_supply_mode_match": spare_parts_supply_mode_match,
        "option_style_overlap": option_style_overlap[:3],
    }


def _build_reason(
    matched_features: list[str],
    matched_item_pairs: list[dict[str, Any]],
    semantic_score: float,
    prefilter_reasons: list[str],
) -> str:
    if matched_item_pairs and semantic_score >= 0.45:
        return "核心项目工作范围、文本语义与服务场景相似。"
    if matched_item_pairs:
        return "核心项目工作范围与服务场景相似。"
    if semantic_score >= 0.45 and prefilter_reasons:
        return "规则预筛通过后，文本语义与场景特征存在相似性。"
    if len(matched_features) >= 3:
        return "服务模式、地点类型和上下文特征存在相似性。"
    if len(matched_features) == 2:
        return "存在多个关键上下文特征匹配。"
    return "存在单个关键特征匹配。"


def _match_level(
    similarity: float, matched_item_pairs: list[dict[str, Any]], semantic_score: float
) -> str:
    if matched_item_pairs and similarity >= 0.65 and semantic_score >= 0.40:
        return "strong_item_match"
    if matched_item_pairs:
        return "item_and_context"
    return "context_only"


def _build_reference_summary(
    matches: list[dict[str, Any]],
    query_items: list[dict[str, Any]],
    history_records: dict[str, dict[str, Any]],
) -> dict[str, Any]:
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
        record_items = _reference_items(record)
        record_remarks = _string_list(record.get("remarks"))
        common_items_counter.update(record_items)
        remark_counter.update(record_remarks)
        all_items.extend(record_items)
        all_remarks.extend(record_remarks)

    item_price_hints = _build_item_price_hints(matches, query_items, history_records)
    history_quality_flags = _build_history_quality_flags(
        matches, amounts, query_items, item_price_hints
    )

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
        "charge_item_hints": _build_charge_item_hints(
            all_items, all_remarks, selected_records
        ),
        "option_style_hints": _build_option_style_hints(
            all_items, all_remarks, selected_records
        ),
        "history_quality_flags": history_quality_flags,
        "item_price_hints": item_price_hints,
    }


def _build_item_price_hints(
    matches: list[dict[str, Any]],
    query_items: list[dict[str, Any]],
    history_records: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    matched_pairs_by_query_item: dict[str, list[dict[str, Any]]] = {}

    for match in matches:
        if not isinstance(match, dict):
            continue
        quote_id = str(match.get("quote_id") or "")
        for pair in _list(match.get("matched_item_pairs")):
            if not isinstance(pair, dict):
                continue
            query_item_id = str(pair.get("query_item_id") or "").strip()
            if not query_item_id:
                continue
            pair_copy = dict(pair)
            pair_copy["quote_id"] = quote_id
            matched_pairs_by_query_item.setdefault(query_item_id, []).append(pair_copy)

    for item in query_items:
        if not isinstance(item, dict):
            continue
        query_item_id = str(item.get("item_id") or "").strip()
        query_title = str(item.get("title") or "").strip()
        if not query_item_id or not query_title:
            continue

        pairs = matched_pairs_by_query_item.get(query_item_id, [])
        price_samples: list[float] = []
        currencies: list[str] = []
        matched_reference_item_ids: list[str] = []
        source_quote_ids: list[str] = []

        for pair in pairs:
            quote_id = str(pair.get("quote_id") or "")
            reference_item_id = str(pair.get("reference_item_id") or "")
            if not quote_id or not reference_item_id:
                continue
            record = history_records.get(quote_id, {})
            item_detail = _history_item_lookup(record).get(reference_item_id)
            amount = (
                item_detail.get("amount") if isinstance(item_detail, dict) else None
            )
            currency = (
                item_detail.get("currency") if isinstance(item_detail, dict) else None
            )
            if isinstance(amount, (int, float)):
                price_samples.append(float(amount))
                matched_reference_item_ids.append(reference_item_id)
                source_quote_ids.append(quote_id)
                if isinstance(currency, str) and currency.strip():
                    currencies.append(currency.strip())

        if not price_samples:
            continue

        hints.append(
            {
                "query_item_id": query_item_id,
                "query_title": query_title,
                "currency": currencies[0] if currencies else None,
                "min": min(price_samples),
                "max": max(price_samples),
                "median": round(float(median(price_samples)), 2),
                "sample_size": len(price_samples),
                "matched_reference_item_ids": _dedupe_list(matched_reference_item_ids),
                "source_quote_ids": _dedupe_list(source_quote_ids),
            }
        )

    return hints


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
    items: list[str], remarks: list[str], selected_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source_texts = items + remarks
    for record in selected_records:
        source_texts.extend(_string_list(record.get("charge_item_tags")))
    result = []
    for hint_type, keywords in CHARGE_ITEM_RULES.items():
        matches = _matched_texts(source_texts, keywords + [hint_type])
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
    items: list[str], remarks: list[str], selected_records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    source_texts = items + remarks
    for record in selected_records:
        source_texts.extend(_string_list(record.get("option_style_tags")))
    result = []
    for style_type, keywords in OPTION_STYLE_RULES.items():
        matches = _matched_texts(source_texts, keywords + [style_type])
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
    matches: list[dict[str, Any]],
    amounts: list[float],
    query_items: list[Any],
    item_price_hints: list[dict[str, Any]],
) -> list[str]:
    flags: list[str] = []
    if len(matches) < 2:
        flags.append("low_sample_size")
    if matches and matches[0]["similarity"] < 0.5:
        flags.append("weak_top_match")
    if query_items and not any(match.get("matched_item_pairs") for match in matches):
        flags.append("weak_item_overlap")
    if matches and all(match.get("match_level") == "context_only" for match in matches):
        flags.append("context_only_match")
    if len(amounts) >= 2 and min(amounts) > 0 and max(amounts) / min(amounts) >= 2:
        flags.append("broad_price_range")
    if item_price_hints and any(hint["sample_size"] < 2 for hint in item_price_hints):
        flags.append("low_item_sample_size")
    if any(
        isinstance(hint.get("min"), (int, float))
        and isinstance(hint.get("max"), (int, float))
        and float(hint["min"]) > 0
        and float(hint["max"]) / float(hint["min"]) >= 2
        for hint in item_price_hints
    ):
        flags.append("broad_item_price_range")
    if any(
        isinstance(match.get("commercial_fit"), dict)
        and not match["commercial_fit"].get("spare_parts_supply_mode_match", True)
        and str(match.get("match_level") or "") != "context_only"
        for match in matches
    ):
        flags.append("commercial_mismatch")
    if any(
        isinstance(match.get("semantic_score"), (int, float))
        and float(match["semantic_score"]) >= 0.5
        and not match.get("matched_item_pairs")
        for match in matches
    ):
        flags.append("semantic_only_match")
    return _dedupe_list(flags)


def _build_confidence(matches: list[dict[str, Any]], query_items: list[Any]) -> float:
    if not matches:
        return 0.0
    top_similarity = matches[0]["similarity"]
    sample_bonus = min(len(matches) * 0.05, 0.15)
    query_penalty = 0.0 if query_items else 0.15
    item_bonus = 0.1 if matches[0].get("matched_item_pairs") else 0.0
    semantic_bonus = (
        0.05 if float(matches[0].get("semantic_score") or 0.0) >= 0.45 else 0.0
    )
    confidence = max(
        0.0,
        min(
            top_similarity + sample_bonus + item_bonus + semantic_bonus - query_penalty,
            1.0,
        ),
    )
    return round(confidence, 2)


def _query_text_blob(
    service_context: dict[str, Any],
    header_context: dict[str, Any],
    spare_parts_context: dict[str, Any],
    query_items: list[dict[str, Any]],
) -> str:
    parts = [
        str(service_context.get("service_category") or ""),
        str(service_context.get("service_mode") or ""),
        str(service_context.get("location_type") or ""),
        _normalize_vessel_type(header_context.get("vessel_type")),
        str(spare_parts_context.get("spare_parts_supply_mode") or ""),
    ]
    for item in query_items:
        if isinstance(item, dict):
            parts.append(_item_text_blob(item))
    return _normalize_text(" ".join(part for part in parts if part))


def _record_text_blob(record: dict[str, Any]) -> str:
    parts = [
        str(record.get("service_category") or ""),
        str(record.get("service_mode") or ""),
        str(record.get("location_type") or ""),
        str(
            record.get("vessel_type_normalized")
            or _normalize_vessel_type(record.get("vessel_type"))
        ),
        str(record.get("spare_parts_supply_mode") or ""),
    ]
    parts.extend(_reference_items(record))
    parts.extend(_string_list(record.get("remarks")))
    parts.extend(_string_list(record.get("option_style_tags")))
    parts.extend(_string_list(record.get("charge_item_tags")))
    for item in _list(record.get("item_details")):
        if isinstance(item, dict):
            parts.append(_item_text_blob(item))
    return _normalize_text(" ".join(part for part in parts if part))


def _semantic_scores(query_text: str, record_texts: dict[str, str]) -> dict[str, Any]:
    if not query_text or not record_texts:
        return {
            "scores": {key: 0.0 for key in record_texts},
            "strategy": "rule_prefilter+tfidf_fallback",
        }

    config = None
    try:
        config = load_config_from_env()
    except EmbeddingProviderError:
        config = None

    if config is not None:
        try:
            return _embedding_semantic_scores(query_text, record_texts)
        except EmbeddingProviderError:
            pass

    corpus = [query_text] + [text for text in record_texts.values() if text]
    idf = _idf(corpus)
    query_vector = _tfidf_vector(query_text, idf)

    scores: dict[str, float] = {}
    for quote_id, text in record_texts.items():
        scores[quote_id] = round(
            _cosine_similarity(query_vector, _tfidf_vector(text, idf)), 4
        )
    return {
        "scores": scores,
        "strategy": "rule_prefilter+tfidf_fallback",
    }


def _embedding_semantic_scores(
    query_text: str, record_texts: dict[str, str]
) -> dict[str, Any]:
    config = load_config_from_env()
    if config is None:
        raise EmbeddingProviderError("Embedding config not available")

    cache = _load_embedding_cache()
    cache_records = _cache_lookup(cache)
    quote_ids = list(record_texts.keys())

    cache_updated = False
    record_vectors: dict[str, list[float]] = {}
    missing_quote_ids: list[str] = []
    missing_texts: list[str] = []

    for quote_id in quote_ids:
        text = record_texts[quote_id]
        content_hash = _content_hash(text)
        cached = cache_records.get(quote_id)
        if (
            cached
            and cached.get("content_hash") == content_hash
            and isinstance(cached.get("embedding"), list)
        ):
            record_vectors[quote_id] = [float(value) for value in cached["embedding"]]
            continue
        missing_quote_ids.append(quote_id)
        missing_texts.append(text)

    if missing_texts:
        new_embeddings = embed_texts(missing_texts, config)
        for quote_id, text, embedding in zip(
            missing_quote_ids, missing_texts, new_embeddings, strict=False
        ):
            record_vectors[quote_id] = embedding
            cache_records[quote_id] = {
                "quote_id": quote_id,
                "content_hash": _content_hash(text),
                "text": text,
                "embedding": embedding,
            }
            cache_updated = True

    query_vector = embed_texts([query_text], config)[0]
    scores = {
        quote_id: round(
            _dense_cosine_similarity(query_vector, record_vectors[quote_id]), 4
        )
        for quote_id in quote_ids
    }

    if cache_updated:
        _write_embedding_cache(cache, cache_records, config)

    return {
        "scores": scores,
        "strategy": "rule_prefilter+aliyun_embedding_rerank",
    }


def _idf(texts: list[str]) -> dict[str, float]:
    doc_count = len(texts)
    frequencies: Counter[str] = Counter()
    for text in texts:
        frequencies.update(set(_tokenize(text)))
    return {
        token: math.log((doc_count + 1) / (count + 1)) + 1.0
        for token, count in frequencies.items()
    }


def _tfidf_vector(text: str, idf: dict[str, float]) -> dict[str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return {}
    counts = Counter(tokens)
    max_tf = max(counts.values())
    return {
        token: (0.5 + 0.5 * count / max_tf) * idf.get(token, 1.0)
        for token, count in counts.items()
    }


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    numerator = sum(left[token] * right.get(token, 0.0) for token in left)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _dense_cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    numerator = sum(lv * rv for lv, rv in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _tokenize(text: str) -> list[str]:
    return [token for token in _normalize_text(text).split() if token]


def _reference_items(record: dict[str, Any]) -> list[str]:
    item_details = record.get("item_details")
    if isinstance(item_details, list):
        titles = [
            str(item.get("title") or "").strip()
            for item in item_details
            if isinstance(item, dict) and str(item.get("title") or "").strip()
        ]
        if titles:
            return _dedupe_list(titles)
    return _string_list(record.get("items"))


def _history_item_lookup(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    item_details = record.get("item_details")
    if not isinstance(item_details, list):
        return lookup
    for item in item_details:
        if isinstance(item, dict) and isinstance(item.get("item_id"), str):
            lookup[item["item_id"]] = item
    return lookup


def _candidate_item_lookup(quote_request: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    candidate_items = quote_request.get("candidate_items")
    if isinstance(candidate_items, list):
        for item in candidate_items:
            if isinstance(item, dict) and isinstance(item.get("item_id"), str):
                lookup[item["item_id"]] = item

    spare_parts_context = _dict(quote_request.get("spare_parts_context"))
    spare_parts_items = spare_parts_context.get("spare_parts_items")
    if isinstance(spare_parts_items, list):
        for item in spare_parts_items:
            if isinstance(item, dict) and isinstance(item.get("item_id"), str):
                lookup[item["item_id"]] = item
    return lookup


def _item_text_blob(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("item_type") or "").strip(),
        str(item.get("title") or "").strip(),
        str(item.get("description") or "").strip(),
    ]
    for key in ["work_scope", "labor_hint", "pricing_clues"]:
        raw = item.get(key)
        if isinstance(raw, list):
            parts.extend(str(value).strip() for value in raw if str(value).strip())
    return _normalize_text(" ".join(value for value in parts if value))


def _normalize_vessel_type(value: Any) -> str:
    text = _normalize_text(str(value or ""))
    if not text:
        return "unknown"
    for vessel_type, keywords in VESSEL_TYPE_RULES.items():
        if any(keyword in text for keyword in keywords):
            return vessel_type
    return "unknown"


def _normalize_item_type(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"service", "spare_parts", "other"}:
        return text
    if text in {"spares", "spare parts", "parts"}:
        return "spare_parts"
    return "service"


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


def _list_overlap(left: list[str], right: list[str]) -> float:
    left_tokens = {_normalize_text(value) for value in left if _normalize_text(value)}
    right_tokens = {_normalize_text(value) for value in right if _normalize_text(value)}
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
    normalized_keywords = [keyword.lower() for keyword in keywords]
    for value in values:
        lowered = value.lower()
        if any(keyword in lowered for keyword in normalized_keywords):
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


def _load_embedding_cache() -> dict[str, Any]:
    if not DEFAULT_EMBEDDING_CACHE_PATH.exists():
        return {"metadata": {}, "records": []}
    try:
        data = json.loads(DEFAULT_EMBEDDING_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"metadata": {}, "records": []}
    if not isinstance(data, dict):
        return {"metadata": {}, "records": []}
    return data


def _cache_lookup(cache: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = cache.get("records")
    if not isinstance(records, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in records:
        if isinstance(item, dict) and isinstance(item.get("quote_id"), str):
            result[item["quote_id"]] = item
    return result


def _write_embedding_cache(
    cache: dict[str, Any],
    cache_records: dict[str, dict[str, Any]],
    config: Any,
) -> None:
    payload = {
        "metadata": {
            "provider": "aliyun_openai_compatible",
            "model": getattr(config, "model", "text-embedding-v4"),
            "dimensions": getattr(config, "dimensions", 1024),
            "base_url": getattr(config, "base_url", ""),
        },
        "records": [cache_records[key] for key in sorted(cache_records.keys())],
    }
    DEFAULT_EMBEDDING_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_EMBEDDING_CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
