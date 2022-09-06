import {Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges} from '@angular/core';
import {FormGroup} from '@angular/forms';
import {Choice, Field, FieldConfiguration, Fieldset, FieldsetConfiguration} from './field';
import {FormService} from './form.service';
import {Document, ReadWriteDocument, Zaak} from '@gu/models';
import {DocumentenService} from '@gu/services';


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
export class FormComponent implements OnInit, OnChanges {
  @Input() form: FieldConfiguration[] = [];
  @Input() fieldsets: FieldsetConfiguration[] = [];
  @Input() buttonLabel = 'Opslaan';
  @Input() buttonSize: 'small' | 'large' = 'large';
  @Input() editable: boolean | string = true;
  @Input() title = '';
  @Input() keys?: string[] = null;
  @Input() resetAfterSubmit = false;
  @Input() showLess: boolean;
  @Input() showEditOnHover: boolean;
  @Input() isLoading = false;

  @Input() zaak: Zaak;

  @Output() formChange: EventEmitter<any> = new EventEmitter<any>();
  @Output() formSubmit: EventEmitter<any> = new EventEmitter<any>();

  /**
   * @type {Object} Documents mapping.
   */
  documents: { [index: string]: Document } = {}

  /**
   * @type {boolean} Whether the form is in edit mode.
   */
  edit: boolean;

  /**
   * @type {Field[]} The fields to render.
   */
  fields!: Field[]

  /**
   * @type {Fieldset[]} The _fieldsets to render.
   */
  _fieldsets: Fieldset[] = [];

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
  constructor(private documentenService: DocumentenService, private formService: FormService) {
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
    this.getContextData();
  }

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   * @param {SimpleChanges} changes
   */
  ngOnChanges(changes: SimpleChanges): void {
    const a = changes.form?.currentValue;
    const b = changes.form?.previousValue;

    if (!a || !b) {
      return;
    }

    // Can we optimize this?
    try {
      if (JSON.stringify(a) === JSON.stringify(b)) {
        return;
      }
    } catch (e) {
      return;
    }

    this.getContextData()
  }

  //
  // Context.
  //

  getContextData(): void {
    if (this.editable === 'toggle') {
      this.edit = false;
    } else {
      this.edit = Boolean(this.editable);
    }

    this.resolvedKeys = this.keys || this.formService.getKeysFromForm(this.form);
    this.formGroup = this.formService.formToFormGroup(this.form, this.resolvedKeys);

    this.updateFields();
    this.updateFieldsets();
  }

  /**
   * Returns the form fields.
   * @return {Field[]}
   */
  getFields(): Field[] {
    return this.formService.formGroupToFields(this.formGroup, this.form, this.resolvedKeys, this.edit)
      .map((field: Field): Field => {
        this.formService.setValidators(this.formGroup, field);
        return field
      })
      .filter(this.formService.isFieldActive.bind(this, this.formGroup)) // Evaluate activeWhen.
  }

  /**
   * Updates this.fields in place.
   */
  updateFields(): void {
    const fields = this.getFields();

    if (!this.fields) {
      this.fields = fields;
      return
    }

    // Update fields.
    fields.forEach((field) => {
      const otherField = this.fields.find((f) => f.name === field.name)

      if (!otherField) {
        this.fields.push(field)
      } else {
        Object.assign(otherField, field);
      }
    });

    const previousFields = this.fields.map((field) => field.name)
    const nextFields = fields.map((field) => field.name)
    const removedFields = previousFields.filter((key) => nextFields.indexOf(key) === -1)

    // Field is removed, remove from fields.
    removedFields.forEach((name) => {
      this.fields = this.fields.filter((field) => field.name !== name)
    });

    // Sort fields by original order.
    this.fields = this.fields.sort((a, b) => {
      const indexA = this.resolvedKeys.findIndex(key => key === this.formService.getKeyFromFieldConfiguration(a))
      const indexB = this.resolvedKeys.findIndex(key => key === this.formService.getKeyFromFieldConfiguration(b))
      return indexA - indexB;
    })
  }

  /**
   * Updates this._fieldsets in place.
   */
  updateFieldsets() {
    // if (this._fieldsets.length) {
    //   this._fieldsets = this._fieldsets.map((fieldsetConfiguration: Fieldset): Fieldset => {
    //   return new Fieldset(fieldsetConfiguration, this.fields)
    //   })
    // }

    const fieldsets = this._fieldsets.length
      ? this._fieldsets
      : this.fieldsets.length
        ? this.fieldsets
        : [{label: '', keys: this.formService.getKeysFromForm(this.form)}]

    this._fieldsets = fieldsets.map((fieldsetConfiguration: FieldsetConfiguration|Fieldset): Fieldset => {
      return new Fieldset(fieldsetConfiguration, this.fields)
    })
  }

  /**
   * Returns whether the toggle should be shown.
   * @return {boolean}
   */
  isToggleable(): boolean {
    switch (typeof this.editable) {
      case 'boolean':
        // Predefined form state, don't toggle.
        return false;

      case 'string':
        // Check if properly set to toggle.
        if (this.editable !== 'toggle') {
          throw new Error('Invalid value for editable input in form');
        }

        // Always show toggle for form.
        if (!this.showEditOnHover) {
          return true;
        }

        // Show toggle based on hover.
        return this.isHovered;
    }
  }

  //
  // Events.
  //

  /**
   * Retrieve read link for document.
   * @param {string} url
   */
  onDocumentClick(url) {
    this.documentenService.readDocument(url).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_self");
    })
  }

  /**
   * Gets called when a document is uploaded.
   * @param {Field} field
   * @param {Document} document
   */
  onUploadedDocument(field: Field, document: Document) {
    this.documents[field.name] = document;
    field.edit = false;
  }

  /**
   * Unlinks a document from the form.
   * The document will not be deleted.
   * @param {Field} field
   */
  removeDocument(field: Field) {
    delete this.documents[field.name]
    field.edit = false;
  }

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
      if (!this.edit) {
        // reset to initial form values when exiting edit mode
        this.resolvedKeys = this.keys || this.formService.getKeysFromForm(this.form);
        this.formGroup = this.formService.formToFormGroup(this.form, this.resolvedKeys);
      }
      this.updateFields();
      this.updateFieldsets();
    }
  }

  /**
   * Gets called when input is changed.
   */
  inputChanged(event, field: Field) {
    this.updateFields();
    this.updateFieldsets();
    this.formChange.emit(this.formGroup.getRawValue())
    if (field.onChange) {
      field.onChange(event, field);
    }
  }

  /**
   * Gets called when select is changed.
   * @param {Choice} choice
   * @param {Field} field
   */
  selectChanged(choice: Choice, field: Field): void {
    field.control.markAsDirty();
    field.control.markAsTouched();
    this.updateFields();
    this.updateFieldsets();
    this.formChange.emit(this.formGroup.getRawValue())
    if (field.onChange) {
      field.onChange(choice, field)
    }
  }

  selectSearch(term: string, field: Field): void {
    if (field.onSearch) {
      field.onSearch(term, field);
    }
  }


  /**
   * Serializes data and emits this.formSubmit.
   * Gets called when form is submitted.
   */
  _formSubmit(): void {
    const data = this.formService.serializeForm(this.formGroup, this.form, this.resolvedKeys, this.documents);
    this.formSubmit.emit(data)

    if (this.resetAfterSubmit) {
      this.formGroup.reset();
    }
  }
}
