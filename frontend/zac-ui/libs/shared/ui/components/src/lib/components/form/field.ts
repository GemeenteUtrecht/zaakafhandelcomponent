import {AbstractControl, FormGroup} from '@angular/forms';
import {FormService} from './form.service';

/**
 * Choices of a select field. The type of the return value can be different.
 */
export interface Choice {
  label: string,
  value: string | number | object,
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

  /** @type {boolean} Whether a checkbox is checked. */
  checked?: boolean;

  /** @type {Choice[]} An optional array of Choice's, setting this will render the field as <select> instance. */
  choices?: Choice[];

  /** @type {AbstractControl} */
  control?: AbstractControl;

  /** @type {string} The format for this field. */
  format?: string;

  /** @type {string} The unique identifier for this field. */
  key?: string;

  /** @type {string} The label to render for the field. */
  label?: string;

  /** @type {number} The maximum length of the value. */
  maxlength?: number;

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

  /** @type {string | string[] | number | object} The type of the form group value that will be registered on input */
  value?: string | string[] | number | object;

  /** @type {boolean} Whether a select takes multiple values. */
  multiple?: boolean;

  /** @type {Function} Function to call when field changes. */
  onChange?: Function

  /** @type {Function} Function to call when multiselect searches for value. */
  onSearch?: Function

  /** @type {string} Specifies the widget type. */
  widgetType?: string
}

/**
 * A group of fields.
 */
export interface FieldsetConfiguration {
  /** The fieldset label. */
  label: string;

  /** The FieldConfiguration keys to render as part of this fiedlset. */
  keys: string[];

  /** Optional description. */
  description?: string

}

/**
 * A combination of various properties that make up a form field.
 * @see {FieldConfiguration} for description of properties.
 * @class
 */
export class Field {
  activeWhen?: Function;
  autocomplete?: 'on' | 'off';
  checked?: boolean;
  choices: Array<Choice>;
  control: AbstractControl;
  edit: boolean;
  format?: string;
  key?: string;
  label: string;
  maxlength?: string;
  name?: string;
  pattern?: string;
  placeholder: string;
  readonly?: boolean;
  required: boolean
  type: string;
  value: any;
  widgetType: string;
  writeonly?: boolean;
  multiple?: boolean;
  onChange?: Function
  onSearch?: Function


  /**
   * Construction method.
   * @param {FieldConfiguration} fieldConfiguration
   */
  constructor(fieldConfiguration: FieldConfiguration) {
    Object.assign(this, fieldConfiguration);

    const label = (typeof fieldConfiguration.label !== 'undefined') ? fieldConfiguration.label : fieldConfiguration.name;
    this.label = label.charAt(0).toUpperCase() + label.slice(1)
    this.name = new FormService().getNameFromFieldConfiguration(fieldConfiguration);
    this.required = (typeof fieldConfiguration.required === 'boolean') ? fieldConfiguration.required : true;
    this.widgetType = this.getWidgetType(fieldConfiguration);
    this.format = fieldConfiguration.format;
  }

  /**
   * Returns the the "widget type" of a field based on FieldConfiguration.
   * @param {FieldConfiguration} fieldConfiguration
   * @return {string}
   */
  getWidgetType(fieldConfiguration: FieldConfiguration) {
    if (fieldConfiguration.widgetType) {
      return fieldConfiguration.widgetType;
    }

    if (fieldConfiguration.type === 'document') {
      return 'document'
    }

    if (fieldConfiguration.readonly) {
      return 'readonly';
    }

    if (fieldConfiguration.choices) {
      return 'select'
    }

    if (fieldConfiguration.type && fieldConfiguration.type.toUpperCase() !== 'DATE') {
      return fieldConfiguration.type;
    }

    return 'input';
  }
}

/**
 * A fieldset.
 */
export class Fieldset {
  key?: string;
  label: string;
  fields: Field[];
  keys: string[];
  description?: string

  constructor(fieldsetConfiguration: FieldsetConfiguration|Fieldset, form: Field[]) {
    Object.assign(this, fieldsetConfiguration);
    this.fields = form.filter((field: Field) =>
      fieldsetConfiguration.keys.indexOf(new FormService().getKeyFromFieldConfiguration(field)) > -1)

    if(!this.key) {
      this.key = this.keys.join("-");
    }
  }
}
