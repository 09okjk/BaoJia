from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from models import EngineeringPdfContext


def render_html(context: EngineeringPdfContext, *, assets_dir: Path) -> str:
    form_data = context.form_data
    display_language = str(context.display_language or "auto")
    html_lang = "en" if display_language == "en" else "zh-CN"
    quotation_template = int(context.quotation_template or 1)

    logo_path = (assets_dir / "winkong_marinsmart_logo.png").resolve().as_uri()
    mitsubishi_path = (assets_dir / "cooperative-brand.png").resolve().as_uri()
    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))
    descriptions = "".join(
        _render_description_row(item, context.display_discounts)
        for item in form_data.get("descriptions", [])
    )
    remark_rows = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("remarks", [])
        if str(item)
    )
    work_scope = "".join(
        f"<p>{index}. {escape(str(item))}</p>"
        for index, item in enumerate(form_data.get("workScope", []), start=1)
        if str(item)
    )
    discount_header = (
        '<td style="min-width: 68px"><p>折扣</p><p>Discount</p></td>'
        if context.display_discounts == 1
        else ""
    )
    tax_colspan = 7 if context.display_discounts == 1 else 6

    if quotation_template == 2:
        header_title = """
            <p class=\"size-big\">MARINSMART GLOBAL SERVICE PTE LTD</p>
            <p class=\"size-middle\">2 Venture Drive,</p>
            <p class=\"size-middle\">+65 9199 1959 | sales@mgs.com.sg | www.winkong.net</p>
            <p class=\"size-middle\">Company Registration: 202142747G</p>
        """
    else:
        header_title = """
            <p class=\"size-big\">WinKong Marine Engineering Co.，Ltd.</p>
            <p class=\"size-middle\">17F, ZHONGXIN BUILDING, NO.263 LIAONING ROAD, QINGDAO, CHINA</p>
            <p class=\"size-middle\">TEL: 0086-532-83829109/83800536</p>
            <p class=\"size-middle\">Http://www.winkong.net E-mail:biz@winkong.net</p>
        """

    mitsubishi_block = (
        f'<div class="mitsubishi_box"><img alt="img" class="mitsubishi" src="{mitsubishi_path}" title="mitsubishi" /></div>'
        if int(form_data.get("logo", 0) or 0) == 1
        else '<div class="mitsubishi_box"></div>'
    )

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Supercharger Quotation</title>
    <style>
@page {{ size: A4; margin: 10px; margin-top: 150px; }}
@page {{ @top-center {{ content: element(headerRunningSupercharger); }} @bottom-right {{ padding-bottom: 20px; }} }}
* {{ margin: 0; padding: 0; line-height: 1.2; }}
body {{ font-family: Arial, "Microsoft YaHei", sans-serif; }}
.main-supercharger-pdf {{ page: superchargerPdf; }}
.header {{ position: running(headerRunningSupercharger); width: 100%; }}
.info_header {{ display: flex; justify-content: space-between; align-items: center; }}
.ruhai {{ width: 140px; }}
.title-box {{ color: #05328e; text-align: center; font-weight: 500; }}
.title-box .size-big {{ font-size: 18px; font-weight: bold; }}
.title-box .size-middle {{ font-size: 14px; font-weight: 500; }}
.mitsubishi_box {{ width: 120px; text-align: right; }}
.mitsubishi {{ width: 100px; }}
.currencyName {{ text-align: right; font-size: 14px; font-weight: normal; margin-bottom: 5px; }}
.content .title {{ margin: 0 auto 10px; width: 100%; font-size: 20px; text-align: center; font-weight: 700; }}
.content .table-bg {{ background-color: #ededed; }}
.content .table-blue thead {{ background-color: #0066cc; color: #fff; }}
.content .pre-line {{ white-space: pre-line; }}
.content .en-word-line {{ word-break: break-word; }}
table {{ margin-top: -1px; width: 100%; border-collapse: collapse; font-size: 12px; color: #000; }}
table tr td {{ padding: 3px 6px !important; border: 1px solid #000; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; word-break: break-all; }}
table .bold {{ font-weight: 700; }}
.blue {{ color: #0b60d0; }}
.line-through {{ text-decoration: line-through; }}
    </style>
  </head>
  <body>
    <div class=\"main-supercharger-pdf\">
      <header class=\"header\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"ruhai\" src=\"{logo_path}\" title=\"logo\" />
          <div class=\"title-box\">{header_title}</div>
          {mitsubishi_block}
        </div>
      </header>
      <section class=\"content\">
        <h1 class=\"title\">Quotation for Turbocharger Service</h1>
        <h2 class=\"currencyName\"><span>币种 Currency：</span><span>{currency_name}</span></h2>
        <table class=\"table-bg\">
          <tbody>
            <tr><td class=\"bold\"><p>客户名称</p><p>Customer Name</p></td><td>{escape(str(form_data.get("customerName", "") or ""))}</td><td class=\"bold\"><p>船名</p><p>Vessel Name</p></td><td>{escape(str(form_data.get("vesselName", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>IMO</p></td><td>{escape(str(form_data.get("imoNo", "") or ""))}</td><td class=\"bold\"><p>船型</p><p>Vessel Type</p></td><td>{escape(str(form_data.get("vesselType", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>增压器型号</p><p>Turbocharger Type</p></td><td>{escape(str(form_data.get("turbochargerType", "") or ""))}</td><td class=\"bold\"><p>运行时间</p><p>Running hours</p></td><td>{escape(str(form_data.get("hours", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>我方报价号</p><p>WK Offer No.</p></td><td>{escape(str(form_data.get("wkOfferNo", "") or ""))}</td><td class=\"bold\"><p>日期</p><p>Date</p></td><td>{escape(str(form_data.get("date", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>港口</p><p>Service Port</p></td><td>{escape(str(form_data.get("servicePort", "") or ""))}</td><td class=\"bold\"><p>询价号</p><p>Your Ref No.</p></td><td>{escape(str(form_data.get("youRefNo", "") or ""))}</td></tr>
          </tbody>
        </table>
        <table class=\"table-blue\">
          <thead>
            <tr class=\"bold\">
              <td style=\"min-width: 134px\"><p>项目 & 工作范围</p><p>Item & Work Scope</p></td>
              <td style=\"min-width: 40px\"><p>序号</p><p>NO.</p></td>
              <td style=\"min-width: 120px\"><p>工作描述</p><p>Work Description</p></td>
              <td style=\"min-width: 74px\"><p>单价</p><p>Unit Price</p></td>
              <td style=\"min-width: 40px\"><p>数量</p><p>Q'ty</p></td>
              <td style=\"min-width: 40px\"><p>单位</p><p>Unit</p></td>
              {discount_header}
              <td style=\"min-width: 64px\"><p>合计</p><p>Amount</p></td>
            </tr>
          </thead>
          <tbody>
            {descriptions}
            <tr><td colspan=\"{tax_colspan}\" style=\"text-align: right\">Total</td><td>{escape(str(form_data.get("totalAmount", "") or ""))}</td></tr>
            {f'<tr><td colspan="{tax_colspan}" style="text-align: right">VAT Of Service</td><td>{escape(str(form_data.get("serviceTaxRate", "") or ""))}</td></tr>' if str(form_data.get("serviceTaxRate", "") or "") else ""}
            {f'<tr><td colspan="{tax_colspan}" style="text-align: right">VAT Of Spare Parts</td><td>{escape(str(form_data.get("productTaxRate", "") or ""))}</td></tr>' if str(form_data.get("productTaxRate", "") or "") else ""}
            {f'<tr><td colspan="{tax_colspan}" style="text-align: right">Final Amount</td><td>{escape(str(form_data.get("finalAmount", "") or ""))}</td></tr>' if str(form_data.get("finalAmount", "") or "") else ""}
          </tbody>
        </table>
        <table>{'<tbody><tr><td class="bold">Remark</td></tr><tr><td>' + remark_rows + "</td></tr></tbody>" if remark_rows else ""}</table>
        <table>{'<tbody><tr><td class="bold">Workscope</td></tr><tr><td><p>For running hour ' + escape(str(form_data.get("runningHours", "") or "")) + " Hrs routine overhaul:</p>" + work_scope + "</td></tr></tbody>" if work_scope else ""}</table>
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
        f"<td>{escape(str(item.get('itemAndWorkScope', '') or ''))}</td>"
        f"<td>{escape(str(item.get('index', '') or ''))}</td>"
        f'<td class="pre-line en-word-line">{escape(str(item.get("content", "") or ""))}</td>'
        f'<td class="{_value_class(item)}">{escape(str(item.get("price", "") or ""))}</td>'
        f"<td>{escape(str(item.get('qty', '') or ''))}</td>"
        f"<td>{escape(str(item.get('unit', '') or ''))}</td>"
        f"{discount_cell}"
        f'<td class="{_value_class(item)}">{escape(str(item.get("amount", "") or ""))}</td>'
        "</tr>"
    )


def _value_class(item: dict[str, Any]) -> str:
    classes: list[str] = []
    if item.get("fixedAppendFlag"):
        classes.append("blue")
    if int(item.get("discountType", 1) or 1) == 2 and not item.get("fixedAppendFlag"):
        classes.append("line-through")
    return " ".join(classes)
