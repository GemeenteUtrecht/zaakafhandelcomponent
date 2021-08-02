import {
  AfterViewInit, ChangeDetectorRef,
  Component,
  ContentChildren,
  Input,
  QueryList,
  ViewChild,
  ViewContainerRef
} from '@angular/core';
import { MAT_TAB_GROUP, MatTab, MatTabGroup } from '@angular/material/tabs';
import { TabComponent } from './tab.component';

@Component({
  selector: 'gu-tab-group',
  templateUrl: './tab-group.component.html',
  providers: [
    {
      provide: MAT_TAB_GROUP,
      useValue: undefined,
    },
  ],
})
export class TabGroupComponent implements AfterViewInit {
  @Input() alignTabs: 'start' | 'center' | 'end' = 'start'
  @Input() selectedIndex = 0;

  @ViewChild('tabBodyWrapper')
  tabBodyWrapper: MatTabGroup;

  @ContentChildren(TabComponent)
  tabs: QueryList<TabComponent>;

  @ViewChild('outlet', { read: ViewContainerRef }) container;

  constructor(private cdRef: ChangeDetectorRef) {}

  public ngAfterViewInit() {
    const matTabsFromQueryList = this.tabs.map(tab => tab.matTab);
    const list = new QueryList<MatTab>();
    list.reset([matTabsFromQueryList]);
    this.tabBodyWrapper._tabs = list;
    this.tabBodyWrapper.selectedIndex = this.selectedIndex;
    this.tabBodyWrapper.ngAfterContentChecked();
    this.cdRef.detectChanges();
  }
}
