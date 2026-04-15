import { Component, Input } from '@angular/core';
@Component({
  selector: 'wk-trade-ui-product-pdf',
  templateUrl: './product-pdf.component.html',
  styleUrls: ['./product-pdf.component.less'],
})
export class ProductPdfComponent {
  @Input() formData: any; //报价单数据
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() taxRate: boolean; //是否显示税率
  @Input() currencyName: string; //币种名称;
}
