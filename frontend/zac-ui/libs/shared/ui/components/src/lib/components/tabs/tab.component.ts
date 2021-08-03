import { AfterViewInit, ChangeDetectorRef, Component, ContentChild, Input, QueryList, ViewChild } from '@angular/core';
import { MatTab, MatTabLabel } from '@angular/material/tabs';
import { isNgTemplate } from '@angular/compiler';

@Component({
  selector: 'gu-tab',
  templateUrl: './tab.component.html',
})
export class TabComponent implements AfterViewInit {
  @Input() label: string;

  @ViewChild(MatTab)
  matTab: MatTab;

  @ContentChild(MatTabLabel)
  template: MatTabLabel;

  constructor(private cdRef: ChangeDetectorRef) {}

  ngAfterViewInit() {
    this.matTab.templateLabel = this.template;
    this.cdRef.detectChanges();
  }

}
