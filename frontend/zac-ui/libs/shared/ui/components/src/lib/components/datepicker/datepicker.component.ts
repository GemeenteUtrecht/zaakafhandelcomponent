import { Component, Input, OnChanges, OnInit, SimpleChanges } from '@angular/core';
import { ControlContainer, UntypedFormControl, NgForm } from '@angular/forms';
import { MAT_DATE_FORMATS } from '@angular/material/core';

export const APP_DATE_FORMATS =
  {
    parse: {
      dateInput: { month: 'short', year: 'numeric', day: 'numeric' },
    },
    display: {
      dateInput: { month: 'short', year: 'numeric', day: 'numeric' },
      monthYearLabel: { year: 'numeric' }
    }
  };

/**
 * <gu-datepicker [control]="formControl" label="Datum">I'm a datepicker</gu-datepicker>
 *
 * Generic datepicker component, based on mat-datepicker.
 *
 * Requires control: Reactive Form Control
 * Takes label: Label of the datepicker
 * Takes id: Id of the datepicker
 * Takes minDate: Minimum selectable date.
 * Takes required: Sets the input on required.
 *
 */
@Component({
  selector: 'gu-datepicker',
  templateUrl: './datepicker.component.html',
  styleUrls: ['../../elements/input/input.component.scss'],
  providers: [{ provide: MAT_DATE_FORMATS, useValue: APP_DATE_FORMATS }],
  viewProviders: [ { provide: ControlContainer, useExisting: NgForm } ]
})
export class DatepickerComponent implements OnInit, OnChanges {
  @Input() control: UntypedFormControl;
  @Input() label: string;
  @Input() id: string;
  @Input() minDate: Date;
  @Input() required: boolean;
  @Input() placeholder: string;

  readonly defaultMinDate = new Date();

  constructor() { }

  ngOnInit() {
    this.checkValidValue();
  }

  ngOnChanges(changes:SimpleChanges) {
    this.minDate = this.minDate ? this.minDate : this.defaultMinDate;
    this.checkValidValue();
  }

  /**
   * Check if the value is not before the minimum date.
   * If the selected value is before the minimum date,
   * it will execute clearValue().
   */
  checkValidValue() {
    const selectedValueDate = this.control.value ? new Date(this.control.value) : null;
    const minValueDate = new Date(this.minDate.toDateString());
    if (selectedValueDate && (selectedValueDate < minValueDate)) {
      this.clearValue();
    }
  }

  /**
   * Clear the selected value.
   */
  clearValue() {
    this.control.patchValue(null)
  }
}

