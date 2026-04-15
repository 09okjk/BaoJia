import { Component, Input } from '@angular/core';
@Component({
  selector: 'wk-trade-ui-valva-pdf',
  templateUrl: './valva-pdf.component.html',
  styleUrls: ['./valva-pdf.component.less'],
})
export class ValvaPdfComponent {
  @Input() formData: any; //报价单数据
  @Input() quotationTemplate: number; //报价单模板
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() currencyName: string; //币种名称;
}
