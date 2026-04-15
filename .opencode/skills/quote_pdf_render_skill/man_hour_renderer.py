from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from models import EngineeringPdfContext


def render_html(context: EngineeringPdfContext, *, assets_dir: Path) -> str:
    form_data = context.form_data
    display_language = str(context.display_language or "auto")
    html_lang = "en" if display_language == "en" else "zh-CN"

    logo_path = (assets_dir / "winkong_marinsmart_logo.png").resolve().as_uri()
    aeo_path = (assets_dir / "aeo-logo.png").resolve().as_uri()
    brand_path = (assets_dir / "cooperative-brand.png").resolve().as_uri()

    quotation_template = int(context.quotation_template or 1)
    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))
    description_rows = "".join(
        _render_description_row(item, display_discounts=context.display_discounts)
        for item in form_data.get("descriptions", [])
    )
    remark_rows = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("remarks", [])
        if str(item)
    )
    service_terms = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("servicePaymentTerms", [])
        if str(item)
    )
    spare_terms = "".join(
        f"<tr><td style=\"width: 30px\">{index}</td><td><p>{escape(str(item))}</p></td></tr>"
        for index, item in enumerate(form_data.get("paymentTermsForSpareParts", []), start=1)
        if str(item)
    )
    inscribe = escape(str(form_data.get("inscribe", "") or ""))
    service_tax_rate = escape(str(form_data.get("serviceTaxRate", "") or ""))
    product_tax_rate = escape(str(form_data.get("productTaxRate", "") or ""))
    discount_header = (
        "<td style=\"min-width: 78px\"><p>折扣</p><p>Discount</p></td>"
        if context.display_discounts == 1
        else ""
    )

    if quotation_template == 2:
        header_title = """
            <p class=\"size-big\">MARINSMART GLOBAL SERVICE PTE LTD</p>
            <p class=\"size-middle\">2 Venture Drive, #08-16 Vision Exchange, Singapore 608526</p>
            <p class=\"size-middle\">+65 9199 1959 | sales@mgs.com.sg | www.winkong.net</p>
            <p class=\"size-middle\">Company Registration: 202142747G</p>
        """
        aeo_block = ""
    else:
        header_title = """
            <p class=\"size-big\">青 岛 儒 海 船 舶 股 份 有 限 公 司</p>
            <p class=\"size-big\">WinKong Marine Engineering Co.，Ltd.</p>
            <p class=\"size-middle\">贻贝MarinSmart船海服务互联网平台</p>
            <p class=\"size-middle\">MARINSMART PLATFORM</p>
        """
        aeo_block = f"<div class=\"aeo_box\"><img alt=\"img\" class=\"aeo\" src=\"{aeo_path}\" title=\"aeo-logo\" /></div>"

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Man-hour Quotation</title>
    <style>
@page {{
  size: A4;
  margin: 30px;
  margin-top: 130px;
}}

@page {{
  @top-center {{
    content: element(headerRunningManHour);
  }}
  @bottom-right {{
    padding-bottom: 20px;
  }}
}}

* {{ margin: 0; padding: 0; line-height: 1.2; }}
body {{ font-family: Arial, "Microsoft YaHei", sans-serif; }}
.man-hour-pdf {{ page: manHourPdf; }}
.header {{ position: running(headerRunningManHour); height: 60px; width: 100%; }}
.info_header {{ display: flex; justify-content: space-between; align-items: center; }}
.winkong_marinsmart_logo {{ width: 140px; }}
.aeo_box {{ margin-right: 20px; width: 100px; height: 68px; }}
.aeo {{ display: block; width: 100%; }}
.title-box {{ color: #05328e; text-align: center; font-weight: 500; }}
.title-box .size-big {{ font-size: 18px; font-weight: bold; }}
.title-box .size-middle {{ font-size: 14px; font-weight: 500; }}
.currencyName {{ text-align: right; font-size: 14px; font-weight: normal; margin-bottom: 5px; }}
.content .title {{ margin: 0 auto 10px; width: 100%; font-size: 20px; text-align: center; font-weight: 700; }}
.content .table-bg {{ background-color: #ededed; }}
.content .table-blue thead {{ background-color: #0066cc; color: #fff; }}
.content .pre-line {{ white-space: pre-line; }}
.content .en-word-line {{ word-break: break-word; }}
.content .bottom-img {{ display: block; width: 720px; height: 161px; }}
table {{ margin-top: -1px; width: 100%; border-collapse: collapse; font-size: 12px; color: #000; }}
table tr {{ break-inside: avoid; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
table tr td {{ padding: 3px 6px !important; border: 1px solid #000; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; word-break: break-all; break-inside: avoid; box-decoration-break: clone; -webkit-box-decoration-break: clone; }}
table .bold {{ font-weight: 700; }}
.blue {{ color: #0b60d0; }}
.line-through {{ text-decoration: line-through; }}
    </style>
  </head>
  <body>
    <div class=\"man-hour-pdf\">
      <header class=\"header\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"winkong_marinsmart_logo\" src=\"{logo_path}\" title=\"logo\" />
          <div class=\"title-box\">{header_title}</div>
          {aeo_block}
        </div>
      </header>
      <section class=\"content\">
        <h1 class=\"title\">Quotation</h1>
        <h2 class=\"currencyName\"><span>币种 Currency：</span><span>{currency_name}</span></h2>

        <table class=\"table-bg\">
          <tbody>
            <tr>
              <td class=\"bold\"><p>船名</p><p>Vessel Name</p></td>
              <td>{escape(str(form_data.get("vesselName", "") or ""))}</td>
              <td class=\"bold\"><p>日期</p><p>Date</p></td>
              <td>{escape(str(form_data.get("date", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>IMO No.</p></td>
              <td>{escape(str(form_data.get("imoNo", "") or ""))}</td>
              <td class=\"bold\"><p>船型</p><p>Vessel Type</p></td>
              <td>{escape(str(form_data.get("vesselType", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>客户名称</p><p>Customer Name</p></td>
              <td>{escape(str(form_data.get("customerName", "") or ""))}</td>
              <td class=\"bold\"><p>港口</p><p>Service Port</p></td>
              <td>{escape(str(form_data.get("servicePort", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>联系人</p><p>Attention</p></td>
              <td>{escape(str(form_data.get("attention", "") or ""))}</td>
              <td class=\"bold\"><p>我方报价号</p><p>WK Offer No.</p></td>
              <td>{escape(str(form_data.get("wkOfferNo", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>询价号</p><p>Your Ref No.</p></td>
              <td>{escape(str(form_data.get("youRefNo", "") or ""))}</td>
              <td class=\"bold\"><p>报价有效期</p><p>Quotation Validity</p></td>
              <td>{escape(str(form_data.get("quotationValidity", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>确认号</p><p>PO No.</p></td>
              <td>{escape(str(form_data.get("poNo", "") or ""))}</td>
              <td class=\"bold\"><p>询价发起人</p><p>PIC of WinKong</p></td>
              <td>{escape(str(form_data.get("inquiryInitiator", "") or ""))}</td>
            </tr>
          </tbody>
        </table>

        <table class=\"table-blue\">
          <thead>
            <tr class=\"bold\">
              <td style=\"min-width: 42px\"><p>序号</p><p>Item</p></td>
              <td style=\"min-width: 100px\"><p>项目内容</p><p>Description</p></td>
              <td style=\"min-width: 74px\"><p>单价</p><p>Unit Price</p></td>
              <td style=\"min-width: 42px\"><p>单位</p><p>Unit</p></td>
              <td style=\"min-width: 42px\"><p>数量</p><p>Q'ty</p></td>
              {discount_header}
              <td style=\"min-width: 78px\"><p>合计</p><p>Amount</p></td>
            </tr>
          </thead>
          <tbody>
            {description_rows}
            {f'<tr><td colspan="{6 if context.display_discounts == 1 else 5}"><p style="text-align: right">服务税率</p><p style="text-align: right">VAT Of Service</p></td><td>{service_tax_rate}</td></tr>' if service_tax_rate else ''}
            {f'<tr><td colspan="{6 if context.display_discounts == 1 else 5}"><p style="text-align: right">备件税率</p><p style="text-align: right">VAT Of Spare Parts</p></td><td>{product_tax_rate}</td></tr>' if product_tax_rate else ''}
          </tbody>
        </table>

        <table>{'<tbody><tr class="bold"><td>备注Remark</td></tr><tr><td>' + remark_rows + '</td></tr></tbody>' if remark_rows else ''}</table>
        <table>{'<tbody><tr class="bold"><td>服务支付条款 Service Payment Terms</td></tr><tr><td>' + service_terms + '</td></tr></tbody>' if service_terms else ''}</table>
        <table>{'<tbody><tr class="bold"><td colspan="2">备件支付条款 Payment Terms For Spare Parts</td></tr>' + spare_terms + '</tbody>' if spare_terms else ''}</table>
        <table>{'<tbody><tr><td class="pre-line">' + inscribe + '</td></tr></tbody>' if inscribe else ''}</table>
        <table>
          <tbody>
            <tr>
              <td><img alt=\"img\" class=\"bottom-img\" src=\"{brand_path}\" title=\"cooperative-brand\" /></td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </body>
</html>
"""


def _render_description_row(item: Any, *, display_discounts: int) -> str:
    if not isinstance(item, dict):
        return ""
    merge_flag = int(item.get("mergeFlag", 0) or 0)
    discount_cell = (
        f"<td>{escape(str(item.get('discount', '') or ''))}</td>" if display_discounts == 1 else ""
    )
    if merge_flag == 1:
        colspan = 5 if display_discounts == 1 else 4
        return (
            "<tr>"
            f"<td>{escape(str(item.get('index', '') or ''))}</td>"
            f'<td class="pre-line en-word-line">{escape(str(item.get("content", "") or ""))}</td>'
            f'<td colspan="{colspan}" class="pre-line">{escape(str(item.get("mergeContent", "") or ""))}</td>'
            "</tr>"
        )
    return (
        "<tr>"
        f"<td>{escape(str(item.get('index', '') or ''))}</td>"
        f'<td class="pre-line en-word-line">{escape(str(item.get("content", "") or ""))}</td>'
        f'<td class="{_value_class(item)}">{escape(str(item.get("price", "") or ""))}</td>'
        f"<td>{escape(str(item.get('unit', '') or ''))}</td>"
        f"<td>{escape(str(item.get('qty', '') or ''))}</td>"
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
