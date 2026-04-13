import { Component, Input } from '@angular/core';
@Component({
  selector: 'wk-trade-ui-engineering-pdf',
  templateUrl: './engineering-pdf.component.html',
  styleUrls: ['./engineering-pdf.component.less'],
})
export class EngineeringPdfComponent {
  @Input() formData: any; //报价单数据
  @Input() quotationTemplate: number; //报价单模板
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() taxRate: boolean; //是否显示税率
  @Input() currencyName: string; //币种名称;

  @Input() quotationType = 1; //报价单类型，默认是1：工程报价; 如果是8的是蓝色科技报价单，只有表头不一样
}
