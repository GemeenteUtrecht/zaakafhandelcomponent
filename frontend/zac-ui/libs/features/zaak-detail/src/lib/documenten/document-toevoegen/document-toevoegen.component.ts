import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { FileUploadComponent, ModalService } from '@gu/components';
import { Document } from '@gu/models';

@Component({
  selector: 'gu-document-toevoegen',
  templateUrl: './document-toevoegen.component.html',
  styleUrls: ['./document-toevoegen.component.scss']
})
export class DocumentToevoegenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() activity: string;
  @Input() documentUrl?: string;
  @Input() updateDocument: boolean;
  @Input() closeButton: boolean;
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
    private fb: FormBuilder,
    private modalService: ModalService
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
      this.getDocumentTypes().subscribe( res => {
        this.documentTypes = res;
      })
    }
  }

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
      this.postDocument(formData).subscribe(res => {
        this.closeAndResetForm();
        this.uploadedDocument.emit(res)
        this.isSubmitting = false;
      }, errorRes => {
        console.log(errorRes);
      })
    } else if (this.updateDocument) {
      this.patchDocument(formData).subscribe(() => {
        this.closeAndResetForm()
        this.isSubmitting = false;
      }, errorRes => {
        console.log(errorRes);
      })
    }
  }

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
    return this.http.Post<any>(encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/document`), formData);
  }

  patchDocument(formData: FormData): Observable<any> {
    return this.http.Patch<any>(encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/document`), formData);
  }

  async handleFileSelect(file: File) {
    this.addDocumentForm.controls['documentFile'].setValue(file);
  }

}
