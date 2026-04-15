import { ChangeDetectorRef, Component, Input, OnInit } from '@angular/core';
import {
  CacheDictionaryService,
  Dictionary,
  dictionaryToOptions,
} from '@wk-mhc-ui/common';
@Component({
  selector: 'wk-trade-ui-supercharger-pdf',
  templateUrl: './supercharger-pdf.component.html',
  styleUrls: ['./supercharger-pdf.component.less'],
})
export class SuperchargerPdfComponent implements OnInit {
  starting_Time_Map = null;
  @Input() formData: any;
  @Input() quotationTemplate: number; //报价单模板
  @Input() displayDiscounts: number; //是否显示折扣
  @Input() currencyName: string; //币种名称;

  constructor(
    private cacheDictionaryService: CacheDictionaryService,
    private cd: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.cacheDictionaryService
      .getDictionaryValues(Dictionary.HostRunTime)
      .pipe(dictionaryToOptions())
      .subscribe((res) => {
        const obj = res.reduce((arr, item) => {
          arr[item.value] = item.label;
          return arr;
        }, {});
        this.starting_Time_Map = obj;
        this.cd.markForCheck();
      });
  }
}
