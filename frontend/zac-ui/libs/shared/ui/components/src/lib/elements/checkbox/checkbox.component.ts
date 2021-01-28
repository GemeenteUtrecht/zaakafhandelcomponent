import { Component, Input, OnInit } from '@angular/core';
import { ControlContainer, FormControl, FormGroup, FormGroupDirective } from '@angular/forms';

@Component({
  selector: 'gu-checkbox',
  templateUrl: './checkbox.component.html',
  styleUrls: ['./checkbox.component.scss'],
  // viewProviders: [{ provide: ControlContainer, useExisting: FormGroupDirective }]
})
export class CheckboxComponent implements OnInit {
  @Input() name: string;
  @Input() id: string;
  @Input() label: string;
  @Input() checkboxFormControl: string;
  @Input() value: string;

  // childForm: FormGroup;

  constructor() {}

  ngOnInit(): void {
    // this.childForm = this.parentForm.form;
    // this.childForm.addControl(this.checkboxFormControl, new FormControl(''))
  }

}
