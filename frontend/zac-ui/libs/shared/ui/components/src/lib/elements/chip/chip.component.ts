import { Component, Input } from '@angular/core';

@Component({
  selector: 'gu-chip',
  templateUrl: './chip.component.html',
  styleUrls: ['./chip.component.scss']
})
export class ChipComponent {

  @Input() color: 'primary' | 'secondary' | 'tertiary' | 'warn'
  @Input() type: 'badge'
  @Input() icon: string;

}
