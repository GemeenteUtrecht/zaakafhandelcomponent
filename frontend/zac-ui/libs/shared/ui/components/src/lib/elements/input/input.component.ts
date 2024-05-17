import {Component, ElementRef, EventEmitter, Input, OnChanges, Output, ViewChild} from '@angular/core';
import {UntypedFormControl} from '@angular/forms';
import {MatFormField} from '@angular/material/form-field';

/**
 * <gu-input [control]="formControl" label="Input">I'm a input field</gu-input>
 *
 * Generic input component, based on mat-input.
 *
 * Requires control: Reactive Form Control
 * Requires type: Type of the input field.
 * Takes label: Label of the input field.
 * Takes required: Sets the input on required.
 * Takes disabled: Disables the input.
 * Takes placeholder: Placeholder for input.
 * Takes value: Sets value for input.
 * Takes autocomplete: Autocomplete.
 *
 */
@Component({
  selector: 'gu-input',
  templateUrl: './input.component.html',
  styleUrls: ['./input.component.scss']
})
export class InputComponent implements OnChanges {
  @Input() control: UntypedFormControl;
  @Input() datalist: string[] = [];
  @Input() type: string;
  @Input() label: string;
  @Input() maxlength: string;
  @Input() required: boolean;
  @Input() disabled: boolean;
  @Input() pattern: string = null;
  @Input() placeholder: string;
  @Input() value: string | number;
  @Input() autocomplete?: 'on' | 'off';
  @Input() hideNotRequiredLabel: boolean;

  @Input() appearance: 'outline' | 'fill' = 'outline';

  @Output() input: EventEmitter<any> = new EventEmitter<any>();

  @ViewChild('inputRef') inputRef: ElementRef;

  datalistId = '';

  ngOnChanges() {
    if (!this.datalist.length) {
      return null;
    }
    this.datalistId = this.inputRef.nativeElement.id + '-datalist';
  }
}

/**
 * The gap between the label and the outline border is hardcoded in Material Form Field.
 * We want to change the font size of the label, but the gap is not scaling with it.
 * This function makes it possible to customise the gap size.
 *
 * https://github.com/angular/components/issues/16411#issuecomment-631436630
 */
export function patchMatFormField() {
  const patchedFormFieldClass = MatFormField.prototype as any;

  patchedFormFieldClass.updateOutlineGapOriginal = MatFormField.prototype.updateOutlineGap;
  MatFormField.prototype.updateOutlineGap = function () {
    this.updateOutlineGapOriginal();
    const container = this._connectionContainerRef.nativeElement;
    const gapEls = container.querySelectorAll('.mat-form-field-outline-gap');
    gapEls.forEach((gp) => {
      const calculatedGapWidth = +gp.style.width.replace('px', '');
      const gapWidth = calculatedGapWidth / 0.9;
      gp.style.width = `${gapWidth}px`;
    });
  };
}
