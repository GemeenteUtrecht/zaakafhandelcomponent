import { Component, Input } from '@angular/core';

@Component({
  selector: 'gu-message',
  templateUrl: './message.component.html',
  styleUrls: ['./message.component.scss']
})
export class MessageComponent {
  @Input() title: string;
  @Input() message: string;
  @Input() type: 'primary' | 'success' | 'warn'
  @Input() isHidden: boolean;
}
