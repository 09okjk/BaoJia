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
    aeo_path = (assets_dir / "aeo-logo.png").resolve().as_uri()
    currency_name = escape(str(form_data.get("currency", context.currency_name) or ""))
    repair_table = _render_valve_table(
        title="Quotation for Repair Kit",
        items=form_data.get("quotationForRepairKit", []),
        display_discounts=context.display_discounts,
    )
    complete_table = _render_valve_table(
        title="Complete valve",
        items=form_data.get("completeValve", []),
        display_discounts=context.display_discounts,
    )
    remark_rows = "".join(
        f"<p>{escape(str(item))}</p>"
        for item in form_data.get("remarks", [])
        if str(item)
    )
    header_class = "header headerHigh" if quotation_template == 1 else "header headerShort"

    if quotation_template == 2:
        header_title = """
          <p class=\"size-big\">MARINSMART GLOBAL SERVICE PTE LTD</p>
          <p class=\"size-middle\">2 Venture Drive, #08-16 Vision Exchange, Singapore 608526</p>
          <p class=\"size-middle\">+65 86476020 Company Registration: 202142747G</p>
        """
        aeo_block = ""
    else:
        header_title = """
          <p class=\"size-big\">青 岛 儒 海 船 舶 股 份 有 限 公 司</p>
          <p class=\"size-big\">WinKong Marine Engineering Co.，Ltd.</p>
          <div class=\"small-box\">
            <p>17F, Zhongxin Building, No.263 LiaoningRoad,Qingdao,P. R.China 266012</p>
            <p>Tel: +86 532 83829109/83836759/83800536; Fax: +86 532 83776955</p>
            <p>E-mail: biz@winkong.net/winkong@vip.sohu.com Website:www.winkong.net</p>
          </div>
          <p class=\"size-middle\">贻贝MarinSmart船海服务互联网平台</p>
          <p class=\"size-middle\">MARINSMART PLATFORM</p>
        """
        aeo_block = f'<div class="aeo_box"><img alt="img" class="aeo" src="{aeo_path}" title="aeo-logo" /></div>'

    return f"""<!doctype html>
<html lang=\"{html_lang}\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Valva Quotation</title>
    <style>
@page {{ size: A4; margin: 30px; margin-top: 180px; }}
@page {{ @top-center {{ content: element(headerRunningValva); }} @bottom-right {{ padding-bottom: 20px; }} }}
* {{ margin: 0; padding: 0; line-height: 1.2; }}
body {{ font-family: Arial, "Microsoft YaHei", sans-serif; }}
.valva-pdf {{ page: valvaPdf; }}
.header {{ position: running(headerRunningValva); width: 100%; }}
.headerShort {{ height: 60px; }}
.headerHigh {{ height: 130px; }}
.info_header {{ display: flex; justify-content: space-between; align-items: center; }}
.winkong_marinsmart_logo {{ width: 140px; }}
.title-box {{ color: #05328e; text-align: center; font-weight: 500; }}
.title-box .size-big {{ font-size: 18px; font-weight: bold; }}
.title-box .size-middle {{ font-size: 14px; font-weight: 500; }}
.small-box p {{ font-size: 12px; }}
.aeo_box {{ margin-right: 20px; width: 100px; height: 68px; }}
.aeo {{ display: block; width: 100%; }}
.time {{ text-align: right; margin-bottom: 5px; font-size: 14px; }}
.introduce-text {{ margin-top: 10px; margin-bottom: 4px; }}
.icon {{ display: inline-block; font-size: 12px; width: 12px; height: 12px; margin-right: 4px; }}
table {{ margin-top: -1px; width: 100%; border-collapse: collapse; font-size: 12px; color: #000; }}
table tr td {{ padding: 3px 6px !important; border: 1px solid #000; white-space: normal; overflow-wrap: break-word; word-wrap: break-word; word-break: break-all; }}
table .bold {{ font-weight: 700; }}
.table-bg {{ background-color: #ededed; }}
.table-blue thead {{ background-color: #0066cc; color: #fff; }}
.blue {{ color: #0b60d0; }}
.line-through {{ text-decoration: line-through; }}
.total {{ margin-top: 8px; margin-bottom: 8px; font-size: 14px; font-weight: 700; text-align: right; }}
    </style>
  </head>
  <body>
    <div class=\"valva-pdf\">
      <header class=\"{header_class}\">
        <div class=\"info_header\">
          <img alt=\"img\" class=\"winkong_marinsmart_logo\" src=\"{logo_path}\" title=\"logo\" />
          <div class=\"title-box\">{header_title}</div>
          {aeo_block}
        </div>
      </header>
      <section class=\"content\">
        <h1 class=\"title pre-line\">{escape(str(form_data.get("title", "Valve Quotation") or "Valve Quotation"))}</h1>
        <p class=\"time\"><span style=\"margin-right: 20px\">币种 Currency：{currency_name}</span><span>Date：{escape(str(form_data.get("date", "") or ""))}</span></p>
        <table class=\"table-bg\">
          <tbody>
            <tr><td class=\"bold\"><p>Vessel Name</p></td><td>{escape(str(form_data.get("vesselName", "") or ""))}</td><td class=\"bold\"><p>ENGINE MAKER/TYPE</p></td><td>{escape(str(form_data.get("engineMakerType", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>BUILT YEAR</p></td><td>{escape(str(form_data.get("builtYear", "") or ""))}</td><td class=\"bold\"><p>BUIT YARD</p></td><td>{escape(str(form_data.get("buitYard", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>DREW BY</p></td><td colspan=\"3\">{escape(str(form_data.get("drewBy", "") or ""))}</td></tr>
            <tr><td class=\"bold\"><p>Valve list refered to</p></td><td colspan=\"3\">{escape(str(form_data.get("valveListReferedTo", "") or ""))}</td></tr>
          </tbody>
        </table>
        {repair_table}
        {complete_table}
        <p class=\"total\">Total：{escape(str(form_data.get("totalPrice", "") or ""))}</p>
        <table><tbody><tr><td><p>✕ Change</p><p>○ Repair(O/H Inspection)</p><p>△ Change after checking the condition</p></td></tr></tbody></table>
        <table>{'<tbody><tr class="bold"><td>REMARK:</td></tr><tr><td>' + remark_rows + '</td></tr></tbody>' if remark_rows else ''}</table>
      </section>
    </div>
  </body>
</html>
"""


def _render_valve_table(*, title: str, items: Any, display_discounts: int) -> str:
    rows = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            discount_cell = (
                f"<td>{escape(str(item.get('discount', '') or ''))}</td>" if display_discounts == 1 else ""
            )
            rows.append(
                "<tr>"
                f"<td>{escape(str(item.get('no', '') or ''))}</td>"
                f"<td>{escape(str(item.get('model', '') or ''))}</td>"
                f"<td>{escape(str(item.get('positionNo', '') or ''))}</td>"
                f"<td>{escape(str(item.get('qty', '') or ''))}</td>"
                f"<td>{_service_symbol(int(item.get('service', 1) or 1))}</td>"
                f'<td class="{_value_class(item)}">{escape(str(item.get("unitPrice", "") or ""))}</td>'
                f"{discount_cell}"
                f'<td class="{_value_class(item)}">{escape(str(item.get("total", "") or ""))}</td>'
                "</tr>"
            )
    if not rows:
        return ""
    discount_header = "<td style=\"min-width: 68px\"><p>Discount</p></td>" if display_discounts == 1 else ""
    return (
        f'<div class="introduce-text"><p>{escape(title)}</p></div>'
        '<table class="table-blue"><thead><tr class="bold">'
        '<td style="min-width: 40px"><p>NO.</p></td>'
        '<td style="min-width: 40px"><p>Model</p></td>'
        '<td style="min-width: 100px"><p>POSITION NO.</p></td>'
        '<td style="min-width: 40px"><p>Q\'ty</p></td>'
        '<td style="min-width: 60px"><p>Service</p></td>'
        '<td style="min-width: 74px"><p>Unit Price</p></td>'
        f'{discount_header}'
        '<td style="min-width: 50px"><p>Total</p></td>'
        '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
    )


def _service_symbol(value: int) -> str:
    if value == 1:
        return "✕"
    if value == 2:
        return "○"
    return "△"


def _value_class(item: dict[str, Any]) -> str:
    classes: list[str] = []
    if item.get("fixedAppendFlag"):
        classes.append("blue")
    if int(item.get("discountType", 1) or 1) == 2 and not item.get("fixedAppendFlag"):
        classes.append("line-through")
    return " ".join(classes)
