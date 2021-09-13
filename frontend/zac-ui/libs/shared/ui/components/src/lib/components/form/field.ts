import {AbstractControl} from '@angular/forms';

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
  choices?: Choice[];
  control?: AbstractControl;
  name?: string;
  label?: string;
  pattern?: string;
  placeholder?: string;
  readonly?: boolean;
  required?: boolean
  type?: string;
  value?: string | string[] | number;
  writeonly?: boolean;
  autocomplete?: 'on' | 'off';
  multiple?: boolean;
}

/**
 * A combination of various properties that make up a form field.
 * @class
 */
export class Field {
  choices: Array<Object>;
  control: AbstractControl;
  name?: string;
  label: string;
  pattern?: string;
  placeholder: string;
  readonly?: boolean;
  required: true
  type: string;
  value: any;
  widgetType: string;
  writeonly?: boolean;
  autocomplete?: 'on' | 'off';
  multiple?: boolean;

  /**
   * Construction method.
   * @param {FieldConfiguration} fieldConfiguration
   */
  constructor(fieldConfiguration: FieldConfiguration) {
    Object.assign(this, fieldConfiguration);

    this.label = fieldConfiguration.label || fieldConfiguration.name;
    this.label = this.label.charAt(0).toUpperCase() + this.label.slice(1)

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
