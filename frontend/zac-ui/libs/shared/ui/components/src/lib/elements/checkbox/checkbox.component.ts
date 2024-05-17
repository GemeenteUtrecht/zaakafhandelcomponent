import {Component, EventEmitter, Input, Output, OnInit, OnChanges} from '@angular/core';
import {AbstractControl, UntypedFormControl} from '@angular/forms';

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
export class CheckboxComponent implements OnInit, OnChanges {
  @Input() control: AbstractControl = new UntypedFormControl('');
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() value: any;
  @Input() disabled: 'disabled';
  @Input() checked: boolean;

  @Output() change: EventEmitter<any> = new EventEmitter<any>();

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit() {
    this.control.setValue(this.checked);
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes) {
    if (changes.checked) {
      const value = changes.checked.currentValue;
      this.control.setValue(value);
    }
  }

  //
  // Events.
  //

  onChange(event) {
    this.change.emit(event)
  }
}
