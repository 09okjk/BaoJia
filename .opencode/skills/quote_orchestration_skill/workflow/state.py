from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowState:
    assessment_report: dict[str, Any]
    customer_context: dict[str, Any]
    business_context: dict[str, Any]
    render_options: dict[str, Any]
    template_selection_result: dict[str, Any] = field(default_factory=dict)
    prepare_result: dict[str, Any] = field(default_factory=dict)
    feedback_reference: dict[str, Any] = field(default_factory=dict)
    feasibility_result: dict[str, Any] = field(default_factory=dict)
    historical_reference: dict[str, Any] = field(default_factory=dict)
    pricing_result: dict[str, Any] = field(default_factory=dict)
    quote_document: dict[str, Any] = field(default_factory=dict)
    render_result: dict[str, Any] = field(default_factory=dict)
    orchestration_status: str = "running"
    draft_status: str = "drafting"
    user_decision: str | None = None
    pause_reason: str | None = None
    execution_trace: list[dict[str, Any]] = field(default_factory=list)
    planner_trace: list[dict[str, Any]] = field(default_factory=list)
    skipped_skills: list[dict[str, Any]] = field(default_factory=list)
    applied_planner_strategies: list[dict[str, Any]] = field(default_factory=list)

    @property
    def selected_template_type(self) -> str | None:
        template_type = self.template_selection_result.get("template_type")
        return template_type if isinstance(template_type, str) else None

    @property
    def quote_request(self) -> dict[str, Any]:
        quote_request = self.prepare_result.get("quote_request")
        return quote_request if isinstance(quote_request, dict) else {}

    def to_result(self) -> dict[str, Any]:
        result = {
            "template_selection_result": self.template_selection_result,
            "prepare_result": self.prepare_result,
            "feedback_reference": self.feedback_reference,
            "feasibility_result": self.feasibility_result,
            "historical_reference": self.historical_reference,
            "pricing_result": self.pricing_result,
            "quote_document": self.quote_document,
            "orchestration_status": self.orchestration_status,
            "draft_status": self.draft_status,
            "user_decision": self.user_decision,
            "execution_trace": self.execution_trace,
            "planner_trace": self.planner_trace,
            "skipped_skills": self.skipped_skills,
            "applied_planner_strategies": self.applied_planner_strategies,
        }
        if self.quote_document and self.draft_status in {
            "awaiting_user_decision",
            "revising",
            "accepted",
        }:
            result["user_decision_prompt"] = {
                "message": "Please choose whether to continue revising this draft or confirm the current version.",
                "options": ["continue_revising", "confirm_current_version"],
            }
        if self.pause_reason:
            result["pause_reason"] = self.pause_reason
        if self.render_result:
            result["render_result"] = self.render_result
        if self.orchestration_status == "paused":
            questions = self.feasibility_result.get("questions_for_user")
            review_flags = self.feasibility_result.get("review_flags")
            result["questions_for_user"] = (
                questions if isinstance(questions, list) else []
            )
            result["review_flags"] = (
                review_flags if isinstance(review_flags, list) else []
            )
            result["clarification_context"] = {
                "resume_supported": True,
                "missing_fields": self.feasibility_result.get("missing_fields", []),
                "question_topics": [
                    question.get("topic")
                    for question in result["questions_for_user"]
                    if isinstance(question, dict)
                    and isinstance(question.get("topic"), str)
                ],
            }
        return result


def build_initial_state(payload: dict[str, Any]) -> WorkflowState:
    return WorkflowState(
        assessment_report=_as_dict(payload.get("assessment_report")),
        customer_context=_as_dict(payload.get("customer_context")),
        business_context=_as_dict(payload.get("business_context")),
        render_options=_as_dict(payload.get("render_options")),
    )


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
