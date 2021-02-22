import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FormField, TaskContextData } from '../../../../models/task-context';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-dynamic-form',
  templateUrl: './dynamic-form.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DynamicFormComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  formFields: FormField[];
  formattedEnumItems = {};
  formattedBooleanItems = {};

  dynamicForm: FormGroup;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private datePipe: DatePipe
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.addDynamicFormControls()
    }
  }

  addDynamicFormControls() {
    this.dynamicForm = this.fb.group({});
    this.formFields = this.taskContextData.context.formFields;
    this.formFields.forEach(formField => {
      switch (formField.inputType) {
        case 'enum': this.formatEnumItems(formField.name, formField.enum); break;
        case 'boolean': this.formatBooleanItems(formField.name); break;
      }
      this.dynamicForm.addControl(formField.name, this.fb.control(formField.value, Validators.required));
    })
  }

  formatEnumItems(name: string, enumArray: Array<string[]>) {
    const formattedEnumArray = []
    enumArray.forEach(value => {
      formattedEnumArray.push({
        id: value[0]
      });
    });
    this.formattedEnumItems[name] = formattedEnumArray;
  }

  submitForm() {
    const formData = {
      form: this.taskContextData.form
    }
    Object.keys(this.dynamicForm.controls).forEach((control, i) => {
      const inputType = this.formFields[i].inputType;
      let value = this.dynamicForm.get(control).value;
      switch (inputType) {
        case 'date':
          value = this.datePipe.transform(value, "yyyy-MM-dd hh:mm:ss");
          break;
        case 'int': value = parseInt(value, 10); break;
      }
      formData[control] = value;
    })
    this.putForm(formData);
  }

  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);
    }, error => {
      this.isSubmitting = false;
      this.submitErrorMessage = error.detail ? error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

  formatBooleanItems(groupName: string) {
    this.formattedBooleanItems[groupName] = [
      {id: true, name: "Ja"},
      {id: false, name: "Nee"}
    ];
  }

  get formField() {
    return this.dynamicForm.controls;
  };

  dynamicFormField(name: string): FormControl {
    return this.dynamicForm.get(name) as FormControl;
  }
}
