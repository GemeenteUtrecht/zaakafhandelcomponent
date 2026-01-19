import { AfterViewInit, Component, ContentChild, Input, ViewChild } from '@angular/core';
import { MatTab, MatTabLabel } from '@angular/material/tabs';

/**
 * <gu-tab label="tab 1"></gu-tab>
 *
 * Generic tab component, based on mat-tab.
 *
 * Takes label: tab label.
 */
@Component({
  selector: 'gu-tab',
  templateUrl: './tab.component.html',
  styleUrls: ['./tab.component.scss']
})
export class TabComponent implements AfterViewInit {
  @Input() label: string;

  @ViewChild(MatTab)
  matTab: MatTab;

  @ContentChild(MatTabLabel)
  template: MatTabLabel;

  /**
   * If the user uses mat-template-label, the template of that
   * will be inserted after MatTab's view has been initiated.
   * This workaround is required because of using a custom
   * wrapper component.
   */
  ngAfterViewInit() {
    this.matTab.templateLabel = this.template;
  }

}
