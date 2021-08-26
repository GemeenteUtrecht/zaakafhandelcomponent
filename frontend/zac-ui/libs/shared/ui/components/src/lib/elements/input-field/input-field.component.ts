import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'gu-input-field',
  templateUrl: './input-field.component.html',
  styleUrls: ['./input-field.component.scss']
})
export class InputFieldComponent {
  @Input() autocomplete: 'off';
  @Input() control: FormControl;
  @Input() id: string;
  @Input() label: string;
  @Input() pattern: null;
  @Input() placeholder: string;
  @Input() required: boolean;
  @Input() type: 'text' | 'number'
  @Input() value: string | number;
}
