from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate

from models import EngineeringPdfContext


class QuoteDocumentError(ValueError):
    pass


class QuoteDocumentMapper:
    _CURRENCY_SYMBOLS = {
        "USD": "$",
        "US$": "$",
        "RMB": "￥",
        "CNY": "￥",
        "EUR": "€",
        "GBP": "£",
        "SGD": "S$",
        "JPY": "¥",
        "HKD": "HK$",
    }

    _ZH_TRANSLATIONS = {
        "Option A Standard quotation": "方案 A 标准报价",
        "Option B Service only quotation": "方案 B 仅服务报价",
        "HCU system overhaul": "HCU 系统大修",
        "HCU system overhaul and calibration": "HCU 系统大修",
        "MPC system inspection": "MPC 系统检查",
        "MPC system inspection and health check": "MPC 系统检查",
        "64k running hours overhaul scope for HCU system": "HCU 系统 64000 小时大修范围",
        "64k running hours overhaul scope for HCU system on MAN B&W 6S60ME-C8.2.": "HCU 系统 64000 小时大修范围",
        "64k running hours inspection scope for MPC system": "MPC 系统 64000 小时检查范围",
        "64k running hours inspection scope for MPC system on MAN B&W 6S60ME-C8.2.": "MPC 系统 64000 小时检查范围",
        "Overhaul ELFI valve/Multiway valve units": "大修 ELFI 阀 / 多路阀单元",
        "Overhaul ELFI valve and multiway valve units": "大修 ELFI 阀 / 多路阀单元",
        "Exhaust valve actuator and fuel oil pressure booster overhauling": "大修排气阀执行器及燃油增压单元",
        "Overhaul exhaust valve actuator and fuel oil pressure booster": "大修排气阀执行器及燃油增压单元",
        "Cylinder lubricator system overhauling": "大修气缸注油器系统",
        "Overhaul cylinder lubricator system": "大修气缸注油器系统",
        "Accumulator overhauling and refill with nitrogen": "大修蓄能器并补充氮气",
        "Overhaul accumulator and refill with nitrogen": "大修蓄能器并补充氮气",
        "Maintenance and overhauling of HPS": "HPS 系统检修及大修",
        "Maintenance and overhaul of HPS": "HPS 系统检修及大修",
        "MPC health inspection and replacement": "MPC 健康检查及更换",
        "MPC health check": "MPC 健康检查及更换",
        "Inspection of MPC status and replacement readiness": "MPC 状态及更换准备检查",
        "Check UPS battery related condition": "UPS 电池相关状态检查",
        "Transportation": "交通费",
        "Accommodation": "住宿费",
        "Dockyard management fee": "船厂管理费",
        "Maritime reporting / safety permit": "海事申报 / 安全许可费用",
        "HPS accumulators repair kit": "HPS 蓄能器修理包",
        "HCU accumulators repair kit": "HCU 蓄能器修理包",
        "Nitrogen for refilling": "补充氮气",
        "FIVA valves pilot valves": "FIVA 阀先导阀",
        "Fuel booster units top covers and suction valves": "燃油增压单元上盖及吸入阀",
        "Exhaust valve actuators safety valves": "排气阀执行器安全阀",
        "MPC & UPS batteries": "MPC 与 UPS 电池",
        "MPC and UPS batteries": "MPC 与 UPS 电池",
        "Supply responsibility to be confirmed": "供货责任待确认",
        "If the FIVA valve need to overhaul at workshop, the cost will charged extra": "如 FIVA 阀需进车间大修，相关费用将另行计取。",
        "repair kits for FIVA valve": "FIVA 阀修理包需另行确认。",
        "Payment within 30 days upon invoice date.": "付款条件：发票日起 30 天内付款。",
        "Quotation validity: 30 days": "报价有效期：30 天。",
        "Spare parts warranty period shall follow supplier confirmation.": "备件质保期以供应商最终确认为准。",
        "Inspection and troubleshooting items carry no service warranty.": "检查与故障排查项目不提供服务质保。",
        "Warranty Compensate Amount: 5 times of the service cost at max.": "质保赔偿上限为服务费的 5 倍。",
        "Warranty Compensate Amount: 5times of the service cost at max.": "质保赔偿上限为服务费的 5 倍。",
    }

    def __init__(
        self,
        payload: Mapping[str, Any],
        *,
        schema_path: Path | None = None,
        display_language: str = "auto",
    ) -> None:
        self._payload = dict(payload)
        self._schema_path = schema_path
        self._display_language = display_language

    def to_engineering_context(self) -> EngineeringPdfContext:
        quote_document = self._extract_quote_document(self._payload)
        self._validate_quote_document(quote_document)

        header = quote_document.get("header", {})
        footer = quote_document.get("footer", {})
        quotation_options = quote_document.get("quotation_options", [])
        currency_name = str(header.get("currency", "") or "")
        currency_symbol = self._currency_symbol(currency_name)

        descriptions = self._build_descriptions(
            quotation_options, currency_name, currency_symbol
        )
        remarks = self._build_remarks(quotation_options, footer)
        service_payment_terms = self._build_service_payment_terms(footer)

        return EngineeringPdfContext(
            form_data={
                "vesselName": str(header.get("vessel_name", "") or ""),
                "date": str(header.get("date", "") or ""),
                "imoNo": str(header.get("imo_no", "") or ""),
                "vesselType": str(header.get("vessel_type", "") or ""),
                "customerName": str(header.get("customer_name", "") or ""),
                "servicePort": str(header.get("service_port", "") or ""),
                "attention": str(header.get("attention", "") or ""),
                "wkOfferNo": str(header.get("wk_offer_no", "") or ""),
                "youRefNo": str(header.get("your_ref_no", "") or ""),
                "quotationValidity": str(header.get("quotation_validity", "") or ""),
                "poNo": str(header.get("po_no", "") or ""),
                "inquiryInitiator": str(header.get("pic_of_winkong", "") or ""),
                "currency": currency_name,
                "descriptions": descriptions,
                "summary": [self._build_summary(footer, currency_name)],
                "remarks": remarks,
                "servicePaymentTerms": service_payment_terms,
                "paymentTermsForSpareParts": [],
            },
            quotation_template=1,
            display_discounts=1 if self._has_discount(quotation_options) else 0,
            tax_rate=False,
            currency_name=currency_name,
            currency_symbol=currency_symbol,
            quotation_type=1,
            inquiry_no=str(header.get("wk_offer_no", "") or ""),
            display_language=self._display_language,
        )

    def _extract_quote_document(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        candidate = payload.get("quote_document", payload)
        if not isinstance(candidate, dict):
            raise QuoteDocumentError("quote_document is required and must be an object")
        return dict(candidate)

    def _validate_quote_document(self, quote_document: Mapping[str, Any]) -> None:
        if self._schema_path is None:
            return
        schema = json.loads(self._schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema_validate(instance=dict(quote_document), schema=schema)
        except ValidationError as exc:
            path = ".".join(str(part) for part in exc.absolute_path) or "$"
            raise QuoteDocumentError(
                f"QuoteDocument schema validation failed at {path}: {exc.message}"
            ) from exc

    def _has_discount(self, quotation_options: Any) -> bool:
        if not isinstance(quotation_options, list):
            return False
        for option in quotation_options:
            if not isinstance(option, dict):
                continue
            sections = option.get("sections")
            if not isinstance(sections, list):
                continue
            for section in sections:
                if not isinstance(section, dict):
                    continue
                groups = section.get("groups")
                if not isinstance(groups, list):
                    continue
                for group in groups:
                    if not isinstance(group, dict):
                        continue
                    lines = group.get("lines")
                    if not isinstance(lines, list):
                        continue
                    for line in lines:
                        if isinstance(line, dict) and isinstance(
                            line.get("discount"), dict
                        ):
                            return True
        return False

    def _build_descriptions(
        self, quotation_options: Any, currency_name: str, currency_symbol: str
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not isinstance(quotation_options, list):
            return rows

        multi_option = (
            len([item for item in quotation_options if isinstance(item, dict)]) > 1
        )

        option_counter = 0
        for option in quotation_options:
            if not isinstance(option, dict):
                continue
            option_counter += 1
            option_prefix = self._option_prefix(option_counter) if multi_option else ""
            option_title = self._display_text(str(option.get("title", "") or ""))
            if option_title and multi_option:
                rows.append(self._title_row(index=option_prefix, content=option_title))

            sections = option.get("sections")
            if not isinstance(sections, list):
                continue

            service_rows: list[dict[str, Any]] = []
            other_rows: list[dict[str, Any]] = []
            spare_part_rows: list[dict[str, Any]] = []
            seen_pending_scopes: set[str] = set()
            group_counter = 0
            for section in sections:
                if not isinstance(section, dict):
                    continue
                section_type = str(section.get("section_type", "") or "")
                section_rows = self._target_section_rows(
                    section_type=section_type,
                    service_rows=service_rows,
                    other_rows=other_rows,
                    spare_part_rows=spare_part_rows,
                )

                groups = section.get("groups")
                if not isinstance(groups, list):
                    continue
                for group in groups:
                    if not isinstance(group, dict):
                        continue
                    numbered_service_section = section_type == "service"
                    if numbered_service_section:
                        group_counter += 1
                        group_no = str(group_counter)
                    else:
                        group_no = ""
                    group_title = self._display_text(str(group.get("title", "") or ""))
                    group_label = group_title
                    if not group_label and group_no:
                        group_label = group_no
                    lines = group.get("lines")
                    if not isinstance(lines, list):
                        continue

                    if not numbered_service_section:
                        section_rows.extend(
                            self._build_non_service_group_rows(
                                lines=lines,
                                group_title=group_title,
                                seen_pending_scopes=seen_pending_scopes,
                                section_type=section_type,
                                currency_name=currency_name,
                                currency_symbol=currency_symbol,
                            )
                        )
                        continue

                    if group_label:
                        section_rows.append(
                            self._group_row(
                                index=self._compose_index(option_prefix, group_no),
                                content=group_label,
                            )
                        )

                    has_priced_service_row = False
                    child_index = 0
                    for line in lines:
                        if not isinstance(line, dict):
                            continue
                        line_type = str(line.get("line_type", "") or "")
                        should_number_line = line_type == "priced" or (
                            line_type == "pending" and not has_priced_service_row
                        )
                        row = self._line_to_description(
                            line,
                            group_no=group_no,
                            child_index=child_index + 1
                            if should_number_line
                            else child_index,
                            group_title=group_title,
                            option_prefix=option_prefix,
                            numbered_service_section=should_number_line,
                            currency_name=currency_name,
                            currency_symbol=currency_symbol,
                        )
                        if row is None:
                            continue
                        if should_number_line:
                            child_index += 1
                        if line_type == "priced":
                            has_priced_service_row = True
                        section_rows.append(row)

            rows.extend(service_rows)
            rows.extend(other_rows)
            rows.extend(spare_part_rows)

            option_summary = option.get("summary")
            if isinstance(option_summary, dict):
                summary_label = self._option_summary_label(option_title)
                rows.append(
                    self._description_row(
                        index="",
                        content=summary_label,
                        price=self._summary_display(
                            option_summary, "service_charge", currency_name
                        ),
                        unit="",
                        qty="",
                        discount="",
                        amount=self._summary_display(
                            option_summary, "total", currency_name
                        ),
                    )
                )

        return rows

    def _option_summary_label(self, option_title: str) -> str:
        if self._display_language == "en":
            return f"Option Summary - {option_title}" if option_title else "Summary"
        return f"方案合计 - {option_title}" if option_title else "合计"

    def _target_section_rows(
        self,
        *,
        section_type: str,
        service_rows: list[dict[str, Any]],
        other_rows: list[dict[str, Any]],
        spare_part_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if section_type == "service":
            return service_rows
        if section_type == "spare_parts":
            return spare_part_rows
        return other_rows

    def _build_non_service_group_rows(
        self,
        *,
        lines: list[Any],
        group_title: str,
        seen_pending_scopes: set[str],
        section_type: str,
        currency_name: str,
        currency_symbol: str,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        visible_lines = [line for line in lines if isinstance(line, dict)]
        if not visible_lines:
            if group_title:
                rows.append(self._group_row(index="", content=group_title))
            return rows

        priced_line = next(
            (
                line
                for line in visible_lines
                if str(line.get("line_type", "") or "") == "priced"
            ),
            None,
        )
        pending_line = next(
            (
                line
                for line in visible_lines
                if str(line.get("line_type", "") or "") == "pending"
            ),
            None,
        )

        if priced_line is not None:
            priced_description = self._customer_facing_description(
                priced_line, group_title=group_title
            )
            merged_title = group_title
            if priced_description and priced_description != group_title:
                merged_title = (
                    f"{group_title} - {priced_description}"
                    if group_title
                    else priced_description
                )
            rows.append(
                self._description_row(
                    index="",
                    content=merged_title,
                    price=self._display_money(
                        str(priced_line.get("unit_price_display", "") or ""),
                        str(priced_line.get("currency", "") or currency_name),
                        currency_symbol,
                    ),
                    unit=str(priced_line.get("unit", "") or ""),
                    qty=str(priced_line.get("qty_display", "") or ""),
                    discount=str(
                        priced_line.get("discount", {}).get("display", "")
                        if isinstance(priced_line.get("discount"), dict)
                        else ""
                    ),
                    amount=self._display_money(
                        str(priced_line.get("amount_display", "") or ""),
                        str(priced_line.get("currency", "") or currency_name),
                        currency_symbol,
                    ),
                )
            )
        elif pending_line is not None:
            if section_type == "spare_parts":
                merged_title = (
                    f"{group_title}（待确认）"
                    if self._display_language != "en"
                    else f"{group_title} (Pending confirmation)"
                )
            else:
                merged_title = self._customer_facing_description(
                    pending_line, group_title=group_title
                )
            pending_scope_key = self._pending_scope_key(merged_title)
            if pending_scope_key in seen_pending_scopes:
                merged_title = (
                    f"{group_title}（待确认）"
                    if self._display_language != "en"
                    else f"{group_title} (Pending confirmation)"
                )
            elif pending_scope_key:
                seen_pending_scopes.add(pending_scope_key)
            rows.append(
                self._description_row(
                    index="",
                    content=merged_title,
                    price="",
                    unit="",
                    qty="",
                    discount="",
                    amount=self._display_money(
                        str(pending_line.get("amount_display", "") or ""),
                        str(pending_line.get("currency", "") or currency_name),
                        currency_symbol,
                    ),
                )
            )
        elif group_title:
            rows.append(self._group_row(index="", content=group_title))

        for line in visible_lines:
            if line is priced_line or line is pending_line:
                continue
            description = self._customer_facing_description(
                line, group_title=group_title
            )
            if not description:
                continue
            line_type = str(line.get("line_type", "") or "")
            normalized_group_title = self._normalize_display_label(group_title)
            normalized_description = self._normalize_display_label(description)
            if line_type in {
                "scope_note",
                "technical_note",
                "commercial_note",
                "assumption_note",
                "note",
            }:
                if self._is_short_auxiliary_note(description):
                    continue
                rows.append(
                    self._description_row(
                        index="",
                        content=description,
                        price="",
                        unit="",
                        qty="",
                        discount="",
                        amount="",
                    )
                )
                continue
            if line_type in {"pending", "conditional", "extra", "optional"}:
                if (
                    normalized_description
                    and normalized_description == normalized_group_title
                ):
                    continue
                if self._is_short_auxiliary_note(description):
                    continue
                rows.append(
                    self._description_row(
                        index="",
                        content=description,
                        price="",
                        unit="",
                        qty="",
                        discount="",
                        amount=self._display_money(
                            str(line.get("amount_display", "") or ""),
                            str(line.get("currency", "") or currency_name),
                            currency_symbol,
                        ),
                    )
                )
                continue
            if description == group_title or self._is_short_auxiliary_note(description):
                continue
            rows.append(
                self._description_row(
                    index="",
                    content=description,
                    price="",
                    unit="",
                    qty="",
                    discount="",
                    amount="",
                )
            )

        return rows

    def _pending_scope_key(self, text: str) -> str:
        normalized = text.strip().lower()
        normalized = normalized.replace("（待确认）", "")
        normalized = normalized.replace("(pending confirmation)", "")
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _line_to_description(
        self,
        line: Mapping[str, Any],
        *,
        group_no: str,
        child_index: int,
        group_title: str,
        option_prefix: str,
        numbered_service_section: bool,
        currency_name: str,
        currency_symbol: str,
    ) -> dict[str, Any] | None:
        line_type = str(line.get("line_type", "") or "")
        description = self._customer_facing_description(line, group_title=group_title)
        if not description:
            return None

        discount_text = ""
        if isinstance(line.get("discount"), dict):
            discount_text = str(line.get("discount", {}).get("display", "") or "")

        row_index = ""
        if numbered_service_section and group_no and child_index == 1:
            row_index = self._compose_index(option_prefix, f"{group_no}.{child_index}")

        amount_text = self._display_money(
            str(line.get("amount_display", "") or ""),
            str(line.get("currency", "") or currency_name),
            currency_symbol,
        )
        unit_price_text = self._display_money(
            str(line.get("unit_price_display", "") or ""),
            str(line.get("currency", "") or currency_name),
            currency_symbol,
        )
        unit_text = str(line.get("unit", "") or "")
        qty_text = str(line.get("qty_display", "") or "")

        if line_type in {
            "scope_note",
            "technical_note",
            "commercial_note",
            "assumption_note",
            "note",
        }:
            row_index = ""
            unit_price_text = ""
            unit_text = ""
            qty_text = ""
            discount_text = ""
            amount_text = ""
        elif line_type in {"pending", "conditional", "extra", "optional"}:
            row_index = ""
            unit_price_text = ""
            unit_text = ""
            qty_text = ""
            discount_text = ""

        return self._description_row(
            index=row_index,
            content=description,
            price=unit_price_text,
            unit=unit_text,
            qty=qty_text,
            discount=discount_text,
            amount=amount_text,
        )

    def _build_summary(
        self, footer: Mapping[str, Any], currency_name: str
    ) -> dict[str, Any]:
        summary = footer.get("summary")
        if not isinstance(summary, dict):
            return {"serviceCharge": "", "sparePartsFee": "", "other": "", "total": ""}
        return {
            "serviceCharge": self._summary_display(
                summary, "service_charge", currency_name
            ),
            "sparePartsFee": self._summary_display(
                summary, "spare_parts_fee", currency_name
            ),
            "other": self._summary_display(summary, "other", currency_name),
            "total": self._summary_display(summary, "total", currency_name),
        }

    def _summary_display(
        self, summary: Mapping[str, Any], key: str, currency_name: str
    ) -> str:
        value = summary.get(key)
        if not isinstance(value, dict):
            return ""
        display = str(value.get("display", "") or "")
        currency = str(value.get("currency", "") or currency_name)
        if display and currency and value.get("value_type") == "amount":
            symbol = self._currency_symbol(currency)
            if symbol:
                return f"{symbol}{display}"
            return f"{currency} {display}"
        return display

    def _display_money(
        self, display: str, currency_name: str, default_symbol: str
    ) -> str:
        cleaned = display.strip()
        if not cleaned:
            return ""
        if not any(char.isdigit() for char in cleaned):
            return cleaned
        if any(symbol in cleaned for symbol in ["$", "￥", "¥", "€", "£"]):
            return cleaned
        symbol = self._currency_symbol(currency_name) or default_symbol
        if symbol:
            return f"{symbol}{cleaned}"
        if currency_name:
            return f"{currency_name} {cleaned}"
        return cleaned

    def _build_remarks(
        self, quotation_options: Any, footer: Mapping[str, Any]
    ) -> list[str]:
        remarks: list[str] = []
        normalized_seen: set[str] = set()
        payment_term_texts = {
            self._normalize_remark_text(item)
            for item in self._build_service_payment_terms(footer)
            if item
        }
        option_remark_map: dict[str, set[str]] = {}
        option_remark_labels: dict[str, str] = {}

        if isinstance(quotation_options, list):
            for option in quotation_options:
                if not isinstance(option, dict):
                    continue
                option_title = str(option.get("title", "") or "")
                option_remarks = option.get("remarks")
                if not isinstance(option_remarks, list):
                    continue
                for remark in option_remarks:
                    if not isinstance(remark, dict):
                        continue
                    text = str(remark.get("text", "") or "")
                    if not text:
                        continue
                    normalized_text = self._normalize_remark_text(text)
                    if normalized_text in payment_term_texts:
                        continue
                    option_remark_map.setdefault(normalized_text, set()).add(
                        option_title
                    )
                    option_remark_labels.setdefault(normalized_text, text)

        for normalized_text, option_titles in option_remark_map.items():
            label = option_remark_labels[normalized_text]
            if len(option_titles) > 1 or "" in option_titles:
                if normalized_text not in normalized_seen:
                    normalized_seen.add(normalized_text)
                    remarks.append(self._display_text(label))
                continue
            option_title = next(iter(option_titles))
            final_text = f"[{option_title}] {label}" if option_title else label
            if normalized_text not in normalized_seen:
                normalized_seen.add(normalized_text)
                remarks.append(self._display_text(final_text))

        remark_block = footer.get("remark")
        if isinstance(remark_block, dict):
            items = remark_block.get("items")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    text = str(item.get("text", "") or "")
                    if not text:
                        continue
                    normalized_text = self._normalize_remark_text(text)
                    if (
                        normalized_text in payment_term_texts
                        or normalized_text in normalized_seen
                    ):
                        continue
                    normalized_seen.add(normalized_text)
                    remarks.append(self._display_text(text))

        return remarks

    def _normalize_remark_text(self, text: str) -> str:
        normalized = text.strip().lower()
        normalized = re.sub(r"^\[[^\]]+\]\s*", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _build_service_payment_terms(self, footer: Mapping[str, Any]) -> list[str]:
        payment_terms = footer.get("service_payment_terms")
        if not isinstance(payment_terms, dict):
            return []
        content = str(payment_terms.get("content", "") or "")
        return [self._display_text(content)] if content else []

    def _description_row(
        self,
        *,
        index: str,
        content: str,
        price: str,
        unit: str,
        qty: str,
        discount: str,
        amount: str,
    ) -> dict[str, Any]:
        return {
            "index": index,
            "content": content,
            "price": price,
            "unit": unit,
            "qty": qty,
            "discount": discount,
            "amount": amount,
            "fixedAppendFlag": False,
            "discountType": 1,
        }

    def _title_row(self, *, index: str, content: str) -> dict[str, Any]:
        return self._description_row(
            index=index,
            content=content,
            price="",
            unit="",
            qty="",
            discount="",
            amount="",
        )

    def _group_row(self, *, index: str, content: str) -> dict[str, Any]:
        return self._description_row(
            index=index,
            content=content,
            price="",
            unit="",
            qty="",
            discount="",
            amount="",
        )

    def _option_prefix(self, option_counter: int) -> str:
        if 1 <= option_counter <= 26:
            return chr(ord("A") + option_counter - 1)
        return f"Option{option_counter}"

    def _compose_index(self, option_prefix: str, local_index: str) -> str:
        if option_prefix and local_index:
            return f"{option_prefix}.{local_index}"
        return option_prefix or local_index

    def _currency_symbol(self, currency_name: str) -> str:
        return self._CURRENCY_SYMBOLS.get(currency_name.strip().upper(), "")

    def _display_text(self, text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return stripped
        if self._display_language == "en":
            return stripped
        option_prefix_match = re.match(r"^(\[[^\]]+\]\s*)(.+)$", stripped)
        if option_prefix_match:
            prefix, body = option_prefix_match.groups()
            return f"{prefix}{self._translate_composite_text(body)}"
        return self._translate_composite_text(stripped)

    def _translate_composite_text(self, text: str) -> str:
        if text in self._ZH_TRANSLATIONS:
            return self._ZH_TRANSLATIONS[text]
        translated = text
        for source, target in sorted(
            self._ZH_TRANSLATIONS.items(), key=lambda item: len(item[0]), reverse=True
        ):
            translated = translated.replace(source, target)
        return translated

    def _normalize_language_specific_suffix(self, text: str) -> str:
        if self._display_language == "en":
            return text.replace("（待确认）", " (Pending confirmation)")
        return text

    def _is_short_auxiliary_note(self, text: str) -> bool:
        lowered = text.strip().lower()
        if not lowered:
            return True
        return lowered in {
            "按一次往返计",
            "如需要，安排酒店及餐食",
            "如船厂或当地安排要求，则适用",
            "仅在船厂或当地主管机关要求时适用",
            "供货责任待确认",
            "based on one round trip",
            "hotel and meal arrangement if needed",
            "applicable if required by yard or local arrangement",
            "applicable only if required by yard or local authority",
            "supply responsibility to be confirmed",
        }

    def _normalize_display_label(self, text: str) -> str:
        normalized = text.strip().lower()
        if not normalized:
            return ""
        normalized = normalized.replace("（待确认）", "")
        normalized = normalized.replace("(pending confirmation)", "")
        normalized = normalized.replace("（如需要）", "")
        normalized = normalized.replace("(if needed)", "")
        normalized = normalized.replace("（额外收费）", "")
        normalized = normalized.replace("(extra)", "")
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip(" -:：;,，")

    def _customer_facing_description(
        self, line: Mapping[str, Any], *, group_title: str
    ) -> str:
        line_type = str(line.get("line_type", "") or "")
        description = self._display_text(str(line.get("description", "") or "").strip())
        amount_display = str(line.get("amount_display", "") or "").strip()
        description = self._simplify_main_description(description, group_title)
        description = self._normalize_language_specific_suffix(description)

        if line_type == "pending":
            suffix = (
                "（待确认）"
                if self._display_language != "en"
                else " (Pending confirmation)"
            )
            fallback = (
                "待确认" if self._display_language != "en" else "Pending confirmation"
            )
            description = self._strip_pending_tail(description)
            return f"{description}{suffix}" if description else fallback
        if self._is_internal_scope_line(description):
            return ""
        if line_type in {"conditional", "optional"}:
            suffix = "（如需要）" if self._display_language != "en" else " (If needed)"
            fallback = "如需要" if self._display_language != "en" else "If needed"
            return f"{description}{suffix}" if description else fallback
        if line_type == "extra":
            suffix = "（额外收费）" if self._display_language != "en" else " (Extra)"
            fallback = "额外收费" if self._display_language != "en" else "Extra"
            return f"{description}{suffix}" if description else fallback
        if line_type == "commercial_note":
            return ""
        if line_type in {"scope_note", "technical_note", "assumption_note"}:
            return "" if self._is_internal_scope_line(description) else description
        if line_type == "note":
            return description or amount_display
        return description

    def _simplify_main_description(self, text: str, group_title: str) -> str:
        text = text.strip()
        if not text:
            return text
        group_title = group_title.strip()
        if group_title and text.lower().startswith(group_title.lower() + " "):
            text = text[len(group_title) :].strip()
        text = self._dedupe_leading_phrase(text)
        return text or group_title

    def _dedupe_leading_phrase(self, text: str) -> str:
        if not text:
            return text
        words = text.split()
        for size in range(min(4, len(words) // 2), 0, -1):
            prefix = " ".join(words[:size]).strip()
            suffix = " ".join(words[size:]).strip()
            if prefix and suffix and suffix.lower().startswith(prefix.lower() + " "):
                return suffix
        return text

    def _strip_pending_tail(self, text: str) -> str:
        updated = text.strip()
        for pattern in [
            r"[（(]?待确认[）)]?$",
            r"pending confirmation$",
            r"scope pending confirmation$",
        ]:
            updated = re.sub(pattern, "", updated, flags=re.IGNORECASE).strip()
        return updated.rstrip("-:：;,， ").strip()

    def _is_internal_scope_line(self, text: str) -> bool:
        lowered = text.lower().strip()
        if not lowered:
            return True
        for pattern in [
            r"^\d+(?:\.\d+)?\s*(set|job|lot|pcs?|pieces?|units?|ea|person|persons|person-day|man-day|days?|hours?|hrs?)$",
            r"^estimated\s+\d+\s+persons?\s+for\s+\d+\s+days?$",
            r"^\d+\s+hours?\s+execution\s+window$",
        ]:
            if re.match(pattern, lowered):
                return True
        internal_keywords = [
            "engineer",
            "fitter",
            "technician",
            "welder",
            "supervisor",
            "assistant",
            "discount applied",
            "approved authority",
            "operator authority",
            "execution window",
            "working time",
            "manhour",
            "man-hour",
            "工时",
            "人数",
            "工程师",
            "钳工",
            "焊工",
            "electrical engineer",
            "mechanical engineer",
        ]
        if any(keyword in lowered for keyword in internal_keywords):
            return True
        return bool(re.search(r"\b(mt|fp|et|wp|rn)\d+\b", lowered))
