import { Component, Input, ViewChild } from '@angular/core';
import { MatTab } from '@angular/material/tabs';

@Component({
  selector: 'gu-tab',
  templateUrl: './tab.component.html',
})
export class TabComponent {
  @Input() label: string;

  @ViewChild(MatTab)
  public matTab: MatTab;

}
