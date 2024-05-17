import { Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { Zaak } from '@gu/models';
import { BenodigdeBijlage, TaskContextData } from '../../../../../../models/task-context';
import { UntypedFormArray, UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { AccountsService, ZaakService } from '@gu/services';
import { SnackbarService } from '@gu/components';
import { SubmittedFields } from '../models/submitted-fields';

/**
 * This component allows the user to upload required
 * documents to start a camunda process.
 */
@Component({
  selector: 'gu-documents-step',
  templateUrl: './documents-step.component.html',
  styleUrls: ['../start-process.component.scss']
})
export class DocumentsStepComponent implements OnChanges {
  @Input() zaak: Zaak;
  @Input() taskContextData: TaskContextData;
  @Input() startProcessDocumentForm: UntypedFormGroup;

  @Output() submittedFields: EventEmitter<SubmittedFields> = new EventEmitter<SubmittedFields>();
  @Output() updateComponents: EventEmitter<boolean> = new EventEmitter<boolean>();

  errorMessage: string;

  submittedDocuments: number[] = [];
  submittingDocuments: number[] = [];

  selectedFiles: File[] = [];

  constructor(
    private fb: UntypedFormBuilder,
    private zaakService: ZaakService,
    private accountsService: AccountsService,
    private snackbarService: SnackbarService,
  ) { }

  //
  // Getters / setters.
  //

  get totalRequired(): number {
    const totalRequired = [];
    this.documentsControl.controls.forEach(c => {
      if (c.hasValidator(Validators.required)) {
        totalRequired.push(c)
      }
    })
    return totalRequired.length ? totalRequired.length : 0;
  }

  get showSaveButton(): boolean {
    return this.submittedDocuments.length <= this.documentsControl.length && this.documentsControl.length > 0;
  }

  get documentsControl(): UntypedFormArray {
    return this.startProcessDocumentForm.get('documents') as UntypedFormArray;
  };

  documentControl(i): UntypedFormControl {
    return this.documentsControl.at(i) as UntypedFormControl;
  }

  //
  // Angular lifecycle.
  //

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.taskContextData) {
      if (changes.taskContextData.previousValue !== this.taskContextData || changes.taskContextData?.firstChange) {
        this.taskContextData.context.benodigdeBijlagen.sort((a, b) => a.order - b.order);
        this.startProcessDocumentForm = this.fb.group({
          documents: this.addDocumentControls()
        })
        this.submittedDocuments = [];
        this.submittingDocuments = [];

        this.submittedFields.emit({
          submitted: 0,
          total: this.documentsControl.controls.length,
          totalRequired: this.totalRequired,
          hasValidForm: this.startProcessDocumentForm.valid
        })
      }
    }
  }

  //
  // Context.
  //

  /**
   * Returns the context for the given index.
   * @param i
   * @returns {BenodigdeBijlage}
   */
  getDocumentsContext(i): BenodigdeBijlage {
    return this.taskContextData.context.benodigdeBijlagen[i];
  }

  /**
   * Creates form controls.
   * @returns {FormArray}
   */
  addDocumentControls(): UntypedFormArray {
    const arr = this.taskContextData.context.benodigdeBijlagen.map(doc => {
      if (doc.required) {
        return this.fb.control('', Validators.required);
      } else {
        return this.fb.control('');
      }
    });
    return this.fb.array(arr);
  }

  /**
   * Checks if document is already submitted.
   * @param i
   * @returns {boolean}
   */
  isSubmittedDocument(i) {
    return this.submittedDocuments.indexOf(i) !== -1;
  }

  //
  // Events
  //

  /**
   * Sets form value when a document is selected.
   * @param {File} file
   * @param {number} i
   * @returns {Promise<void>}
   */
  async handleFileSelect(file: File, i: number) {
    this.documentControl(i).patchValue(file.name);
    this.documentControl(i).markAsTouched();
    this.selectedFiles.push(file);
  }


  /**
   * Loop and post documents
   */
  submitDocuments() {
    this.documentsControl.controls.forEach((control, i) => {
      if (control.value) {
        this.postDocument(i);
      }
    })
  }


  /**
   * Submits the selected document to the API.
   * @param i
   */
  postDocument(i) {
    const selectedDocument = this.getDocumentsContext(i);
    const selectedFile = this.selectedFiles.find( ({ name })  => name === this.documentControl(i).value);
    this.submittingDocuments.push(i)

    const newCaseDocument = new FormData();

    newCaseDocument.append("file", selectedFile);
    newCaseDocument.append("informatieobjecttype", selectedDocument.informatieobjecttype.url);
    newCaseDocument.append("zaak", this.zaak.url);

    this.zaakService.createCaseDocument(newCaseDocument)
      .subscribe(() => {
        this.submittingDocuments = this.submittingDocuments.filter(index => index !== i);
        this.submittedDocuments.push(i);
        this.documentControl(i).setErrors(null);

        // Emit the total submitted documents to parent
        this.submittedFields.emit({
          submitted: this.submittedDocuments.length,
          total: this.documentsControl.controls.length,
          totalRequired: this.totalRequired,
          hasValidForm: this.startProcessDocumentForm.valid
        })

        if (this.submittingDocuments.length === 0) {
          this.updateComponents.emit(true);
        }
        this.documentControl(i).disable()
      }, error => {
        this.submittingDocuments = this.submittingDocuments.filter(index => index !== i);
        this.documentControl(i).enable();
        this.errorMessage = 'Het toevoegen van het document is mislukt.'
        this.reportError(error)
      })
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
