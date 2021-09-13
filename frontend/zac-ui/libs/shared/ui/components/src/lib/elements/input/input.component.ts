import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';
import { MatFormField } from '@angular/material/form-field';

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
export class InputComponent {
  @Input() control: FormControl;
  @Input() type: string;
  @Input() label: string;
  @Input() required: boolean;
  @Input() disabled: boolean;
  @Input() pattern: string = null;
  @Input() placeholder: string;
  @Input() value: string | number;
  @Input() autocomplete?: 'on' | 'off';

  /**
   * Creates input label.
   * @returns {string}
   */
  getLabel() {
    return this.required ? this.label : (this.label + ' (niet verplicht)')
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
