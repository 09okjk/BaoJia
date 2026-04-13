from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import escape
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, FileSystemLoader, select_autoescape

from py_pdf.domain.models import EngineeringPdfContext


def _format_date(value: Any, fmt: str = "%Y/%m/%d") -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(fmt)
    if isinstance(value, date):
        return value.strftime(fmt)
    if isinstance(value, str):
        # 兼容 yyyy/MM/dd 或 ISO format
        value = value.replace("/", "-")
        try:
            return datetime.fromisoformat(value).strftime(fmt)
        except ValueError:
            try:
                return date.fromisoformat(value).strftime(fmt)
            except ValueError:
                return value
    return str(value)


def _permil(value: Any, symbol: str = "") -> str:
    if value is None:
        return ""

    parsed_numeric = False

    # 格式化数字核心逻辑
    def format_num(val: Any) -> str:
        if isinstance(val, bool):
            return str(val)
        if isinstance(val, int):
            return f"{val:,}"
        if isinstance(val, float):
            text = f"{val:,.2f}"
            return text.rstrip("0").rstrip(".")
        if isinstance(val, Decimal):
            normalized = val.normalize()
            if normalized == normalized.to_integral():
                return f"{int(normalized):,}"
            text = f"{normalized:,.2f}"
            return text.rstrip("0").rstrip(".")
        return str(val)

    formatted_val = ""
    if isinstance(value, (int, float, Decimal, bool)):
        formatted_val = format_num(value)
    elif isinstance(value, str):
        # 尝试清理货币符号和逗号 (e.g. "¥555" -> "555")
        clean_val = value.replace("¥", "").replace("$", "").replace(",", "").strip()
        try:
            dec = Decimal(clean_val)
            formatted_val = format_num(dec)
            parsed_numeric = True
        except (InvalidOperation, ValueError, TypeError):
            formatted_val = value
    else:
        try:
            dec = Decimal(str(value))
            formatted_val = format_num(dec)
        except (InvalidOperation, ValueError, TypeError):
            formatted_val = str(value)

    # 如果已经是字符串且无法转换为数字，不添加符号；或者值为空，也不添加
    if not formatted_val or (
        isinstance(value, str) and formatted_val == value and not parsed_numeric
    ):
        return formatted_val

    return f"{symbol}{formatted_val}" if symbol else formatted_val


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_form_data(form_data: Mapping[str, Any] | None) -> dict[str, Any]:
    if not form_data:
        return {
            "descriptions": [],
            "summary": [],
            "remarks": [],
            "servicePaymentTerms": [],
            "paymentTermsForSpareParts": [],
        }

    normalized = dict(form_data)
    normalized["descriptions"] = _ensure_list(normalized.get("descriptions"))
    normalized["summary"] = _ensure_list(normalized.get("summary"))
    normalized["remarks"] = _ensure_list(normalized.get("remarks"))
    normalized["servicePaymentTerms"] = _ensure_list(
        normalized.get("servicePaymentTerms")
    )
    normalized["paymentTermsForSpareParts"] = _ensure_list(
        normalized.get("paymentTermsForSpareParts")
    )
    return normalized


def _create_env(template_dir: Path) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(enabled_extensions=("html", "xml", "j2")),
    )
    env.filters["format_date"] = _format_date
    env.filters["permil"] = _permil
    env.filters["nl2br"] = lambda value: escape(str(value or "")).replace(
        "\n", "<br />"
    )
    return env


def render_engineering_pdf(context: EngineeringPdfContext | Mapping[str, Any]) -> str:
    if isinstance(context, EngineeringPdfContext):
        payload: dict[str, Any] = {
            "form_data": _normalize_form_data(context.form_data),
            "quotation_template": context.quotation_template,
            "display_discounts": context.display_discounts,
            "tax_rate": context.tax_rate,
            "currency_name": context.currency_name,
            "currency_symbol": context.currency_symbol,
            "quotation_type": context.quotation_type,
            "display_language": context.display_language,
        }
    else:
        payload = dict(context)
        payload["form_data"] = _normalize_form_data(payload.get("form_data"))
        payload.setdefault("quotation_template", 1)
        payload.setdefault("display_discounts", 0)
        payload.setdefault("tax_rate", False)
        payload.setdefault("currency_name", "")
        payload.setdefault("currency_symbol", "")
        payload.setdefault("quotation_type", 1)
        payload.setdefault("display_language", "auto")

    template_dir = Path(__file__).resolve().parent / "templates"
    payload["template_assets_base"] = (template_dir / "assets").resolve().as_uri()
    env = _create_env(template_dir)
    template = env.get_template("engineering_pdf.html.j2")
    return template.render(**payload)
