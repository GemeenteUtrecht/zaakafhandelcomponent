import { Component, Input } from '@angular/core';
import { FormControl } from '@angular/forms';

@Component({
  selector: 'gu-text-field',
  templateUrl: './text-field.component.html',
  styleUrls: ['./text-field.component.scss']
})
export class TextFieldComponent {
  @Input() control: FormControl;
  @Input() label: string;
  @Input() id: string;
  @Input() placeholder: string;
  @Input() required: boolean;
}
