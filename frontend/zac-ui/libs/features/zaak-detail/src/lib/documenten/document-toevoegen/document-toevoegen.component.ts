import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { ApplicationHttpClient } from '@gu/services';
import { FileUploadComponent, ModalService, SnackbarService } from '@gu/components';
import { Document } from '@gu/models';
import { DocumentenService } from '../documenten.service';


/**
 * This component allows users to add or override documents.
 *
 * Requires mainZaakUrl: case url
 * Requires zaaktypeurl: case type url
 * Requires bronorganisatie: organisation
 * Requires identificatie: identification

 * Takes activity: Specifies if the documents are for the activity widget (needs extra field "Beschrijving").
 * Takes documentUrl: When updating a document, the url of the document is needed to know which document needs to be updated.
 *
 * Emits reload: event to notify that the parent component can reload.
 * Emits closeModal: event to notify that the parent component can close the modal.
 * Emits uploadedDocument: emits the url of the uploaded document
 */
@Component({
  selector: 'gu-document-toevoegen',
  templateUrl: './document-toevoegen.component.html',
  styleUrls: ['./document-toevoegen.component.scss']
})
export class DocumentToevoegenComponent implements OnInit {

  @Input() mainZaakUrl: string;
  @Input() zaaktypeurl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() activity: string;
  @Input() documentUrl?: string;
  @Input() updateDocument: boolean;

  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() uploadedDocument: EventEmitter<Document> = new EventEmitter<Document>();

  @ViewChild(FileUploadComponent) private fileUploadComponent: FileUploadComponent

  documentTypes: any;
  addDocumentForm: FormGroup;
  isLoading: boolean;
  isSubmitting: boolean;

  constructor(
    private http: ApplicationHttpClient,
    private documentService: DocumentenService,
    private fb: FormBuilder,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
  ) { }


  //
  // Getters / setters.
  //

  get documentTypeControl(): FormControl {
    return this.addDocumentForm.controls['documentType'] as FormControl;
  }

  get reasonControl(): FormControl {
    return this.addDocumentForm.controls['reason'] as FormControl;
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */

  ngOnInit() {
    this.addDocumentForm = this.fb.group({
      documentFile: this.fb.control("", Validators.required)
    })

    if (!this.updateDocument) {
      const documentTypeControl = this.fb.control("", Validators.required);
      this.addDocumentForm.addControl('documentType', documentTypeControl);
    }

    if (this.updateDocument) {
      const reasonControl = this.fb.control("", Validators.required);
      this.addDocumentForm.addControl('reason', reasonControl);
    }

    this.fetchDocumentTypes()
  }

  //
  // Context.
  //

  /**
   * Fetch document types.
   */
  fetchDocumentTypes() {
    this.isLoading = true;
    if (this.mainZaakUrl) {
      this.documentService.getDocumentTypes(this.mainZaakUrl).subscribe( res => {
        this.documentTypes = res;
      })
    }
  }

  /**
   * Submit form.
   */
  submitForm(): void {
    const formData = new FormData();

    formData.append("file", this.addDocumentForm.controls['documentFile'].value);
    formData.append("zaak", this.mainZaakUrl);

    if (!this.updateDocument) {
      formData.append("informatieobjecttype", this.addDocumentForm.controls['documentType'].value);
    }

    if (this.activity) {
      formData.append("beschrijving", `Document voor activiteit '${this.activity}'`);
    }

    if (this.updateDocument) {
      formData.append("url", this.documentUrl);
      formData.append("reden", this.addDocumentForm.controls['reason'].value);
    }

    this.isSubmitting = true;

    if (!this.updateDocument) {
      this.documentService.postDocument(formData, this.bronorganisatie, this.identificatie).subscribe(res => {
        this.closeAndResetForm();
        this.uploadedDocument.emit(res)
        this.isSubmitting = false;
      }, errorRes => {
        this.reportError(errorRes);
      })
    } else if (this.updateDocument) {
      this.documentService.patchDocument(formData, this.bronorganisatie, this.identificatie).subscribe(() => {
        this.closeAndResetForm()
        this.isSubmitting = false;
      }, errorRes => {
        this.reportError(errorRes);
      })
    }
  }

  /**
   * Closes modals and resets the forms
   */
  closeAndResetForm() {
    this.fileUploadComponent.resetFileInput();
    this.reload.emit(true);
    this.closeModal.emit(true);
    if (!this.activity) {
      this.modalService.close("document-toevoegen-modal");
      this.modalService.close("document-overschrijven-modal");
    }
    this.addDocumentForm.reset();
  }

  //
  // Events.
  //

  /**
   * Add selected file to the form.
   * @param {File} file
   * @returns {Promise<void>}
   */
  async handleFileSelect(file: File) {
    this.addDocumentForm.controls['documentFile'].setValue(file);
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const errorMessage = error.error?.name[0] || 'Er is een fout opgetreden';
    this.snackbarService.openSnackBar(errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }

}
