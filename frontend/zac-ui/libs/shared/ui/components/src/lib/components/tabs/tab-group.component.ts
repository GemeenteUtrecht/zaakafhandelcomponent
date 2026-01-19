import {
  AfterViewInit,
  Component,
  ContentChildren,
  Input,
  QueryList,
  ViewChild,
  ViewContainerRef
} from '@angular/core';
import { MAT_TAB_GROUP, MatTab, MatTabGroup } from '@angular/material/tabs';
import { TabComponent } from './tab.component';

/**
 * <gu-tab-group></gu-tab-group>
 *
 * Generic tab group component, based on mat-tab-group.
 *
 * Takes: alignTabs: position of the tabs.
 * Takes: selectedIndex: index of selected tab.
 */
@Component({
  selector: 'gu-tab-group',
  templateUrl: './tab-group.component.html',
  providers: [
    {
      provide: MAT_TAB_GROUP,
      useValue: undefined,
    },
  ]
})
export class TabGroupComponent implements AfterViewInit {
  @Input() alignTabs: 'start' | 'center' | 'end' = 'start'
  @Input() selectedIndex = 0;

  @ViewChild(MatTabGroup)
  tabBodyWrapper: MatTabGroup;

  @ContentChildren(TabComponent)
  tabs: QueryList<TabComponent>;

  @ViewChild('outlet', { read: ViewContainerRef }) container;

  /**
   * After completing loading the view of the tab group,
   * all the tabs will assigned to the group.
   * This workaround is required because of using a custom
   * wrapper component.
   */
  ngAfterViewInit() {
    const matTabsFromQueryList = this.tabs.map(tab => tab.matTab);
    const list = new QueryList<MatTab>();
    list.reset([matTabsFromQueryList]);
    this.tabBodyWrapper._tabs = list;
    this.tabBodyWrapper.selectedIndex = this.selectedIndex;
    this.tabBodyWrapper.ngAfterContentChecked();
  }
}
