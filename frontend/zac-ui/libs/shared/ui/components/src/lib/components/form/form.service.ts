import {Injectable} from '@angular/core';
import {UntypedFormControl, UntypedFormGroup, Validators} from '@angular/forms';
import {Field, FieldConfiguration} from './field';
import {Document} from '@gu/models';


@Injectable()
export class FormService {
  /**
   * Returns whether a Field(Configuration) is active within the context of a form.
   * @param {FormGroup} formGroup
   * @param {Field|FieldConfiguration} field
   * @return {boolean}
   */
  isFieldActive(formGroup: UntypedFormGroup, field: Field | FieldConfiguration): boolean {
    return !field.activeWhen || field.activeWhen(formGroup)
  }

  /**
   * Returns the keys for every Field(Configuration) in the form.
   * @param {FieldConfiguration[]} form
   * @return {string[]}
   */
  getKeysFromForm(form: FieldConfiguration[]): string[] {
    return form.map((fieldConfiguration: FieldConfiguration) => this.getKeyFromFieldConfiguration(fieldConfiguration));
  }

  /**
   * Returns the key for a Field(Configuration).
   * @param {Field|FieldConfiguration} field
   * @return {string}
   */
  getKeyFromFieldConfiguration(field: Field | FieldConfiguration): string {
    return field.key || field.name || field.label;
  }

  /**
   * Returns the name for a Field(Configuration).
   * @param {Field|FieldConfiguration} field
   * @return {string}
   */
  getNameFromFieldConfiguration(field: Field | FieldConfiguration): string {
    return field.name || field.key || field.label;
  }

  /**
   * Returns field configuration as needle in haystack form.
   * @param {FieldConfiguration[]} form
   * @param {string} key
   * @return {FieldConfiguration}
   */
  getFieldConfigurationByKey(form: FieldConfiguration[], key: string): FieldConfiguration {
    return form.find((fieldConfiguration: FieldConfiguration) => this.getKeyFromFieldConfiguration(fieldConfiguration) === key);
  }

  /**
   * Sets validators on field.
   * @param {FormGroup} formGroup
   * @param {Field|FieldConfiguration} field
   */
  setValidators(formGroup: UntypedFormGroup, field: Field | FieldConfiguration): void {
    const isActive = this.isFieldActive(formGroup, field)
    const isRequired = typeof field.required === "boolean" ? field.required : true;
    const key = this.getKeyFromFieldConfiguration(field);
    const _field = formGroup.get(key);

    if (!_field) {
      return;
    }

    _field.clearValidators();

    if (isActive && isRequired) {
      _field.setValidators([Validators.required])
    }
    _field.updateValueAndValidity();
  }

  /**
   * Creates FormGroup for the given form.
   * @param {FieldConfiguration[]} form
   * @param {string[]} [keys]
   * @return {FormGroup}
   */
  formToFormGroup(form: FieldConfiguration[], keys: string[] = this.getKeysFromForm(form)): UntypedFormGroup {
    const formControls = form

      // Filter FieldConfigurations on keys.
      .filter((fieldConfiguration: FieldConfiguration) => keys.indexOf(this.getKeyFromFieldConfiguration(fieldConfiguration)) > -1)

      // Convert FieldConfigurations to FormGroup instance.
      .reduce((acc, fieldConfiguration: FieldConfiguration) => {
        const key = this.getKeyFromFieldConfiguration(fieldConfiguration);
        const required = typeof fieldConfiguration.required === "boolean" ? fieldConfiguration.required : true;
        acc[key] = new UntypedFormControl(fieldConfiguration.value);
        return acc;
      }, {})

    // @ts-ignore
    const formGroup = new UntypedFormGroup(formControls);
    this.getKeysFromForm(form)
      .forEach((key) => {
        const fieldConfiguration = form[key];

        if (!fieldConfiguration) {
          return;
        }

        this.setValidators(formGroup, fieldConfiguration);
      })

    return formGroup;
  }

  /**
   * Returns all the fields from a formGroup.
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration[]} form
   * @param {string[]} [keys]
   * @param {boolean} [isInEditMode] Whether the form is editable.
   * @return {Field[]}
   */
  formGroupToFields(formGroup: UntypedFormGroup, form: FieldConfiguration[], keys: string[] = this.getKeysFromForm(form), fieldsets = [], isInEditMode: boolean = true, editable?: boolean | string): Field[] {
    return keys
      .map(key => {
        const fieldConfiguration = this.getFieldConfigurationByKey(form, key);
        fieldConfiguration.control = formGroup.controls[key];
        if (fieldsets.length > 0) {
          fieldConfiguration.readonly = (typeof isInEditMode === 'boolean') ? !isInEditMode : fieldConfiguration.readonly;
        } else {
          fieldConfiguration.readonly = (typeof editable === 'string') && !fieldConfiguration.readonly ? !isInEditMode : fieldConfiguration.readonly;
        }
        return new Field(fieldConfiguration);
      });
  }

  /**
   * Serializes the form.
   * @param {FormGroup} formGroup
   * @param {FieldConfiguration[]} form
   * @param {string[]} [resolvedKeys]
   * @param {Object} documents
   * @return {Object}
   */
  serializeForm(formGroup, form, resolvedKeys = this.getKeysFromForm(form), documents: { [index: string]: Document } = {}) {

    // Initial serialized data.
    const rawData = formGroup.getRawValue();

    // Update rawData with support for activeWhen, and use name instead of key in resulting object.
    const data = Object.entries(rawData).reduce(
      (acc, [key, value]) => {
        // Find active field by key.
        const field = this.formGroupToFields(formGroup, form, resolvedKeys)
          .filter(this.isFieldActive.bind(this, formGroup))
          .find((_field: Field) => this.getKeyFromFieldConfiguration(_field) === key)

        // Field not found (or not active).
        if (!field) {
          return acc;
        }

        // Use name as key in data.
        const name = this.getNameFromFieldConfiguration(field);

        // Update data.
        acc[name] = value
        return acc;
      }, {}
    );

    // Update data with documents.
    return Object.assign(data, documents)
  }
}
