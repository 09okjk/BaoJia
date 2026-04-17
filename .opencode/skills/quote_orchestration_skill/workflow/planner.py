from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .skill_registry import SkillRegistryEntry
from .state import WorkflowState


@dataclass
class PlannerDecision:
    action: str
    skill_name: str | None = None
    reason: str = ""
    decision_type: str = "required"
    planner_notes: list[str] = field(default_factory=list)


def plan_next_action(
    state: WorkflowState, registry: dict[str, SkillRegistryEntry]
) -> PlannerDecision:
    if _should_finish_from_resume(state):
        return PlannerDecision(
            "finish",
            None,
            "resume payload already contains completed downstream outputs",
            "optional",
            ["resume_from provided render_result or quote_document outputs"],
        )
    if not state.template_selection_result:
        force_template_type = state.business_context.get("force_template_type")
        if isinstance(force_template_type, str) and force_template_type.strip():
            return PlannerDecision(
                "skip",
                "quote_template_select_skill",
                "template type already forced by business_context",
                "optional",
            )
        return _run_required("quote_template_select_skill", registry)
    if not state.prepare_result:
        return _run_required("quote_request_prepare_skill", registry)
    if not state.feedback_reference:
        return _run_optional("quote_feedback_reference_skill", registry)
    if not state.feasibility_result:
        return _run_required("quote_feasibility_check_skill", registry)
    if _should_pause_after_feasibility(state):
        return PlannerDecision(
            "pause",
            None,
            "manual confirmation required before pricing",
            "required",
            ["feasibility_result indicates not_ready or blocking questions"],
        )
    if not state.historical_reference:
        historical_assessment = _assess_historical_reference_value(state)
        if historical_assessment["skip"]:
            return PlannerDecision(
                "skip",
                "historical_quote_reference_skill",
                historical_assessment["reason"],
                "optional",
                historical_assessment["notes"],
            )
        return PlannerDecision(
            "run_skill",
            "historical_quote_reference_skill",
            historical_assessment["reason"],
            "optional",
            historical_assessment["notes"],
        )
    if not state.pricing_result:
        return _run_required("quote_pricing_skill", registry)
    if not state.quote_document:
        return _run_required("quote_review_output_skill", registry)
    if not state.render_result:
        if _should_render(state):
            return _run_optional("quote_pdf_render_skill", registry)
        return PlannerDecision("finish", None, "rendering not requested", "optional")
    return PlannerDecision("finish", None, "workflow complete")


def _should_pause_after_feasibility(state: WorkflowState) -> bool:
    if _should_render(state):
        return False
    if state.business_context.get("interactive_mode") is not True:
        return False
    if state.template_selection_result.get("needs_manual_confirmation") is True:
        return True
    quote_scope = state.feasibility_result.get("quote_scope")
    if quote_scope == "not_ready":
        return True
    questions = state.feasibility_result.get("questions_for_user")
    return isinstance(questions, list) and len(questions) > 0 and quote_scope != "full"


def _assess_historical_reference_value(state: WorkflowState) -> dict[str, Any]:
    notes: list[str] = []
    has_strong_pricing_signals = _has_strong_pricing_signals(state)
    needs_history_for_structure = _needs_history_for_structure(state)

    if state.business_context.get("skip_historical_reference") is True:
        return {
            "skip": True,
            "reason": "historical reference skipped by explicit business override",
            "notes": ["business_context.skip_historical_reference=true"],
        }

    quotable_items = state.feasibility_result.get("quotable_items")
    if not isinstance(quotable_items, list) or not quotable_items:
        return {
            "skip": True,
            "reason": "historical reference skipped because no quotable items remain",
            "notes": ["feasibility_result.quotable_items is empty"],
        }

    quote_scope = state.feasibility_result.get("quote_scope")
    if quote_scope == "not_ready":
        return {
            "skip": True,
            "reason": "historical reference skipped because quote scope is not ready",
            "notes": ["feasibility_result.quote_scope=not_ready"],
        }

    review_flags = state.feasibility_result.get("review_flags")
    flag_codes = {
        str(flag.get("flag_code") or "")
        for flag in review_flags
        if isinstance(review_flags, list) and isinstance(flag, dict)
    }
    if "critical_context_missing" in flag_codes and quote_scope != "full":
        return {
            "skip": True,
            "reason": "historical reference skipped because critical context is still missing",
            "notes": [
                "feasibility_result.review_flags contains critical_context_missing"
            ],
        }

    template_type = state.selected_template_type
    if has_strong_pricing_signals:
        notes.append("query already contains pricing-friendly signals")
    else:
        notes.append("query lacks strong pricing-friendly signals")

    if (
        state.business_context.get("prefer_fast_quote") is True
        and not needs_history_for_structure
    ):
        return {
            "skip": True,
            "reason": "historical reference skipped for fast quote mode with low structural value",
            "notes": ["business_context.prefer_fast_quote=true", *notes],
        }

    if template_type in {"product", "digital-product"} and quote_scope == "full":
        return {
            "skip": True,
            "reason": "historical reference skipped because current template can price from deterministic inputs",
            "notes": [f"selected_template_type={template_type}", "quote_scope=full"],
        }

    if needs_history_for_structure:
        notes.append("history can still improve pricing structure or remarks")
        return {
            "skip": False,
            "reason": "historical reference selected because current quote still benefits from structural guidance",
            "notes": notes,
        }

    if quote_scope == "full" and has_strong_pricing_signals:
        return {
            "skip": True,
            "reason": "historical reference skipped because current quote can proceed from direct structured inputs",
            "notes": notes,
        }

    return {
        "skip": False,
        "reason": "historical reference selected because the current quote may benefit from pricing and remark context",
        "notes": notes,
    }


def _needs_history_for_structure(state: WorkflowState) -> bool:
    quote_request = state.quote_request
    service_context = (
        quote_request.get("service_context")
        if isinstance(quote_request.get("service_context"), dict)
        else {}
    )
    spare_parts_context = (
        quote_request.get("spare_parts_context")
        if isinstance(quote_request.get("spare_parts_context"), dict)
        else {}
    )

    if state.business_context.get("force_multi_option") is True:
        return True
    if service_context.get("needs_multi_option") is True:
        return True
    if state.business_context.get("option_hints"):
        return True

    spare_parts_items = spare_parts_context.get("spare_parts_items")
    has_spare_parts = bool(spare_parts_context.get("has_spare_parts")) or (
        isinstance(spare_parts_items, list) and len(spare_parts_items) > 0
    )
    supply_mode = str(spare_parts_context.get("spare_parts_supply_mode") or "").strip()
    if has_spare_parts and supply_mode == "company_supply":
        return True

    quote_scope = state.feasibility_result.get("quote_scope")
    return quote_scope == "partial"


def _has_strong_pricing_signals(state: WorkflowState) -> bool:
    candidate_items = state.quote_request.get("candidate_items")
    if not isinstance(candidate_items, list) or not candidate_items:
        return False

    rich_items = 0
    for item in candidate_items:
        if not isinstance(item, dict):
            continue
        work_scope = item.get("work_scope")
        pricing_clues = item.get("pricing_clues")
        labor_hint = item.get("labor_hint")
        quantity_hint = item.get("quantity_hint")
        unit_hint = item.get("unit_hint")
        if isinstance(work_scope, list) and work_scope:
            rich_items += 1
            continue
        if isinstance(pricing_clues, list) and pricing_clues:
            rich_items += 1
            continue
        if isinstance(labor_hint, list) and labor_hint:
            rich_items += 1
            continue
        if quantity_hint is not None and unit_hint is not None:
            rich_items += 1

    return rich_items >= max(1, len(candidate_items) // 2)


def _should_render(state: WorkflowState) -> bool:
    if state.render_options.get("enabled") is True:
        return True
    languages = state.render_options.get("languages")
    return isinstance(languages, list) and len(languages) > 0


def _should_finish_from_resume(state: WorkflowState) -> bool:
    resume_from = state.business_context.get("resume_from")
    if not isinstance(resume_from, str) or not resume_from.strip():
        return False
    return state.business_context.get("_resume_has_completed_outputs") is True


def _run_required(
    skill_name: str, registry: dict[str, SkillRegistryEntry]
) -> PlannerDecision:
    return PlannerDecision(
        "run_skill",
        skill_name,
        f"required stage: {registry[skill_name].stage}",
        "required",
    )


def _run_optional(
    skill_name: str, registry: dict[str, SkillRegistryEntry]
) -> PlannerDecision:
    return PlannerDecision(
        "run_skill",
        skill_name,
        f"optional stage chosen: {registry[skill_name].stage}",
        "optional",
    )
