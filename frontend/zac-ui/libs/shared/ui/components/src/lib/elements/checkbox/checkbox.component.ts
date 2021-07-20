import { Component, EventEmitter, Input, Output } from '@angular/core';
import { AbstractControl } from '@angular/forms';

@Component({
  selector: 'gu-checkbox',
  templateUrl: './checkbox.component.html',
  styleUrls: ['./checkbox.component.scss']
})
export class CheckboxComponent {
  @Input() name: string;
  @Input() id: string;
  @Input() label: string;
  @Input() control: AbstractControl;
  @Input() value: string;

  @Output() change: EventEmitter<boolean> = new EventEmitter<boolean>();

  constructor() {}
}
