import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AbstractControl } from '@angular/forms';

/**
 * <gu-checkbox [control]="formControl">I'm a checkbox</gu-checkbox>
 *
 * Generic checkbox component, based on mat-checkbox.
 *
 * Requires control: Reactive Form Control
 * Takes color: defines the color of the checkbox.
 * Takes value: value of the checkbox input.
 * Takes disabled: disables the checkbox.
 *
 * Emits change: output when the checkbox is clicked.
 */
@Component({
  selector: 'gu-checkbox',
  templateUrl: './checkbox.component.html',
  styleUrls: ['./checkbox.component.scss']
})
export class CheckboxComponent {
  @Input() control: AbstractControl;
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() value: string;
  @Input() disabled: 'disabled';

  @Output() change: EventEmitter<boolean> = new EventEmitter<boolean>();

  constructor() {}
}
