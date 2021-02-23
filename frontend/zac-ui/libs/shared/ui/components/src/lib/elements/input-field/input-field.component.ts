import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'gu-input-field',
  templateUrl: './input-field.component.html',
  styleUrls: ['./input-field.component.scss']
})
export class InputFieldComponent {
  @Input() type: 'text' | 'number'
  @Input() control: FormControl;
  @Input() label: string;
  @Input() id: string;
  @Input() placeholder: string;
  @Input() required: boolean;
  @Input() value: string | number;
  @Input() autocomplete: 'off';
}
