import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import { AbstractControl, FormControl } from '@angular/forms';

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
export class CheckboxComponent implements OnInit {
  @Input() control: AbstractControl = new FormControl('');
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() value: any;
  @Input() disabled: 'disabled';
  @Input() checked: boolean;

  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  model = false

  ngOnInit() {
    this.model = Boolean(this.checked)
  }

  onChange(event) {
    this.change.emit(event)
  }
}
