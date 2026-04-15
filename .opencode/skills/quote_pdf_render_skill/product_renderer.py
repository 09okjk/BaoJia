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
    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))
    descriptions = "".join(
        _render_description_row(item, context.display_discounts)
        for item in form_data.get("descriptions", [])
    )
    summary = (form_data.get("summary") or [{}])[0]
    remark_rows = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("remarks", [])
        if str(item)
    )
    spare_terms = "".join(
        f"<tr><td>{index}</td><td><p>{escape(str(item))}</p></td></tr>"
        for index, item in enumerate(
            form_data.get("paymentTermsForSpareParts", []), start=1
        )
        if str(item)
    )
    inscribe = escape(str(form_data.get("inscribe", "") or ""))
    discount_header = (
        '<td style="min-width: 70px"><p>折扣</p><p>Discount</p></td>'
        if context.display_discounts == 1
        else ""
    )
    discount_colspan = "5" if context.tax_rate else "3"

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Product Quotation</title>
    <style>
@page {{ size: A4; margin: 30px; margin-top: 130px; }}
@page {{ @top-center {{ content: element(headerRunningProduct); }} @bottom-right {{ padding-bottom: 20px; }} }}
* {{ margin: 0; padding: 0; line-height: 1.2; }}
body {{ font-family: Arial, "Microsoft YaHei", sans-serif; }}
.product-pdf {{ page: productPdf; }}
.header {{ position: running(headerRunningProduct); width: 100%; }}
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
.introduce-text {{ margin-top: 8px; margin-bottom: 8px; }}
.introduce-text h1 {{ font-size: 12px; font-weight: normal; }}
table {{ margin-top: -1px; width: 100%; border-collapse: collapse; font-size: 12px; color: #000; }}
table tr td {{ padding: 3px 6px !important; border: 1px solid #000; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; word-break: break-all; }}
table .bold {{ font-weight: 700; }}
.blue {{ color: #0b60d0; }}
.line-through {{ text-decoration: line-through; }}
    </style>
  </head>
  <body>
    <div class=\"product-pdf\">
      <header class=\"header\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"winkong_marinsmart_logo\" src=\"{logo_path}\" title=\"logo\" />
          <div class=\"title-box\">
            <p class=\"size-big\">青 岛 儒 海 船 舶 股 份 有 限 公 司</p>
            <p class=\"size-big\">WinKong Marine Engineering Co.，Ltd.</p>
            <p class=\"size-middle\">贻贝MarinSmart船海服务互联网平台</p>
            <p class=\"size-middle\">MARINSMART PLATFORM</p>
          </div>
          <div class=\"aeo_box\"><img alt=\"img\" class=\"aeo\" src=\"{aeo_path}\" title=\"aeo-logo\" /></div>
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
              <td class=\"bold\"><p>To</p></td>
              <td>{escape(str(form_data.get("to", "") or ""))}</td>
              <td class=\"bold\"><p>From</p></td>
              <td>{escape(str(form_data.get("from", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>联系人</p><p>Attention</p></td>
              <td>{escape(str(form_data.get("attention", "") or ""))}</td>
              <td class=\"bold\"><p>电话</p><p>Tel</p></td>
              <td>{escape(str(form_data.get("tel", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>询价号</p><p>Your Ref No.</p></td>
              <td>{escape(str(form_data.get("youRefNo", "") or ""))}</td>
              <td class=\"bold\"><p>我方报价号</p><p>WK Offer No.</p></td>
              <td>{escape(str(form_data.get("wkOfferNo", "") or ""))}</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>报价有效期</p><p>Quotation Validity</p></td>
              <td>{escape(str(form_data.get("quotationValidity", "") or ""))}</td>
              <td class=\"bold\"><p>交货条款</p><p>Trade term</p></td>
              <td>{escape(str(form_data.get("paymentTerms", "") or ""))}</td>
            </tr>
          </tbody>
        </table>
        <table class=\"table-blue\">
          <thead>
            <tr class=\"bold\">
              <td style=\"min-width: 42px\"><p>序号</p><p>Item</p></td>
              <td style=\"min-width: 240px\"><p>备件名称&规格</p><p>Name & Specifications of spare parts</p></td>
              <td style=\"min-width: 72px\"><p>单价</p><p>Unit Price</p></td>
              <td style=\"min-width: 42px\"><p>单位</p><p>Unit</p></td>
              <td style=\"min-width: 42px\"><p>数量</p><p>Q'ty</p></td>
              {discount_header}
              <td style=\"min-width: 70px\"><p>合计</p><p>Amount</p></td>
            </tr>
          </thead>
          <tbody>
            {descriptions}
          </tbody>
        </table>
        <table>
          <thead><tr class=\"bold\"><td colspan=\"{discount_colspan}\">总结 Summary</td></tr></thead>
          <tbody>
            <tr>
              <td style=\"width: 80%; text-align: right\"><p>备件费{"(" + escape(str(summary.get("productTaxRate", "") or "")) + "VAT)" if summary.get("productTaxRate") else ""} Spare Parts Fee</p></td>
              <td>{escape(str(summary.get("sparePartsFee", "") or ""))}</td>
            </tr>
            <tr>
              <td style=\"width: 80%; text-align: right\"><p>其它 Other</p></td>
              <td>{escape(str(summary.get("other", "") or ""))}</td>
            </tr>
            <tr>
              <td style=\"width: 80%; text-align: right\"><p>总计 Total</p></td>
              <td>{escape(str(summary.get("total", "") or ""))}</td>
            </tr>
          </tbody>
        </table>
        <table>{'<tbody><tr class="bold"><td>备注Remark</td></tr><tr><td>' + remark_rows + "</td></tr></tbody>" if remark_rows else ""}</table>
        <table>{'<tbody><tr><td colspan="2" class="bold">备件支付条款 Payment Terms For Spare Parts</td></tr>' + spare_terms + "</tbody>" if spare_terms else ""}</table>
        <div class=\"introduce-text\"><h1>Note: Other cost if happened to be charged extra.</h1><h1>*Cancellation made after receipt of Purchase Order will incur a 50 Percent cancellation fee.</h1></div>
        <table>{'<tr><td><p class="pre-line">' + inscribe + "</p></td></tr>" if inscribe else ""}</table>
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
