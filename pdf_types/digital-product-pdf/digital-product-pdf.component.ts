import { Component, Input } from '@angular/core';
@Component({
  selector: 'wk-trade-ui-digital-product-pdf',
  templateUrl: './digital-product-pdf.component.html',
  styleUrls: ['./digital-product-pdf.component.less'],
})
export class DigitalProductPdfComponent {
  @Input() formData: any;
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() taxRate: boolean; //是否显示税率
  @Input() currencyName: string; //币种名称;
}
