import { Component, Input } from '@angular/core';
@Component({
  selector: 'wk-trade-ui-laboratory-pdf',
  templateUrl: './laboratory-pdf.component.html',
  styleUrls: ['./laboratory-pdf.component.less'],
})
export class LaboratoryPdfComponent {
  @Input() formData: any; //报价单数据
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() currencyName: string; //币种名称;

  isDuplicateName(list, currentIndex: number): boolean {
    for (let i = 0; i < currentIndex; i++) {
      if (this.formData.testingItems[i].group === list.group) {
        return true;
      }
    }
    return false;
  }

  getRowCount(list, currentIndex: number): number {
    let count = 1;
    for (let i = currentIndex + 1; i < this.formData.testingItems.length; i++) {
      if (this.formData.testingItems[i].group === list.group) {
        count++;
      } else {
        break;
      }
    }
    return count;
  }
}
