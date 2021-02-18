import { Component, Input, OnInit } from '@angular/core';
import { AbstractControl, FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FormField, TaskContextData } from '../../../../models/task-context';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { DatePipe } from '@angular/common';

@Component({
  selector: 'gu-dynamic-form',
  templateUrl: './dynamic-form.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DynamicFormComponent implements OnInit {
  @Input() taskContextData: TaskContextData;

  formFields: FormField[];

  //Form
  dynamicForm: FormGroup;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private datePipe: DatePipe
  ) { }

  ngOnInit(): void {
    this.dynamicForm = this.fb.group({});
    this.formFields = this.taskContextData.context.formFields;
    this.formFields.forEach(formField => {
      this.dynamicForm.addControl(formField.name, this.fb.control('', Validators.required));
    })
  }

  get formField() {
    return this.dynamicForm.controls;
  };
}
