from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from models import EngineeringPdfContext


def render_html(context: EngineeringPdfContext, *, assets_dir: Path) -> str:
    form_data = context.form_data
    display_language = str(context.display_language or "auto")
    html_lang = "en" if display_language == "en" else "zh-CN"
    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))

    gms_path = (assets_dir / "winkong_marinsmart_logo.png").resolve().as_uri()
    yibei_path = (assets_dir / "cooperative-brand.png").resolve().as_uri()
    description_rows = "".join(
        _render_description_row(item, context.display_discounts)
        for item in form_data.get("description", [])
    )
    testing_rows = _render_testing_rows(form_data.get("testingItems", []))
    remark_rows = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("remarks", [])
        if str(item)
    )
    prepared_by = str(form_data.get("preparedBy", "") or "").strip()
    approved_by = str(form_data.get("approvedBy", "") or "").strip()
    inscribe = escape(str(form_data.get("inscribe", "") or ""))
    discount_header = (
        '<td style="min-width: 72px"><p>折扣</p><p>Discount</p></td>'
        if context.display_discounts == 1
        else ""
    )

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Laboratory Quotation</title>
    <style>
@page {{ size: A4; margin: 30px; margin-top: 150px; }}
@page {{ @top-center {{ content: element(headerRunningLaboratory); }} @bottom-right {{ padding-bottom: 20px; }} }}
* {{ margin: 0; padding: 0; line-height: 1.2; }}
body {{ font-family: Arial, "Microsoft YaHei", sans-serif; }}
.laboratory-pdf {{ page: laboratoryPdf; }}
.header {{ position: running(headerRunningLaboratory); width: 100%; }}
.info_header {{ display: flex; justify-content: space-between; align-items: center; }}
.gms {{ width: 160px; }}
.yibei {{ width: 120px; }}
.title-box {{ color: #05328e; text-align: center; font-weight: 500; }}
.title-box .size-big {{ font-size: 18px; font-weight: bold; }}
.title-box .size-middle {{ font-size: 14px; font-weight: 500; }}
.rainbow {{ width: 100%; margin-top: 6px; }}
.rainbow img {{ width: 100%; height: 8px; }}
.currencyName {{ text-align: right; font-size: 14px; font-weight: normal; margin-bottom: 5px; }}
.content .title {{ margin: 0 auto 10px; width: 100%; font-size: 20px; text-align: center; font-weight: 700; }}
.table-white {{ background-color: #fff; }}
.table-gray thead {{ background-color: #d9d9d9; color: #000; }}
.pre-line {{ white-space: pre-line; }}
.en-word-line {{ word-break: break-word; }}
table {{ margin-top: -1px; width: 100%; border-collapse: collapse; font-size: 12px; color: #000; }}
table tr td {{ padding: 3px 6px !important; border: 1px solid #000; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; word-break: break-all; }}
table .bold {{ font-weight: 700; }}
.blue {{ color: #0b60d0; }}
.line-through {{ text-decoration: line-through; }}
.tr-img .td-img {{ height: 80px; vertical-align: middle; text-align: center; }}
.tr-img img {{ max-height: 70px; max-width: 180px; }}
    </style>
  </head>
  <body>
    <div class=\"laboratory-pdf\">
      <header class=\"header\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"gms\" src=\"{gms_path}\" title=\"gms-care\" />
          <div class=\"title-box\">
            <p class=\"size-big\">青岛儒海蓝色科技有限公司</p>
            <p class=\"size-middle\">Qingdao Global Marine Safetycare Technology Co., Ltd.</p>
            <p class=\"size-middle\">贻贝MarinSmart船海服务互联网平台</p>
            <p class=\"size-middle\">MarinSmart Platform</p>
          </div>
          <img alt=\"img\" class=\"yibei\" src=\"{yibei_path}\" title=\"logo\" />
        </div>
        <div class=\"rainbow\"><img alt=\"img\" src=\"{yibei_path}\" title=\"rainbow-bar\" /></div>
      </header>
      <section class=\"content\">
        <h1 class=\"title\">Quotation</h1>
        <h2 class=\"currencyName\"><span>币种 Currency：</span><span>{currency_name}</span></h2>
        <table class=\"table-bg table-white\">
          <tbody>
            <tr><td class=\"bold\"><p>客户名称</p><p>Customer Name</p></td><td>{escape(str(form_data.get("customerName", "") or ""))}</td><td class=\"bold\"><p>船名</p><p>Vessel Name</p></td><td>{escape(str(form_data.get("vesselName", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>联系人</p><p>Attention</p></td><td>{escape(str(form_data.get("attention", "") or ""))}</td><td class=\"bold\"><p>挂旗国</p><p>Flag</p></td><td>{escape(str(form_data.get("vesselFlag", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>服务港口</p><p>Service Port</p></td><td>{escape(str(form_data.get("servicePort", "") or ""))}</td><td class=\"bold\"><p>船级社</p><p>Class</p></td><td>{escape(str(form_data.get("vesselClass", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>报价日期</p><p>Date</p></td><td>{escape(str(form_data.get("date", "") or ""))}</td><td class=\"bold\"><p>我方报价号</p><p>WK Offer No.</p></td><td>{escape(str(form_data.get("wkOfferNo", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>设备信息</p><p>System info.</p></td><td>{escape(str(form_data.get("systemInfo", "") or ""))}</td><td class=\"bold\"><p>厂家及型号</p><p>Maker&Mode</p></td><td>{escape(str(form_data.get("makerModel", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>报价有效期</p><p>Quotation Validity</p></td><td>{escape(str(form_data.get("quotationValidity", "") or ""))}</td><td class=\"bold\"><p>付款方式</p><p>Payment Terms</p></td><td>{escape(str(form_data.get("paymentTerms", "") or ""))}</td></tr>
          </tbody>
        </table>
        <table class=\"table-gray\">{('<thead><tr class="bold"><td style="min-width: 42px"><p>序号</p><p>Item</p></td><td style="min-width: 100px"><p>项目内容</p><p>Description</p></td><td style="min-width: 72px"><p>单价</p><p>Unit Price</p></td><td style="min-width: 42px"><p>数量</p><p>Q\'ty</p></td><td style="min-width: 42px"><p>单位</p><p>Unit</p></td>' + discount_header + '<td style="min-width: 72px"><p>合计</p><p>Amount</p></td></tr></thead><tbody>' + description_rows + "</tbody>") if description_rows else ""}</table>
        <table class=\"table-gray\">{('<thead><tr class="bold"><td style="min-width: 100px"><p>检测项目</p><p>Testing items</p></td><td style="min-width: 220px"><p>采集样本数量</p><p>Collected Sample Quantity</p></td><td style="min-width: 120px"><p>进水</p><p>Intake Water</p></td><td style="min-width: 130px"><p>排水</p><p>Discharge Water</p></td></tr></thead><tbody>' + testing_rows + "</tbody>") if testing_rows else ""}</table>
        <table>{'<tbody><tr class="bold"><td>备注Remark</td></tr><tr><td>' + remark_rows + "</td></tr></tbody>" if remark_rows else ""}</table>
        <table>
          <thead><tr class=\"bold\"><td>制作人 Prepared by</td><td>签署人 Approved by</td></tr></thead>
          <tbody><tr class=\"tr-img\"><td class=\"td-img\"><div>{('<span><img alt="img" src="' + escape(prepared_by) + '" title="preparedBy" /></span>') if prepared_by else ""}</div></td><td class=\"td-img\"><div>{('<span><img alt="img" src="' + escape(approved_by) + '" title="approvedBy" /></span>') if approved_by else ""}</div></td></tr></tbody>
        </table>
        <table>{'<tbody><tr><td><p class="pre-line">' + inscribe + "</p></td></tr></tbody>" if inscribe else ""}</table>
      </section>
    </div>
  </body>
</html>
"""


def _render_description_row(item: Any, display_discounts: int) -> str:
    if not isinstance(item, dict):
        return ""
    discount_cell = (
        f"<td>{escape(str(item.get('discount', '') or ''))}</td>"
        if display_discounts == 1
        else ""
    )
    return (
        "<tr>"
        f"<td>{escape(str(item.get('index', '') or ''))}</td>"
        f'<td class="pre-line en-word-line">{escape(str(item.get("content", "") or ""))}</td>'
        f'<td class="{_value_class(item)}">{escape(str(item.get("price", "") or ""))}</td>'
        f"<td>{escape(str(item.get('qty', '') or ''))}</td>"
        f"<td>{escape(str(item.get('unit', '') or ''))}</td>"
        f"{discount_cell}"
        f'<td class="{_value_class(item)}">{escape(str(item.get("amount", "") or ""))}</td>'
        "</tr>"
    )


def _render_testing_rows(items: Any) -> str:
    if not isinstance(items, list):
        return ""
    rows = []
    current_group = None
    group_count = 0
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        group = str(item.get("group", "") or item.get("testingItemName", "") or idx)
        if group != current_group:
            current_group = group
            group_count = sum(
                1
                for candidate in items[idx:]
                if isinstance(candidate, dict)
                and str(
                    candidate.get("group", "")
                    or candidate.get("testingItemName", "")
                    or ""
                )
                == group
            )
            rows.append(
                "<tr>"
                f'<td rowspan="{group_count}"><div>{escape(str(item.get("testingItemName", "") or ""))}</div></td>'
                f"<td><div>{escape(str(item.get('sampleQty', '') or ''))}</div></td>"
                f"<td><div>{escape(str(item.get('intakeWater', '') or ''))}</div></td>"
                f"<td><div>{escape(str(item.get('dischargeWater', '') or ''))}</div></td>"
                "</tr>"
            )
        else:
            rows.append(
                "<tr>"
                f"<td><div>{escape(str(item.get('sampleQty', '') or ''))}</div></td>"
                f"<td><div>{escape(str(item.get('intakeWater', '') or ''))}</div></td>"
                f"<td><div>{escape(str(item.get('dischargeWater', '') or ''))}</div></td>"
                "</tr>"
            )
    return "".join(rows)


def _value_class(item: dict[str, Any]) -> str:
    classes: list[str] = []
    if item.get("fixedAppendFlag"):
        classes.append("blue")
    if int(item.get("discountType", 1) or 1) == 2 and not item.get("fixedAppendFlag"):
        classes.append("line-through")
    return " ".join(classes)
