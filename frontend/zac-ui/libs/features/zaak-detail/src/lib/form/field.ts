import {FormControl} from "@angular/forms";

export interface FieldConfiguration {
  choices?: Array<{ label: string, value: string }>;
  control?: FormControl;
  name? : string;
  label?: string;
  placeholder?: string;
  readonly? : boolean;
  required?: boolean
  type? : string;
  value?: string;
  writeonly?: boolean;
}

/**
 * A combination of various properties that make up a form field.
 * @class
 */
export class Field<T> {
  choices: Array<Object>;
  control: T;
  name? : string;
  label: string;
  placeholder: string;
  readonly? : boolean;
  required: true
  type: string;
  value: any;
  widgetType: string;
  writeonly?: boolean;

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
