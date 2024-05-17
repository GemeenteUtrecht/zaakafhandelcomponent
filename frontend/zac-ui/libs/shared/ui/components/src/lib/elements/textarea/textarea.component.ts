import { Component, Input } from '@angular/core';
import { UntypedFormControl } from '@angular/forms';

/**
 * <gu-textarea [control]="formControl" label="Textarea">I'm a textarea</gu-textarea>
 *
 * Generic textarea component, based on mat-textarea.
 *
 * Requires control: Reactive Form Control
 * Requires type: Type of the input field.
 * Takes label: Label of the input field.
 * Takes required: Sets the input on required.
 * Takes disabled: Disables the input.
 * Takes placeholder: Placeholder for input.
 * Takes value: Sets value for input.
 *
 */

@Component({
  selector: 'gu-textarea',
  templateUrl: './textarea.component.html',
  styleUrls: ['../../elements/input/input.component.scss']
})
export class TextareaComponent {
  @Input() control: UntypedFormControl;
  @Input() label: string;
  @Input() required: boolean;
  @Input() disabled: boolean;
  @Input() placeholder: string;
  @Input() value: string | number;
  @Input() maxlength: string;
  @Input() minheight: string;
}
