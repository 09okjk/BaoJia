from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TEMPLATE_TYPES = [
    "engineering-service",
    "digital-product",
    "laboratory",
    "man-hour",
    "product",
    "supercharger",
    "valva",
]

DEFAULT_TEMPLATE_TYPE = "engineering-service"

RULE_GROUPS: dict[str, list[tuple[str, float]]] = {
    "laboratory": [
        (r"\blaboratory\b", 5.0),
        (r"\btesting\b", 4.0),
        (r"\bsample\b", 4.0),
        (r"\bintake water\b", 5.0),
        (r"\bdischarge water\b", 5.0),
        (r"检测|化验|实验室|样本|取样|进水|排水", 5.0),
    ],
    "supercharger": [
        (r"\bturbocharger\b", 6.0),
        (r"\bsupercharger\b", 6.0),
        (r"\bvtr\b|\btca\b|\bmet\b", 4.0),
        (r"\brunning hours\b", 2.0),
        (r"增压器", 6.0),
    ],
    "valva": [
        (r"\bvalve\b", 4.0),
        (r"\brepair kit\b", 4.0),
        (r"\bcomplete valve\b", 5.0),
        (r"\bposition no\b", 4.0),
        (r"\bpilot valve\b", 5.0),
        (r"阀|修理包|完整阀|阀位号", 4.0),
    ],
    "digital-product": [
        (r"\bdigital\b", 5.0),
        (r"\bsoftware\b", 5.0),
        (r"\blicense\b", 5.0),
        (r"\bsubscription\b", 5.0),
        (r"\bplatform\b", 4.0),
        (r"数字产品|软件|系统授权|订阅|平台", 5.0),
    ],
    "product": [
        (r"\bspare part\b", 4.0),
        (r"\bspare parts\b", 4.0),
        (r"\bpart no\b", 4.0),
        (r"\bspecification\b", 3.0),
        (r"商品|备件|规格|型号", 3.0),
    ],
    "man-hour": [
        (r"\bman-hour\b", 5.0),
        (r"\bengineer\b", 2.0),
        (r"\bfitter\b", 2.0),
        (r"\battendance\b", 5.0),
        (r"\bdays\b|\bhours\b", 2.0),
        (r"工时|人工|工程师|钳工|人数|小时|天数", 3.0),
    ],
    "engineering-service": [
        (r"\boverhaul\b", 3.0),
        (r"\binspection\b", 3.0),
        (r"\bcalibration\b", 3.0),
        (r"\bmaintenance\b", 3.0),
        (r"\bcommissioning\b", 3.0),
        (r"\bservice\b", 2.0),
        (r"大修|检修|校验|调试|维护|工程服务", 3.0),
    ],
}


def select_quote_template(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Input payload must be a JSON object.")

    assessment_report = payload.get("assessment_report")
    if not isinstance(assessment_report, dict):
        raise ValueError("assessment_report is required and must be a JSON object.")

    business_context = payload.get("business_context")
    if business_context is None:
        business_context = {}
    if not isinstance(business_context, dict):
        raise ValueError("business_context must be a JSON object when provided.")

    forced_template = business_context.get("force_template_type")
    if isinstance(forced_template, str) and forced_template in TEMPLATE_TYPES:
        return {
            "template_selection_result": {
                "template_type": forced_template,
                "confidence": 1.0,
                "candidate_templates": [forced_template],
                "rule_scores": _empty_rule_scores(),
                "reasons": [
                    "business_context.force_template_type 已显式指定模板类型。"
                ],
                "matched_signals": [
                    {
                        "signal": "force_template_type",
                        "source": "business_context.force_template_type",
                        "weight": 100.0,
                        "supports": [forced_template],
                    }
                ],
                "needs_manual_confirmation": False,
                "questions_for_user": [],
                "review_flags": [],
            }
        }

    text_sources = _collect_text_sources(assessment_report)
    rule_scores, matched_signals = _score_templates(text_sources)
    selected_template, candidate_templates = _pick_templates(rule_scores)
    confidence = _confidence(rule_scores, candidate_templates)
    reasons = _build_reasons(selected_template, candidate_templates, matched_signals)
    needs_manual_confirmation = confidence < 0.65 or len(candidate_templates) > 1
    review_flags: list[str] = []
    questions_for_user: list[str] = []

    if needs_manual_confirmation:
        review_flags.append("模板识别置信度较低，建议人工确认。")
        if len(candidate_templates) > 1:
            questions_for_user.append(
                f"当前模板候选为 {', '.join(candidate_templates)}，请确认最终报价类型。"
            )

    if selected_template == DEFAULT_TEMPLATE_TYPE and not matched_signals:
        reasons.append("未命中明显专项模板特征，当前按工程服务模板兜底。")

    return {
        "template_selection_result": {
            "template_type": selected_template,
            "confidence": confidence,
            "candidate_templates": candidate_templates,
            "rule_scores": rule_scores,
            "reasons": reasons,
            "matched_signals": matched_signals,
            "needs_manual_confirmation": needs_manual_confirmation,
            "questions_for_user": questions_for_user,
            "review_flags": review_flags,
        }
    }


def load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be an object.")
    return data


def dump_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _collect_text_sources(assessment_report: dict[str, Any]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []

    def add(source: str, value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            cleaned = value.strip()
            if cleaned:
                texts.append((source, cleaned))
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                add(f"{source}[{index}]", item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                add(f"{source}.{key}", item)

    for key in [
        "service_category",
        "service_mode",
        "location_type",
        "vessel_name",
        "vessel_type",
        "service_port",
        "attention",
        "remarks",
    ]:
        add(f"assessment_report.{key}", assessment_report.get(key))

    for key in [
        "service_items",
        "spare_parts_items",
        "pending_items",
        "risks",
        "assumptions",
    ]:
        add(f"assessment_report.{key}", assessment_report.get(key))

    return texts


def _score_templates(
    text_sources: list[tuple[str, str]],
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    scores = _empty_rule_scores()
    matched_signals: list[dict[str, Any]] = []
    for source, text in text_sources:
        lowered = text.lower()
        for template_type, rules in RULE_GROUPS.items():
            for pattern, weight in rules:
                if (
                    pattern == r"\bsample\b"
                    and source == "assessment_report.vessel_name"
                ):
                    continue
                if re.search(pattern, lowered, flags=re.IGNORECASE):
                    scores[template_type] += weight
                    matched_signals.append(
                        {
                            "signal": pattern,
                            "source": source,
                            "weight": weight,
                            "supports": [template_type],
                        }
                    )

    if scores["product"] > 0 and scores["engineering-service"] > 0:
        scores["product"] -= 1.0
    if scores["man-hour"] > 0 and scores["engineering-service"] > 0:
        scores["engineering-service"] += 1.0
    if scores["valva"] > 0 and scores["supercharger"] > 0:
        scores["valva"] += 1.0

    return scores, matched_signals


def _pick_templates(rule_scores: dict[str, float]) -> tuple[str, list[str]]:
    sorted_items = sorted(rule_scores.items(), key=lambda item: item[1], reverse=True)
    top_template, top_score = sorted_items[0]
    if top_score <= 0:
        return DEFAULT_TEMPLATE_TYPE, [DEFAULT_TEMPLATE_TYPE]

    candidates = [
        name for name, score in sorted_items if score > 0 and top_score - score <= 2.0
    ]
    if top_template not in candidates:
        candidates.insert(0, top_template)
    return top_template, candidates[:3]


def _confidence(rule_scores: dict[str, float], candidate_templates: list[str]) -> float:
    sorted_scores = sorted(rule_scores.values(), reverse=True)
    top = sorted_scores[0] if sorted_scores else 0.0
    second = sorted_scores[1] if len(sorted_scores) > 1 else 0.0
    if top <= 0:
        return 0.35
    margin = max(top - second, 0.0)
    if top >= 10 and margin >= 5:
        return 0.93
    if top >= 8 and margin >= 3:
        return 0.86
    if top >= 6 and margin >= 2:
        return 0.74
    if len(candidate_templates) > 1:
        return 0.58
    return 0.66


def _build_reasons(
    selected_template: str,
    candidate_templates: list[str],
    matched_signals: list[dict[str, Any]],
) -> list[str]:
    dominant_signals = [
        item for item in matched_signals if selected_template in item["supports"]
    ][:3]
    reasons: list[str] = []
    if dominant_signals:
        reasons.append(f"规则命中 {selected_template} 相关特征词。")
        reasons.extend(
            [
                f"命中信号：{item['signal']}，来源：{item['source']}。"
                for item in dominant_signals
            ]
        )
    else:
        reasons.append("未命中明显专项模板特征。")

    if len(candidate_templates) > 1:
        reasons.append(f"当前与 {', '.join(candidate_templates[1:])} 存在一定相似性。")
    return reasons


def _empty_rule_scores() -> dict[str, float]:
    return {name: 0.0 for name in TEMPLATE_TYPES}
