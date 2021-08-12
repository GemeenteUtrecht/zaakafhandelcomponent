import { Component, HostBinding, Input } from '@angular/core';

@Component({
  // tslint:disable-next-line:component-selector
  selector: '[gu-button]',
  templateUrl: './button.component.html',
  styleUrls: ['./button.component.scss']
})
export class ButtonComponent {
  @Input() type: 'primary' | 'secondary' | 'tertiary' | 'action-link' = 'primary';
  @Input() size?: 'extrasmall' | 'small' | 'medium' | 'large' = 'medium';
  @Input() noPadding?: boolean;
  @Input() loading?: boolean;
  @Input() icon?: string;
  @Input() class = '';
  @Input() disabled?: boolean;

  @HostBinding('attr.disabled')
  get disable() {
    return this.disabled ? 'disabled' : null;
  }

  @HostBinding('attr.class')
  get buttonType() {
    if (this.type === 'action-link') {
      return [
        'action-link',
        this.class
      ].filter(Boolean).join(' ')
    } else {
      return [
        'btn',
        `btn--${this.type}`,
        `btn--${this.size}`,
        this.loading ? `btn__spinner` : null,
        this.loading ? `btn__spinner--${this.type}` : null,
        this.class
      ].filter(Boolean).join(' ')
    }
  };
}
