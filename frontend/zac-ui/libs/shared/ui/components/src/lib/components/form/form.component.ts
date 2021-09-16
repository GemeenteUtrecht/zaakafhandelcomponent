import {Component, EventEmitter, Input, OnInit, Output} from '@angular/core';
import {FormGroup} from '@angular/forms';
import {Choice, Field, FieldConfiguration} from './field';
import {FormService} from './form.service';


/**
 * <gu-form [form]="form"></gu-form>
 *
 * Generic form component, can be shown as form or as summary. Can also be configured to allow the user to "toggle"
 * between summary and form.
 *
 * Requires form: FieldConfiguration[] input for main form configuration.
 * Takes buttonLabel: string as submit button label.
 * Takes editable: boolean|'toggle' to indicate whether the form is form or summary mode.
 * Takes keys: string[] to indicate what field in form to render.
 * Takes title: string as form title.
 *
 * Emits formSubmit: Object output when a form is submitted.
 */
@Component({
  providers: [FormService],
  selector: 'gu-form',
  styleUrls: ['./form.component.scss'],
  templateUrl: './form.component.html',
})
export class FormComponent implements OnInit {
  @Input() form: FieldConfiguration[] = [];
  @Input() buttonLabel = 'Opslaan';
  @Input() editable: boolean | string = true;
  @Input() title = '';
  @Input() keys?: string[] = null;
  @Input() showLess: boolean;
  @Input() showEditOnHover: boolean;

  @Output() formSubmit: EventEmitter<any> = new EventEmitter<any>();

  /**
   * @type {boolean} Whether the form is in edit mode.
   */
  edit: boolean;

  /**
   * @type {Field[]} The fields to render.
   */
  fields!: Field[]

  /**
   * @type {FormGroup} The FormGroup used by this form.
   */
  formGroup!: FormGroup;

  /**
   * @type {string[]} Keys resolved either from keys or form.
   */
  resolvedKeys = [];

  isExpanded = false;
  isHovered = false;

  /**
   * Constructor method.
   * @param {FormService} formService
   */
  constructor(private formService: FormService) {
  }

  //
  // Getters / setters.
  //

  /**
   * Returns the fields that are initially visible.
   * @return {Field[]}
   */
  get visibleFields(): Field[] {
    return this.fields.filter((field) => !field.writeonly && field.type !== 'hidden');
  }

  /**
   * Returns fields with type hidden.
   * @return {Field[]}
   */
  get hiddenFields(): Field[] {
    return this.fields.filter((field) => field.type === 'hidden');
  }


  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    if (this.editable === 'toggle') {
      this.edit = false;
    } else {
      this.edit = Boolean(this.editable);
    }

    this.resolvedKeys = this.keys || this.formService.keysFromForm(this.form);
    this.formGroup = this.formService.objectToFormGroup(this.form, this.resolvedKeys);
    this.fields = this.getFields();
  }

  //
  // Context.
  //

  /**
   * Returns the form fields.
   * @return {Field[]}
   */
  getFields(): Field[] {
    return this.formService.formGroupToFields(this.formGroup, this.form, this.resolvedKeys, this.edit);
  }

  //
  // Events.
  //

  /**
   * Gets called when toggle is clicked, performs toggle.
   * @param {Event} [e]
   */
  toggleClick(e: Event): void {
    if (e) {
      e.preventDefault();
    }

    if (this.editable === 'toggle') {
      this.edit = !this.edit;
      this.fields = this.getFields();
    }
  }

  /**
   * Gets called when select is changed.
   * @param {Choice} choice
   * @param {Field} field
   */
  selectChanged(choice: Choice, field: Field): void {
    field.control.markAsDirty()
    field.control.markAsTouched()
  }


  /**
   * Gets called when form is submitted.
   */
  _formSubmit(): void {
    this.formSubmit.emit(this.formGroup.getRawValue())
    this.formGroup.reset();
  }

}
