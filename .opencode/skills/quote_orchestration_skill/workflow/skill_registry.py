from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRegistryEntry:
    skill_name: str
    stage: str
    optional: bool
    supports_pause: bool
    when_to_use: list[str]
    when_not_to_use: list[str]
    core_behavior: list[str]


def load_skill_registry(skills_dir: Path) -> dict[str, SkillRegistryEntry]:
    return {
        "quote_template_select_skill": _load_entry(
            skills_dir / "quote_template_select_skill" / "SKILL.md",
            "quote_template_select_skill",
            "template_select",
            True,
            True,
        ),
        "quote_request_prepare_skill": _load_entry(
            skills_dir / "quote_request_prepare_skill" / "SKILL.md",
            "quote_request_prepare_skill",
            "prepare",
            False,
            False,
        ),
        "quote_feasibility_check_skill": _load_entry(
            skills_dir / "quote_feasibility_check_skill" / "SKILL.md",
            "quote_feasibility_check_skill",
            "feasibility",
            False,
            True,
        ),
        "historical_quote_reference_skill": _load_entry(
            skills_dir / "historical_quote_reference_skill" / "SKILL.md",
            "historical_quote_reference_skill",
            "historical_reference",
            True,
            False,
        ),
        "quote_pricing_skill": _load_entry(
            skills_dir / "quote_pricing_skill" / "SKILL.md",
            "quote_pricing_skill",
            "pricing",
            False,
            False,
        ),
        "quote_review_output_skill": _load_entry(
            skills_dir / "quote_review_output_skill" / "SKILL.md",
            "quote_review_output_skill",
            "review_output",
            False,
            False,
        ),
        "quote_pdf_render_skill": _load_entry(
            skills_dir / "quote_pdf_render_skill" / "SKILL.md",
            "quote_pdf_render_skill",
            "pdf_render",
            True,
            False,
        ),
    }


def _load_entry(
    skill_md_path: Path,
    skill_name: str,
    stage: str,
    optional: bool,
    supports_pause: bool,
) -> SkillRegistryEntry:
    content = skill_md_path.read_text(encoding="utf-8")
    return SkillRegistryEntry(
        skill_name=skill_name,
        stage=stage,
        optional=optional,
        supports_pause=supports_pause,
        when_to_use=_extract_section_lines(content, "## When to Use（何时使用）"),
        when_not_to_use=_extract_section_lines(
            content, "## When NOT to Use（何时不用）"
        ),
        core_behavior=_extract_section_lines(content, "## Core Behavior（核心行为）"),
    )


def _extract_section_lines(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    try:
        start_index = lines.index(heading)
    except ValueError:
        return []
    collected: list[str] = []
    for line in lines[start_index + 1 :]:
        if line.startswith("## "):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            collected.append(stripped[2:])
    return collected
