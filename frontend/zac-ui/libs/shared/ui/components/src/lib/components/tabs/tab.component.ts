import {Component, Input} from '@angular/core';

@Component({
  selector: 'gu-tab',
  templateUrl: './tab.component.html',
})
export class TabComponent {
  @Input() label = '';
}
