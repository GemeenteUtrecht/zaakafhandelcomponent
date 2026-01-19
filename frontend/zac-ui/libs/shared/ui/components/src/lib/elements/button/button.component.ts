import { Component, HostBinding, Input } from '@angular/core';

@Component({
  // tslint:disable-next-line:component-selector
  selector: '[gu-button]',
  templateUrl: './button.component.html',
  styleUrls: ['./button.component.scss']
})
export class ButtonComponent {
  @Input() buttonStyle: 'primary' | 'secondary' | 'tertiary' | 'action-button' | 'action-link' | 'danger' = 'primary';
  @Input() buttonType: 'danger';
  @Input() size?: 'extrasmall' | 'small' | 'medium' | 'large' | 'huge' = 'medium';
  @Input() noPadding?: boolean;
  @Input() loading?: boolean;
  @Input() icon?: string;
  @Input() class = '';
  @Input() disabled?: boolean;
  @Input() hidden?: boolean;

  @HostBinding('attr.disabled')
  get disable() {
    return this.disabled ? 'disabled' : null;
  }

  @HostBinding('attr.hidden')
  get hide() {
    return this.hidden ? 'hidden' : null;
  }

  @HostBinding('attr.class')
  get buttonClass() {
    if (this.buttonStyle === 'action-link') {
      return [
        'action-link',
        this.class
      ].filter(Boolean).join(' ')
    } else {
      return [
        'btn',
        `btn--${this.buttonStyle}`,
        `btn--${this.buttonType}`,
        `btn--${this.size}`,
        this.loading ? `btn__spinner` : null,
        this.loading ? `btn__spinner--${this.buttonStyle}` : null,
        this.class
      ].filter(Boolean).join(' ')
    }
  };
}
