from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

from .planner import PlannerDecision, plan_next_action
from .policy import can_run_skill
from .skill_registry import load_skill_registry
from .state import WorkflowState, build_initial_state


BASE_DIR = Path(__file__).resolve().parent
SKILL_DIR = BASE_DIR.parent
SKILLS_DIR = SKILL_DIR.parent
INPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "input.schema.json"
OUTPUT_SCHEMA_PATH = BASE_DIR / "schemas" / "output.schema.json"
QUOTE_DOCUMENT_SCHEMA_PATH = SKILLS_DIR.parent / "quote-document-v1.1.schema.json"


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Input JSON root must be object.")
    return data


def _dump_json(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_schema(path: str | Path) -> dict[str, Any]:
    return _load_json(path)


def _validate_payload(payload: dict[str, Any], schema_path: Path, label: str) -> None:
    schema = _load_schema(schema_path)
    try:
        validate(payload, schema)
    except ValidationError as exc:
        raise ValueError(f"{label} schema validation failed: {exc.message}") from exc


def _validate_quote_document(payload: dict[str, Any]) -> None:
    if payload.get("orchestration_status") != "completed":
        return
    quote_document = payload.get("quote_document")
    if not isinstance(quote_document, dict) or not quote_document:
        return
    schema = _load_schema(QUOTE_DOCUMENT_SCHEMA_PATH)
    validate(quote_document, schema)


def _load_skill_module(skill_name: str):
    skill_path = SKILLS_DIR / skill_name / "skill.py"
    skill_dir = str(skill_path.parent)
    if skill_dir not in sys.path:
        sys.path.insert(0, skill_dir)
    spec = importlib.util.spec_from_file_location(f"{skill_name}_module", skill_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load skill module: {skill_name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _default_pricing_rules(payload: dict[str, Any]) -> dict[str, Any]:
    business_context = payload.get("business_context")
    if not isinstance(business_context, dict):
        business_context = {}

    pricing_rules = business_context.get("pricing_rules")
    if isinstance(pricing_rules, dict):
        return pricing_rules

    customer_context = payload.get("customer_context")
    if not isinstance(customer_context, dict):
        customer_context = {}

    currency = (
        str(
            customer_context.get("currency")
            or customer_context.get("preferred_currency")
            or "USD"
        ).strip()
        or "USD"
    )
    return {
        "currency": currency,
        "service_rates": {
            "mechanical_supervisor_hourly": 55.0,
            "mechanical_technician_hourly": 35.0,
            "electrical_supervisor_hourly": 60.0,
            "electrical_assistant_hourly": 40.0,
            "service": 3500.0,
            "spare_parts": 800.0,
            "other": 300.0,
        },
        "lump_sum_overrides": {},
        "multi_option_mode": bool(business_context.get("multi_option")),
        "remark_hints": [],
        "default_discount_percentage": 5.0,
        "discount_overrides": {},
        "pricing_multipliers": {
            "spare_parts_oem": 1.25,
            "spare_parts_alternative": 1.5,
            "freight": 1.35,
            "delivery": 1.35,
            "third_party": 1.4,
            "dock_port_service": 1.3,
            "dockyard_management": 1.2,
            "boarding_travel": 1.2,
        },
        "charge_bases": {
            "third_party_base": 1200.0,
            "freight_base": 300.0,
            "delivery_base": 260.0,
            "transportation_base": 450.0,
            "accommodation_daily": 45.0,
            "port_service_base": 150.0,
            "maritime_reporting_base": 150.0,
            "dockyard_management_base": 200.0,
            "boarding_travel_base": 180.0,
        },
    }


def orchestrate_quote(payload: dict[str, Any]) -> dict[str, Any]:
    state = build_initial_state(payload)
    _hydrate_resume_state(state, payload)
    _apply_user_confirmations(state)
    registry = load_skill_registry(SKILLS_DIR)
    modules = {
        "quote_template_select_skill": _load_skill_module(
            "quote_template_select_skill"
        ),
        "quote_request_prepare_skill": _load_skill_module(
            "quote_request_prepare_skill"
        ),
        "quote_feasibility_check_skill": _load_skill_module(
            "quote_feasibility_check_skill"
        ),
        "historical_quote_reference_skill": _load_skill_module(
            "historical_quote_reference_skill"
        ),
        "quote_pricing_skill": _load_skill_module("quote_pricing_skill"),
        "quote_review_output_skill": _load_skill_module("quote_review_output_skill"),
        "quote_pdf_render_skill": _load_skill_module("quote_pdf_render_skill"),
    }

    while True:
        decision = plan_next_action(state, registry)
        state.planner_trace.append(_decision_trace(decision))
        if decision.action == "finish":
            if state.orchestration_status != "paused":
                state.orchestration_status = "completed"
            return state.to_result()
        if decision.action == "pause":
            state.orchestration_status = "paused"
            state.pause_reason = decision.reason
            return state.to_result()
        if decision.action == "skip":
            _apply_skip(state, decision)
            continue
        if decision.action != "run_skill" or not isinstance(decision.skill_name, str):
            raise RuntimeError(f"Unsupported planner action: {decision.action}")
        if not can_run_skill(state, decision.skill_name):
            raise RuntimeError(
                f"Planner selected invalid skill for current state: {decision.skill_name}"
            )
        _run_skill(state, decision, modules[decision.skill_name], payload)


def _run_skill(
    state: WorkflowState,
    decision: PlannerDecision,
    module: Any,
    original_payload: dict[str, Any],
) -> None:
    skill_name = decision.skill_name
    assert isinstance(skill_name, str)
    if skill_name == "historical_quote_reference_skill":
        _record_historical_reference_strategy(state, decision, executed=True)
    if skill_name == "quote_template_select_skill":
        result = module.select_quote_template(
            {
                "assessment_report": state.assessment_report,
                "customer_context": state.customer_context,
                "business_context": state.business_context,
            }
        )
        state.template_selection_result = result.get("template_selection_result", {})
    elif skill_name == "quote_request_prepare_skill":
        result = module.prepare_quote_request(
            {
                "assessment_report": state.assessment_report,
                "customer_context": state.customer_context,
                "business_context": {
                    **state.business_context,
                    **(
                        {"template_type": state.selected_template_type}
                        if isinstance(state.selected_template_type, str)
                        else {}
                    ),
                },
            }
        )
        state.prepare_result = result
    elif skill_name == "quote_feasibility_check_skill":
        state.feasibility_result = module.check_quote_feasibility(
            {"quote_request": state.quote_request}
        )
    elif skill_name == "historical_quote_reference_skill":
        state.historical_reference = module.build_historical_reference(
            {
                "quote_request": state.quote_request,
                "quotable_items": state.feasibility_result.get("quotable_items", []),
            }
        )
    elif skill_name == "quote_pricing_skill":
        state.pricing_result = module.build_pricing_result(
            {
                "quote_request": state.quote_request,
                "feasibility_result": state.feasibility_result,
                "historical_reference": state.historical_reference,
                "pricing_rules": _pricing_rules_for_state(state, original_payload),
            }
        )
    elif skill_name == "quote_review_output_skill":
        review_output = module.build_quote_document(
            {
                "quote_request": state.quote_request,
                "feasibility_result": state.feasibility_result,
                "historical_reference": state.historical_reference,
                "pricing_result": state.pricing_result,
            }
        )
        state.quote_document = (
            review_output.get("quote_document", {})
            if isinstance(review_output.get("quote_document"), dict)
            else {}
        )
    elif skill_name == "quote_pdf_render_skill":
        render_options = _normalized_render_options(state.render_options)
        if "template_type" not in render_options and isinstance(
            state.selected_template_type, str
        ):
            render_options["template_type"] = state.selected_template_type
        render_result = module.build_render_result(
            {"quote_document": state.quote_document, "render_options": render_options}
        )
        state.render_result = (
            render_result.get("render_result", {})
            if isinstance(render_result.get("render_result"), dict)
            else {}
        )
    else:
        raise RuntimeError(f"Unsupported skill execution: {skill_name}")
    state.execution_trace.append(
        {
            "skill_name": skill_name,
            "decision_type": decision.decision_type,
            "reason": decision.reason,
        }
    )


def _apply_skip(state: WorkflowState, decision: PlannerDecision) -> None:
    if decision.skill_name == "historical_quote_reference_skill":
        _record_historical_reference_strategy(state, decision, executed=False)
    state.skipped_skills.append(
        {
            "skill_name": decision.skill_name,
            "reason": decision.reason,
            "decision_type": decision.decision_type,
        }
    )
    if decision.skill_name == "quote_template_select_skill":
        forced_template_type = state.business_context.get("force_template_type")
        state.template_selection_result = {
            "template_type": forced_template_type,
            "confidence": 1.0,
            "candidate_templates": [forced_template_type],
            "rule_scores": {},
            "reasons": [
                "Skipped automatic template selection because force_template_type was provided."
            ],
            "matched_signals": [],
            "needs_manual_confirmation": False,
            "questions_for_user": [],
            "review_flags": [],
        }
    elif decision.skill_name == "historical_quote_reference_skill":
        state.historical_reference = {
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
                "history_quality_flags": ["skipped_by_planner"],
                "item_price_hints": [],
                "retrieval_strategy": "skipped_by_planner",
            },
            "confidence": 0.0,
        }


def _decision_trace(decision: PlannerDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "skill_name": decision.skill_name,
        "reason": decision.reason,
        "decision_type": decision.decision_type,
        "planner_notes": decision.planner_notes,
    }


def _hydrate_resume_state(state: WorkflowState, payload: dict[str, Any]) -> None:
    resume_payload = payload.get("resume_payload")
    if not isinstance(resume_payload, dict):
        return
    state.business_context["_resume_has_completed_outputs"] = bool(
        (
            isinstance(resume_payload.get("render_result"), dict)
            and bool(resume_payload.get("render_result"))
        )
        or (
            isinstance(resume_payload.get("quote_document"), dict)
            and bool(resume_payload.get("quote_document"))
        )
    )

    for field_name in [
        "template_selection_result",
        "prepare_result",
        "feasibility_result",
        "historical_reference",
        "pricing_result",
        "quote_document",
        "render_result",
    ]:
        value = resume_payload.get(field_name)
        if isinstance(value, dict) and value:
            setattr(state, field_name, value)

    execution_trace = resume_payload.get("execution_trace")
    if isinstance(execution_trace, list):
        state.execution_trace = [
            item for item in execution_trace if isinstance(item, dict)
        ]

    planner_trace = resume_payload.get("planner_trace")
    if isinstance(planner_trace, list):
        state.planner_trace = [item for item in planner_trace if isinstance(item, dict)]

    skipped_skills = resume_payload.get("skipped_skills")
    if isinstance(skipped_skills, list):
        state.skipped_skills = [
            item for item in skipped_skills if isinstance(item, dict)
        ]

    applied_strategies = resume_payload.get("applied_planner_strategies")
    if isinstance(applied_strategies, list):
        state.applied_planner_strategies = [
            item for item in applied_strategies if isinstance(item, dict)
        ]


def _apply_user_confirmations(state: WorkflowState) -> None:
    confirmations = _confirmed_answers(state)
    if not confirmations:
        return
    if not state.prepare_result or not state.quote_request:
        return

    applied_any = False
    spare_parts_supply_mode = confirmations.get("spare_parts_supply_mode")
    if isinstance(spare_parts_supply_mode, str):
        normalized_supply_mode = spare_parts_supply_mode.strip().lower()
        normalized_supply_mode = normalized_supply_mode.replace(" ", "_")
        if normalized_supply_mode in {"owner_supply", "company_supply"}:
            spare_parts_context = state.quote_request.get("spare_parts_context")
            if isinstance(spare_parts_context, dict):
                spare_parts_context["spare_parts_supply_mode"] = normalized_supply_mode
                applied_any = True
                _record_planner_strategy(
                    state,
                    strategy_type="clarification_applied",
                    reason="applied confirmed spare parts supply mode during resume",
                    payload={"spare_parts_supply_mode": normalized_supply_mode},
                )

    work_scope_answers = confirmations.get("work_scope")
    if isinstance(work_scope_answers, dict):
        candidate_items = state.quote_request.get("candidate_items")
        if isinstance(candidate_items, list):
            for item in candidate_items:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("item_id") or "")
                answer_value = work_scope_answers.get(item_id)
                if item_id and isinstance(answer_value, list):
                    cleaned_scope = [
                        str(scope).strip()
                        for scope in answer_value
                        if str(scope).strip()
                    ]
                    if cleaned_scope:
                        item["work_scope"] = cleaned_scope
                        applied_any = True
            if applied_any:
                _record_planner_strategy(
                    state,
                    strategy_type="clarification_applied",
                    reason="applied confirmed work scope details during resume",
                    payload={"work_scope_item_ids": sorted(work_scope_answers.keys())},
                )

    if applied_any:
        state.business_context["_resume_has_completed_outputs"] = False
        state.feasibility_result = {}
        state.historical_reference = {}
        state.pricing_result = {}
        state.quote_document = {}
        state.render_result = {}


def _confirmed_answers(state: WorkflowState) -> dict[str, Any]:
    customer_confirmations = state.customer_context.get("confirmed_answers")
    if isinstance(customer_confirmations, dict):
        return customer_confirmations
    business_confirmations = state.business_context.get("confirmed_answers")
    if isinstance(business_confirmations, dict):
        return business_confirmations
    return {}


def _pricing_rules_for_state(
    state: WorkflowState, original_payload: dict[str, Any]
) -> dict[str, Any]:
    pricing_rules = dict(_default_pricing_rules(original_payload))
    strategy_notes: dict[str, Any] = {}

    if state.business_context.get("force_multi_option") is True:
        pricing_rules["multi_option_mode"] = True
        strategy_notes["force_multi_option"] = True

    option_hints = state.business_context.get("option_hints")
    quote_request = state.quote_request
    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else None
    )
    if isinstance(service_context, dict) and isinstance(option_hints, list):
        cleaned_hints = [
            str(item).strip() for item in option_hints if str(item).strip()
        ]
        if cleaned_hints:
            existing_hints = service_context.get("option_hints")
            if not isinstance(existing_hints, list):
                existing_hints = []
            merged_hints = []
            seen: set[str] = set()
            for item in [*existing_hints, *cleaned_hints]:
                key = str(item).strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                merged_hints.append(str(item).strip())
            service_context["option_hints"] = merged_hints
            service_context["needs_multi_option"] = True
            pricing_rules["multi_option_mode"] = True
            strategy_notes["option_hints"] = cleaned_hints

    if strategy_notes:
        _record_planner_strategy(
            state,
            strategy_type="pricing_strategy",
            reason="planner injected pricing strategy before pricing stage",
            payload=strategy_notes,
        )
    return pricing_rules


def _record_planner_strategy(
    state: WorkflowState,
    strategy_type: str,
    reason: str,
    payload: dict[str, Any],
) -> None:
    entry = {
        "strategy_type": strategy_type,
        "reason": reason,
        "payload": payload,
    }
    if entry not in state.applied_planner_strategies:
        state.applied_planner_strategies.append(entry)


def _record_historical_reference_strategy(
    state: WorkflowState, decision: PlannerDecision, executed: bool
) -> None:
    _record_planner_strategy(
        state,
        strategy_type="historical_reference_strategy",
        reason=decision.reason,
        payload={
            "executed": executed,
            "skill_name": decision.skill_name,
            "decision_type": decision.decision_type,
            "planner_notes": decision.planner_notes,
        },
    )


def _normalized_render_options(render_options: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    languages = render_options.get("languages")
    if isinstance(languages, list):
        valid_languages = [item for item in languages if item in {"zh", "en"}]
        if valid_languages:
            normalized["languages"] = valid_languages
    output_dir = render_options.get("output_dir")
    if isinstance(output_dir, str) and output_dir.strip():
        normalized["output_dir"] = output_dir.strip()
    template_type = render_options.get("template_type")
    if isinstance(template_type, str) and template_type in {
        "engineering-service",
        "digital-product",
        "laboratory",
        "man-hour",
        "product",
        "supercharger",
        "valva",
    }:
        normalized["template_type"] = template_type
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the full quote workflow engine.")
    parser.add_argument("--input", required=True, help="Input JSON file path")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument(
        "--skip-schema-validation",
        action="store_true",
        help="Skip input/output JSON Schema validation.",
    )
    args = parser.parse_args()

    payload = _load_json(args.input)
    if not args.skip_schema_validation:
        _validate_payload(payload, INPUT_SCHEMA_PATH, "input")

    result = orchestrate_quote(payload)
    if not args.skip_schema_validation:
        _validate_payload(result, OUTPUT_SCHEMA_PATH, "output")
        _validate_quote_document(result)

    if args.output:
        _dump_json(args.output, result)
        print(f"Wrote output to {Path(args.output)}")
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
