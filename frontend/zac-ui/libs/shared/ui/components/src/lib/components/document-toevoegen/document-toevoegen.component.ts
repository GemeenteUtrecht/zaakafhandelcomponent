import {HttpResponse} from '@angular/common/http';
import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { FileUploadComponent, ModalService, SnackbarService } from '@gu/components';
import { Document, InformatieObjectType, Zaak } from '@gu/models';
import {ApplicationHttpClient, DocumentenService} from "@gu/services";
import {CachedObservableMethod} from '@gu/utils';


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
  @Input() zaak: Zaak;

  @Input() activity: string;
  @Input() documentUrl?: string;
  @Input() updateDocument: boolean;
  @Input() buttonSize: 'extrasmall' | 'small' | 'medium' | 'large' | 'huge' = 'large'

  @Input() title = 'Informatieobjecttype';
  @Input() description = 'Kies een relevante informatieobjecttype. Je ziet de informatieobjecttypen die bij het zaaktype horen';
  @Input() submitLabel = 'Opslaan';

  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeForm: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() uploadedDocument: EventEmitter<Document> = new EventEmitter<Document>();
  @Output() selectDocument: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() removeDocument: EventEmitter<boolean> = new EventEmitter<boolean>();

  @ViewChild(FileUploadComponent) private fileUploadComponent: FileUploadComponent

  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van documenten.';

  documentTypes: InformatieObjectType[];
  addDocumentForm: UntypedFormGroup;
  isLoading: boolean;
  isSubmitting: boolean;

  constructor(
    private documentService: DocumentenService,
    private fb: UntypedFormBuilder,
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

  get documentTypeControl(): UntypedFormControl {
    return this.addDocumentForm.controls['documentType'] as UntypedFormControl;
  }

  get reasonControl(): UntypedFormControl {
    return this.addDocumentForm.controls['reason'] as UntypedFormControl;
  }

  fetchDocumentTypes() {
    this.isLoading = true;
    if (this.zaak.url) {
      this.documentService.getDocumentTypes(this.zaak.url).subscribe( res => {
        // Sort and set values
        this.documentTypes = res.sort((a,b) => (a.omschrijving > b.omschrijving) ? 1 : ((b.omschrijving > a.omschrijving) ? -1 : 0));
      })
    }
  }

  @CachedObservableMethod('DocumentToevoegenComponent.getDocumentTypes')
  getDocumentTypes(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/core/informatieobjecttypen?zaak=${this.zaak.url}`);
    return this.http.Get<any>(endpoint);
  }

  submitForm(): void {
    const formData = new FormData();

    formData.append("file", this.addDocumentForm.controls['documentFile'].value);
    formData.append("zaak", this.zaak.url);

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
    let f = file;
    if (f.type === '' && f.name.endsWith('.msg')) {
      f = new File([f], f.name, { type: 'application/vnd.ms-outlook' });
    }
    this.addDocumentForm.controls['documentFile'].setValue(f);
    if (file) {
      this.selectDocument.emit(true)
      if (!this.documentTypeControl.value) {
        this.documentTypeControl.setErrors({'invalid': true})
        this.documentTypeControl.markAsTouched();
      } else {
        this.documentTypeControl.clearValidators();
      }
    } else {
      this.removeDocument.emit(true);
    }
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    let message = error?.error?.detail || error?.error.nonFieldErrors?.join(', ') || this.errorMessage;
    message = error?.error?.file ? error?.error?.file[0] : message;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    console.error(error);
    this.isSubmitting = false;
    this.isLoading = false;
  }
}
