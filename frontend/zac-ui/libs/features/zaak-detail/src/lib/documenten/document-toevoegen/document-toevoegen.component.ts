import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FileUploadComponent, ModalService, SnackbarService } from '@gu/components';
import { Document } from '@gu/models';
import { DocumentenService } from '../documenten.service';

import {CachedObservableMethod} from '@gu/utils';
import { Observable } from 'rxjs';
import {HttpResponse} from "@angular/common/http";
import {ApplicationHttpClient} from "@gu/services";

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
  @Output() closeForm: EventEmitter<boolean> = new EventEmitter<boolean>();

  @ViewChild(FileUploadComponent) private fileUploadComponent: FileUploadComponent

  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van documenten.';

  documentTypes: any;
  addDocumentForm: FormGroup;
  isLoading: boolean;
  isSubmitting: boolean;

  constructor(
    private documentService: DocumentenService,
    private fb: FormBuilder,
    private http: ApplicationHttpClient,
    private modalService: ModalService,
    private snackbarService: SnackbarService,
  ) { }

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

  get documentTypeControl(): FormControl {
    return this.addDocumentForm.controls['documentType'] as FormControl;
  }

  get reasonControl(): FormControl {
    return this.addDocumentForm.controls['reason'] as FormControl;
  }

  fetchDocumentTypes() {
    this.isLoading = true;
    if (this.mainZaakUrl) {
      this.documentService.getDocumentTypes(this.mainZaakUrl).subscribe( res => {
        this.documentTypes = res;
      })
    }
  }

  @CachedObservableMethod('DocumentToevoegenComponent.getDocumentTypes')
  getDocumentTypes(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/document-types?zaak=${this.mainZaakUrl}`);
    return this.http.Get<any>(endpoint);
  }

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
      this.documentService.postDocument(formData).subscribe(res => {
        this.closeAndResetForm();
        this.uploadedDocument.emit(res)
        this.isSubmitting = false;
      }, errorRes => {
        this.reportError(errorRes);
      })
    } else if (this.updateDocument) {
      this.documentService.patchDocument(formData).subscribe(() => {
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

  postDocument(formData: FormData): Observable<Document> {
    return this.http.Post<any>(encodeURI('/api/core/cases/document'), formData);
  }

  patchDocument(formData: FormData): Observable<any> {
    return this.http.Patch<any>(encodeURI('/api/core/cases/document'), formData);
  }

  async handleFileSelect(file: File) {
    this.addDocumentForm.controls['documentFile'].setValue(file);
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
