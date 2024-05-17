import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { FormField, TaskContextData } from '../../../../../models/task-context';
import { KetenProcessenService } from '../../keten-processen.service';
import { DatePipe } from '@angular/common';
import { ModalService } from '@gu/components';

/**
 * <gu-dynamic-form [taskContextData]="taskContextData"></gu-dynamic-form>
 *
 * A Dynamic Form is a specific type of form for a process task.
 * As the name implies, a form will be rendered dynamically according
 * to the input data. The value of "inputType" from the input data
 * specifies what type of input field needs to be displayed.
 *
 * Requires taskContextData: TaskContextData input for the form layout.
 *
 * Emits successReload: boolean after succesfully submitting the form.
 */
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

  dynamicForm: UntypedFormGroup;

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;
  showCloseCaseConfirmation = false;

  constructor(
    private fb: UntypedFormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService,
    private datePipe: DatePipe
  ) {}

  /**
   * Lifecycle hook which detect changes from the component input data.
   * @param {SimpleChanges} changes
   */
  ngOnChanges(changes: SimpleChanges) {
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.addDynamicFormControls()
    }
  }

  /**
   * Create controls for the input fields.
   */
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

  /**
   * Format the component input data to fit the "gu-multiselect" component.
   * @param {string} name
   * @param {Array<string[]>} enumArray
   */
  formatEnumItems(name: string, enumArray: Array<string[]>) {
    const formattedEnumArray = []
    enumArray.forEach(value => {
      formattedEnumArray.push({
        id: value[0],
        name: value[1]
      });
    });
    this.formattedEnumItems[name] = formattedEnumArray;
  }

  /**
   * Format the form data to fit the API.
   */
  submitForm() {
    this.isSubmitting = true;

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

  /**
   * PUT request.
   * @param formData
   */
  putForm(formData) {
    this.ketenProcessenService.putTaskData(this.taskContextData.task.id, formData).subscribe(() => {
      this.isSubmitting = false;
      this.submitSuccess = true;
      this.successReload.emit(true);

      this.modalService.close('ketenprocessenModal');
    }, res => {
      this.isSubmitting = false;
      this.submitErrorMessage = res.error.detail ? res.error.detail : "Er is een fout opgetreden";
      this.submitHasError = true;
    })
  }

  /**
   * Format the boolean input type to fit the "gu-multiselect" component.
   * @param {string} groupName
   */
  formatBooleanItems(groupName: string) {
    this.formattedBooleanItems[groupName] = [
      {id: true, name: "Ja"},
      {id: false, name: "Nee"}
    ];
  }

  /**
   * Get the form control of the input field.
   * @param {string} name
   * @returns {FormControl}
   */
  dynamicFormField(name: string): UntypedFormControl {
    return this.dynamicForm.get(name) as UntypedFormControl;
  }
}
