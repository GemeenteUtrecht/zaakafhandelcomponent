import {Injectable} from '@angular/core';
import {FormControl, FormGroup, Validators} from '@angular/forms';
import {Field, FieldConfiguration} from './field';

@Injectable()
export class FormService {
  /**
   * Returns whether a Field(Configuration) is active within the context of a form.
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration} field
   * @return {boolean}
   */
  isFieldActive(formGroup: FormGroup, field: FieldConfiguration) {
    return !field.activeWhen || field.activeWhen(formGroup)
  }

  /**
   * Returns the keys for every Field(Configuration) in the form.
   * @param {FieldConfiguration[]} form
   * @return {string[]}
   */
  keysFromForm(form: FieldConfiguration[]): string[] {
    return form.map((fieldConfiguration: FieldConfiguration) => this.keyFromFieldConfiguration(fieldConfiguration));
  }

  /**
   * Returns the key for a Field(Configuration).
   * @param {FieldConfiguration} fieldConfiguration
   * @return {string}
   */
  keyFromFieldConfiguration(fieldConfiguration: FieldConfiguration|Field): string {
    return fieldConfiguration.key || fieldConfiguration.name || fieldConfiguration.label;
  }

  /**
   * Returns the name for a Field(Configuration).
   * @param {FieldConfiguration} fieldConfiguration
   * @return {string}
   */
  nameFromFieldConfiguration(fieldConfiguration: FieldConfiguration|Field): string {
    return fieldConfiguration.name || fieldConfiguration.key || fieldConfiguration.label;
  }


  /**
   * Creates FormGroup for the given form.
   * @param {FieldConfiguration[]} form
   * @param {string[]} [keys]
   * @return {FormGroup}
   */
  formToFormGroup(form: FieldConfiguration[], keys: string[] = this.keysFromForm(form)): FormGroup {
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
   * Returns all the fields from a formGroup.
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration[]} form
   * @param {string[]} [keys]
   * @param {boolean} [editable] Whether the form is editable.
   * @return {Field[]}
   */
  formGroupToFields(formGroup: FormGroup, form: FieldConfiguration[], keys: string[] = this.keysFromForm(form), editable: boolean = true): Field[] {
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

  /**
   * Serializes the form.
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration[]} form
   * @param {string[]} [resolvedKeys]
   * @return {Object}
   */
  serializeForm(formGroup, form, resolvedKeys=this.keysFromForm(form)) {

    // Initial serialized data.
    const rawData = formGroup.getRawValue();

    // Update rawData with support for activeWhen, and use name instead of key key in resulting object.
    return Object.entries(rawData).reduce(
      (acc, [key, value]) => {
        // Find active field by key.
        const field = this.formGroupToFields(formGroup, form, resolvedKeys)
          .filter(this.isFieldActive.bind(this, formGroup))
          .find((_field: Field) => this.keyFromFieldConfiguration(_field) === key)

        // Field not found (or not active).
        if(!field) {
          return acc;
        }

        // Use name as key in data.
        const name = this.nameFromFieldConfiguration(field);

        // Update data.
        acc[name] = value
        return acc;
      }, {}
    );
  }
}
