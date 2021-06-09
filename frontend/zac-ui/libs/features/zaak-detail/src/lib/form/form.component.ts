import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FormGroup} from '@angular/forms';
import {FormService} from './form.service';
import {Field, FieldConfiguration} from "./field";

@Component({
  providers: [FormService],
  selector: 'gu-form',
  styleUrls: ['./form.component.scss'],
  templateUrl: './form.component.html',
})
export class FormComponent implements OnInit {
  edit: boolean;
  fields!: Array<Field<any>>
  formGroup!: FormGroup;
  payLoad = '';

  @Input() title: string = '';
  @Input() editable: boolean | string = true;
  @Input() form: Array<FieldConfiguration> = [];
  @Input() keys?: Array<string> = null;
  @Input() readonlyKeys?: Array<string> = [];

  @Output() submit: EventEmitter<any> = new EventEmitter<any>();

  constructor(private fs: FormService) {
  }

  ngOnInit() {
    if (this.editable === 'toggle') {
      this.edit = false;
    } else {
      this.edit = Boolean(this.editable);
    }

    this.keys = this.keys || this.fs.keysFromForm(this.form);
    this.formGroup = this.fs.objectToFormGroup(this.form, this.keys);
    this.fields = this.getFields();
  }

  /**
   * Swaps boolean value of `this.edit` if `editable` is set to 'toggle'.
   * @param {Event} [e]
   */
  toggleEdit(e) {
    if (e) {
      e.preventDefault();
    }

    if (this.editable === 'toggle') {
      this.edit = !this.edit;
      this.fields = this.getFields();
    }
  }

  /**
   * Returns the form fields.
   * @return {Field[]}
   */
  getFields() {
    return this.fs.formGroupToFields(this.formGroup, this.form, this.keys, this.edit);
  }

  /**
   * Handles a select change.
   * @param choice
   * @param {Field} field
   */
  selectChanged(choice, field: Field<any>) {
    field.control.setValue(choice.value);
    field.control.markAsDirty()
    field.control.markAsTouched()
  }

  _submit() {
    this.submit.emit(this.formGroup.getRawValue())
  }

}
