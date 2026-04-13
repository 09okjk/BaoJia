from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from py_pdf.domain.models import EngineeringPdfContext


class QuotationResponseError(ValueError):
    pass


class QuotationResponseJsonDataSource:
    def __init__(self, json_path: Path) -> None:
        self._json_path = json_path

    def load(self) -> Mapping[str, Any]:
        with self._json_path.open("r", encoding="utf-8") as f:
            payload: object = json.load(f)
        if not isinstance(payload, dict):
            raise QuotationResponseError(
                f"无效的响应结构：根节点不是对象（文件：{self._json_path}）"
            )
        return payload  # type: ignore[return-value]

    def to_engineering_context(self) -> EngineeringPdfContext:
        payload = self.load()
        data = payload.get("data")
        quotation_orders = (
            data.get("quotationOrders") if isinstance(data, dict) else None
        )
        if not isinstance(quotation_orders, dict):
            raise QuotationResponseError(
                f"无效的响应结构：缺少 data.quotationOrders（文件：{self._json_path}）"
            )

        form_data = quotation_orders.get("engineeringQuotationOrder")
        if not isinstance(form_data, dict):
            raise QuotationResponseError(
                f"无效的响应结构：engineeringQuotationOrder 不是对象（文件：{self._json_path}）"
            )

        return EngineeringPdfContext(
            form_data=form_data,
            quotation_template=int(quotation_orders.get("quotationTemplate", 1) or 1),
            display_discounts=int(quotation_orders.get("displayDiscounts", 0) or 0),
            tax_rate=bool(quotation_orders.get("taxRate", False)),
            currency_name=str(quotation_orders.get("currencyName", "") or ""),
            currency_symbol=str(quotation_orders.get("currencySymbol", "") or ""),
            quotation_type=1,
            inquiry_no=str(quotation_orders.get("inquiryNo", "") or ""),
        )
