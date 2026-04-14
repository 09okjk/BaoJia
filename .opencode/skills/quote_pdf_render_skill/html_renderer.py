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

    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))
    description_rows = "".join(
        _render_description_row(item) for item in form_data.get("descriptions", [])
    )
    summary = (form_data.get("summary") or [{}])[0]
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

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Engineering Quotation</title>
    <style>
@page {{
  size: A4;
  margin: 30px;
  margin-top: 110px;
}}

@page {{
  @top-center {{
    content: element(headerRunningEngineering);
  }}
  @bottom-right {{
    padding-bottom: 20px;
  }}
}}

* {{
  margin: 0;
  padding: 0;
  line-height: 1.2;
}}

body {{
  font-family: Arial, "Microsoft YaHei", sans-serif;
}}

.engineering-pdf {{
  page: engineeringPdf;
}}

.currencyName {{
  text-align: right;
  font-size: 14px;
  font-weight: normal;
  margin-bottom: 5px;
}}

table {{
  margin-top: -1px;
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  color: #000;
}}

table tr {{
  break-inside: avoid;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}}

table tr td {{
  padding: 3px 6px !important;
  border: 1px solid #000;
  white-space: normal;
  overflow-wrap: break-word;
  word-wrap: break-word;
  word-break: break-all;
  break-inside: avoid;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}}

table .bold {{
  font-weight: 700;
}}

.header {{
  position: running(headerRunningEngineering);
  width: 100%;
  text-align: start;
}}

.header .info_header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.header .info_header .winkong_marinsmart_logo {{
  width: 140px;
}}

.header .info_header .aeo_box {{
  margin-right: 20px;
  width: 100px;
  height: 68px;
}}

.header .info_header .aeo_box .aeo {{
  display: block;
  width: 100%;
}}

.header .info_header .title-box {{
  color: #05328e;
  text-align: center;
  font-weight: 500;
}}

.header .info_header .title-box .size-big {{
  font-size: 18px;
  font-weight: bold;
}}

.header .info_header .title-box .size-middle {{
  font-size: 14px;
  font-weight: 500;
}}

.header .info_header .title-box .small-box p {{
  font-size: 12px;
}}

.content .bottom-img {{
  display: block;
  width: 720px;
  height: 161px;
}}

.content .table-blue thead {{
  background-color: #0066cc;
  color: #fff;
}}

.content .pre-line {{
  white-space: pre-line;
}}

.content .en-word-line {{
  word-break: break-word;
}}

.content .title {{
  margin: 0 auto 10px;
  width: 100%;
  word-break: normal;
  font-size: 20px;
  text-align: center;
  font-weight: 700;
}}

.content .table-bg {{
  background-color: #ededed;
}}

.content .table-bg td:nth-child(odd) {{
  width: 25%;
}}

.content .table-bg td:nth-child(even) {{
  width: 25%;
}}
    </style>
  </head>
  <body>
    <div class=\"engineering-pdf\">
      <header class=\"header\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"winkong_marinsmart_logo\" src=\"{logo_path}\" title=\"logo\" />
          <div class=\"title-box\">
            <p class=\"size-big\">青 岛 儒 海 船 舶 股 份 有 限 公 司</p>
            <p class=\"size-big\">WinKong Marine Engineering Co.，Ltd.</p>
            <p class=\"size-middle\">贻贝MarinSmart船海服务互联网平台</p>
            <p class=\"size-middle\">MARINSMART PLATFORM</p>
          </div>
          <div class=\"aeo_box\">
            <img alt=\"img\" class=\"aeo\" src=\"{aeo_path}\" title=\"aeo-logo\" />
          </div>
        </div>
      </header>

      <section class=\"content\">
        <h1 class=\"title\">Quotation</h1>
        <h2 class=\"currencyName\"><span>币种 Currency：</span> <span>{currency_name}</span></h2>

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
              <td style=\"min-width: 72px\"><p>单价</p><p>Unit Price</p></td>
              <td style=\"min-width: 42px\"><p>单位</p><p>Unit</p></td>
              <td style=\"min-width: 42px\"><p>数量</p><p>Q'ty</p></td>
              <td style=\"min-width: 72px\"><p>折扣</p><p>Discount</p></td>
              <td style=\"min-width: 72px\"><p>合计</p><p>Amount</p></td>
            </tr>
          </thead>
          <tbody>
            {description_rows}
          </tbody>
        </table>

        <table>
          <thead>
            <tr>
              <td colspan=\"4\" class=\"bold\">总结 Summary</td>
            </tr>
            <tr>
              <td class=\"bold\"><p>服务费</p><p>Service Charge</p></td>
              <td class=\"bold\"><p>备件费</p><p>Spare Parts Fee</p></td>
              <td class=\"bold\"><p>其它</p><p>Other</p></td>
              <td class=\"bold\"><p>总计</p><p>Total</p></td>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{escape(str(summary.get("serviceCharge", "") or ""))}</td>
              <td>{escape(str(summary.get("sparePartsFee", "") or ""))}</td>
              <td>{escape(str(summary.get("other", "") or ""))}</td>
              <td>{escape(str(summary.get("total", "") or ""))}</td>
            </tr>
          </tbody>
        </table>

        <table>
          <tbody>
            <tr>
              <td class=\"bold\">备注Remark</td>
            </tr>
            <tr>
              <td>{remark_rows}</td>
            </tr>
          </tbody>
        </table>

        <table>
          <tbody>
            <tr>
              <td class=\"bold\">服务支付条款 Service Payment Terms</td>
            </tr>
            <tr>
              <td>{service_terms}</td>
            </tr>
          </tbody>
        </table>

        <table>
          <tbody>
            <tr>
              <td>
                <img alt=\"img\" class=\"bottom-img\" src=\"{brand_path}\" title=\"cooperative-brand\" />
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  </body>
</html>
"""


def _render_description_row(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    return (
        "<tr>"
        f"<td>{escape(str(item.get('index', '') or ''))}</td>"
        f'<td class="pre-line en-word-line">{escape(str(item.get("content", "") or ""))}</td>'
        f'<td class="">{escape(str(item.get("price", "") or ""))}</td>'
        f"<td>{escape(str(item.get('unit', '') or ''))}</td>"
        f"<td>{escape(str(item.get('qty', '') or ''))}</td>"
        f"<td>{escape(str(item.get('discount', '') or ''))}</td>"
        f'<td class="">{escape(str(item.get("amount", "") or ""))}</td>'
        "</tr>"
    )
