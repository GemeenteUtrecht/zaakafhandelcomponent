import {Injectable} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {Field, FieldConfiguration} from './field';

@Injectable()
export class FormService {
  /**
   * @param {FieldConfiguration[]} form
   * @return {string[]}
   */
  keysFromForm(form: FieldConfiguration[]): string[] {
    return form.map((fieldConfiguration: FieldConfiguration) => this.keyFromFieldConfiguration(fieldConfiguration));
  }

  /**
   * @param {FieldConfiguration} fieldConfiguration
   * @return {string}
   */
  keyFromFieldConfiguration(fieldConfiguration: FieldConfiguration|Field): string {
    return fieldConfiguration.name || fieldConfiguration.label;
  }


  /**
   * @param {FieldConfiguration[]} form
   * @param {string[]} keys
   * @return {FormGroup}
   */
  objectToFormGroup(form: FieldConfiguration[], keys: string[] = this.keysFromForm(form)): FormGroup {
    const formControls = form

      // Filter FieldConfigurations on keys.
      .filter((fieldConfiguration: FieldConfiguration) => keys.indexOf(this.keyFromFieldConfiguration(fieldConfiguration)) > -1)

      // Convert FieldConfigurations to FormGroup instance.
      .reduce((acc, fieldConfiguration: FieldConfiguration) => {
        const key = this.keyFromFieldConfiguration(fieldConfiguration);
        const required = typeof fieldConfiguration.required === "boolean" ? fieldConfiguration.required : true;

        if (required) {
          acc[key] = new FormControl(fieldConfiguration.value, Validators.required);
        } else {
          acc[key] = new FormControl(fieldConfiguration.value);
        }
        return acc;
      }, {})

    // @ts-ignore
    return new FormGroup(formControls);
  }

  /**
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration[]} form
   * @param {string[]} keys
   * @param {boolean} editable Whether the form is editable.
   * @return {Field}
   */
  formGroupToFields(formGroup: FormGroup, form: FieldConfiguration[], keys: string[] = this.keysFromForm(form), editable: boolean): Field[] {
    return keys
      .map(key => {
        const fieldConfiguration = this.fieldConfigurationByKey(form, key);
        fieldConfiguration.control = formGroup.controls[key];
        fieldConfiguration.readonly = editable ? fieldConfiguration.readonly : true;
        return new Field(fieldConfiguration);
      });
  }

  /**
   * Returns field configuration as needle in haystack form.
   * @param {FieldConfiguration[]} form
   * @param {string} key
   * @return {FieldConfiguration}
   */
  fieldConfigurationByKey(form: FieldConfiguration[], key: string): FieldConfiguration {
    return form.find((fieldConfiguration: FieldConfiguration) => this.keyFromFieldConfiguration(fieldConfiguration) === key);
  }
}
