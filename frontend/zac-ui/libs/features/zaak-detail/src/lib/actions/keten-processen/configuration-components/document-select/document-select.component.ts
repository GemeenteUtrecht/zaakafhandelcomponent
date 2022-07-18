import { ChangeDetectorRef, Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { TaskContextData } from '../../../../../models/task-context';
import { FormArray, FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient } from '@gu/services';
import { KetenProcessenService } from '../../keten-processen.service';
import { atleastOneValidator } from '@gu/utils';
import { InformatieObjectType, ReadWriteDocument } from '@gu/models';
import { ModalService } from '@gu/components';

/**
 * <gu-document-select [taskContextData]="taskContextData"></gu-document-select>
 *
 * This is a configuration component for document select tasks.
 *
 * Requires taskContextData: TaskContextData input for the form layout.
 *
 * Emits successReload: boolean after successfully submitting the form.
 */
@Component({
  selector: 'gu-document-select',
  templateUrl: './document-select.component.html',
  styleUrls: ['../configuration-components.scss']
})
export class DocumentSelectComponent implements OnChanges {
  @Input() taskContextData: TaskContextData;

  @Output() successReload: EventEmitter<boolean> = new EventEmitter<boolean>();

  selectDocumentsForm: FormGroup

  isSubmitting: boolean;
  submitSuccess: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  openSelectorsArray: number[] = [];

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private ketenProcessenService: KetenProcessenService,
    private modalService: ModalService,
    private cdRef: ChangeDetectorRef
  ) { }

  //
  // Getters / setters.
  //


  get documents(): FormArray {
    return this.selectDocumentsForm.get('documents') as FormArray;
  };

  get documentTypes(): FormArray {
    return this.selectDocumentsForm.get('documentTypes') as FormArray;
  };

  documentType(index: number): FormControl {
    return this.documentTypes.at(index) as FormControl;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes: SimpleChanges): void {
    this.selectDocumentsForm = this.fb.group({
      documents: this.addDocumentCheckboxes(),
      documentTypes: this.addDocumentTypes()
    }, Validators.required)
    if (changes.taskContextData.previousValue !== this.taskContextData ) {
      this.selectDocumentsForm = this.fb.group({
        documents: this.addDocumentCheckboxes(),
        documentTypes: this.addDocumentTypes()
      }, Validators.required)
    }
  }

  //
  // Context.
  //

  /**
   * Creates form array for document checkboxes.
   * @returns {FormArray}
   */
  addDocumentCheckboxes(): FormArray {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control(false);
    });
    return this.fb.array(arr, atleastOneValidator());
  }

  /**
   * Create form array for document types.
   * @returns {FormArray}
   */
  addDocumentTypes(): FormArray {
    const arr = this.taskContextData.context.documents.map(() => {
      return this.fb.control('');
    });
    return this.fb.array(arr);
  }

  /**
   * PUTs form data to API.
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
   * Open document
   * @param url
   */
  readDocument(url) {
    this.ketenProcessenService.readDocument(url).subscribe((res: ReadWriteDocument) => {
      window.open(res.magicUrl, "_blank");
    });
  }

  findDocumentTypeObject(documentType): InformatieObjectType {
    return this.taskContextData.context.informatieobjecttypen
      .filter(type => {
        return type.omschrijving === documentType;
      })[0]
  }

  //
  // Events.
  //

  /**
   * Show document type multiselect to change document type.
   * @param {number} i
   */
  openDocumentTypeSelector(i: number) {
    this.openSelectorsArray.push(i);
  }

  /**
   * Hides document type multiselect
   * @param {number} i
   */
  closeDocumentTypeSelector(i: number) {
    const index = this.openSelectorsArray.indexOf(i);
    if (index !== -1) {
      this.openSelectorsArray.splice(index, 1);
    }
    this.documentType(i).patchValue(null)
  }

  /**
   * Creates form data for request.
   */
  submitForm() {
    this.isSubmitting = true;

    const selectedDocuments = this.documents.value
      .map((checked, i) => {
        if (checked) {
          // Check if document type has been changed by user
          const documentTypeObject = this.documentType(i).value ? this.findDocumentTypeObject(this.documentType(i).value) : this.findDocumentTypeObject(this.taskContextData.context.documents[i].documentType);

          // If document type doesn't exist in list if informatieobject types
          if (!documentTypeObject) {
            this.documentType(i).setErrors({noMatchingDocumentType: true})
            this.cdRef.detectChanges();
            return null;
          }
          return {
            document: this.taskContextData.context.documents[i].url,
            documentType: documentTypeObject.url
          };
        }
        return null;
      })
      .filter(v => v !== null);

    const formData = {
      form: this.taskContextData.form,
      selectedDocuments: selectedDocuments,
    };

    if (this.selectDocumentsForm.valid) {
      this.putForm(formData);
    }

    this.isSubmitting = false;
  }

}
