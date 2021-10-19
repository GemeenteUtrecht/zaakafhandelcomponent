import {AbstractControl, FormGroup} from '@angular/forms';
import {FormService} from './form.service';

/**
 * Choices of a select field.
 */
export interface Choice {
  label: string,
  value: string | number,
}

/**
 * Configuration of a field.
 */
export interface FieldConfiguration {
  /**
   * @type {Function} An optional function which, if part of a form, can be used do determine whether a field should be
   * active or not. This can be used create conditional forms based on the (value) of other Field instances.
   *
   * @param {FormGroup} formGroup The form's (main) formGroup is passed as argument, allowing access to its (raw) value
   * using form.getRawValue() or the full serialized data using FormService.serializeForm()
   *
   * @return {boolean} Whether the field should be active.
   */
  activeWhen?: Function;

  /** @type {string} FIXME: should be boolean. */
  autocomplete?: 'on' | 'off';

  /** @type {Choice[]} An optional array of Choice's, setting this will render the field as <select> instance. */
  choices?: Choice[];

  /** @type {AbstractControl} */
  control?: AbstractControl;

  /** @type {string} The unique identifier for this field. */
  key?: string;

  /** @type {string} The label to render for the field. */
  label?: string;

  /** @type {string} The name attribute for the field, this is also used as key in the serialized form. */
  name?: string;

  /** @type {string} Pattern attribute for the field, allowing basic (HTML) validation - DO NOT RELY ON THIS FOR SAFETY. */
  pattern?: string;

  /** @type {string} */
  placeholder?: string;

  /** @type {boolean} Setting this will turn the input in a readonly field. */
  readonly?: boolean;

  /** @type {boolean} Setting this will turn the input in a writeonly  field, only visible during editing. */
  writeonly?: boolean;

  /** @type {string} Whether the field is required. */
  required?: boolean

  /** @type {string} The type attribute for the field. */
  type?: string;

  /** @type {string} */
  value?: string | string[] | number;

  /** @type {boolean} Whether a select takes multiple values. */
  multiple?: boolean;
}

/**
 * A combination of various properties that make up a form field.
 * @see {FieldConfiguration} for description of properties.
 * @class
 */
export class Field {
  activeWhen?: Function;
  autocomplete?: 'on' | 'off';
  choices: Array<Object>;
  control: AbstractControl;
  key?: string;
  label: string;
  name?: string;
  pattern?: string;
  placeholder: string;
  readonly?: boolean;
  required: true
  type: string;
  value: any;
  widgetType: string;
  writeonly?: boolean;
  multiple?: boolean;

  /**
   * Construction method.
   * @param {FieldConfiguration} fieldConfiguration
   */
  constructor(fieldConfiguration: FieldConfiguration) {
    Object.assign(this, fieldConfiguration);

    const label = fieldConfiguration.label || fieldConfiguration.name;
    this.label = label.charAt(0).toUpperCase() + label.slice(1)
    this.name = new FormService().getNameFromFieldConfiguration(fieldConfiguration);

    this.widgetType = this.getWidgetType(fieldConfiguration);
  }

  /**
   * Returns the the "widget type" of a field based on FieldConfiguration.
   * @param {FieldConfiguration} fieldConfiguration
   * @return {string}
   */
  getWidgetType(fieldConfiguration: FieldConfiguration) {
    if (fieldConfiguration.readonly) {
      return 'readonly';
    }

    if (fieldConfiguration.choices) {
      return 'select'
    }

    if (fieldConfiguration.type) {
      return fieldConfiguration.type;
    }

    return 'input';
  }
}
