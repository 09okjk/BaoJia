from __future__ import annotations

from .state import WorkflowState


def can_run_skill(state: WorkflowState, skill_name: str) -> bool:
    if skill_name == "quote_template_select_skill":
        return bool(state.assessment_report)
    if skill_name == "quote_request_prepare_skill":
        return bool(state.assessment_report)
    if skill_name == "quote_feedback_reference_skill":
        return bool(state.quote_request)
    if skill_name in {
        "quote_feasibility_check_skill",
        "historical_quote_reference_skill",
        "quote_pricing_skill",
    }:
        return bool(state.quote_request)
    if skill_name == "quote_review_output_skill":
        return bool(state.pricing_result)
    if skill_name == "quote_pdf_render_skill":
        return bool(state.quote_document)
    return False
