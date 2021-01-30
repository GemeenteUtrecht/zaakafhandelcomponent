import { Component, Input, OnInit } from '@angular/core';
import { ControlContainer, FormControl, FormGroup, FormGroupDirective } from '@angular/forms';

@Component({
  selector: 'gu-radio',
  templateUrl: './radio.component.html',
  styleUrls: ['./radio.component.scss'],
  viewProviders: [{ provide: ControlContainer, useExisting: FormGroupDirective }]
})
export class RadioComponent implements OnInit {
  @Input() name: string;
  @Input() id: string;
  @Input() label: string;
  @Input() radioFormControl: string;
  @Input() value: string;

  childForm: FormGroup;

  constructor(private parentForm: FormGroupDirective) {}

  ngOnInit(): void {
    if (this.radioFormControl) {
      this.childForm = this.parentForm.form;
      this.childForm.addControl(this.radioFormControl, new FormControl(''))
    }
  }

}
