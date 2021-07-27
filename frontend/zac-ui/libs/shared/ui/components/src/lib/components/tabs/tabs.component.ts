import {Component, Input} from '@angular/core';

@Component({
  selector: 'gu-tabs',
  templateUrl: './tabs.component.html',
})
export class TabsComponent {
  @Input() selectedIndex: number = null;
}
