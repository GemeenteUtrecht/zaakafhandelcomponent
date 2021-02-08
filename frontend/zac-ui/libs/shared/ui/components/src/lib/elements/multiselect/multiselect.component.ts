import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { ControlContainer, FormControl, FormGroup, FormGroupDirective } from '@angular/forms';

@Component({
  selector: 'gu-multiselect',
  templateUrl: './multiselect.component.html',
  styleUrls: ['./multiselect.component.scss'],
  viewProviders: [{ provide: ControlContainer, useExisting: FormGroupDirective }]
})
export class MultiselectComponent implements OnInit {
  @Input() placeholder: string;
  @Input() items = [];
  @Input() bindLabel = 'name';
  @Input() bindValue = 'id'
  @Input() multiple: boolean;
  @Input() customFormControl: string;

  @Output() typeOutput: EventEmitter<any> = new EventEmitter<any>();

  selectedItems: any;

  childForm: FormGroup;

  constructor(private parentForm: FormGroupDirective) {}

  ngOnInit() {
    if (this.customFormControl) {
      this.childForm = this.parentForm.form;
      this.childForm.addControl(this.customFormControl, new FormControl(''))
    }
  }

  onSearch(value){
    this.typeOutput.emit(value.term);
  }
}
