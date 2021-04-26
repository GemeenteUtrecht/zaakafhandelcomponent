import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { ModalService } from '@gu/components';
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
  @Input() closeButton: boolean;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() close: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() uploadedDocument: EventEmitter<Document> = new EventEmitter<Document>();

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
      documentType: this.fb.control("", Validators.required),
      documentFile: this.fb.control("", Validators.required),
    })
    this.fetchDocumentTypes()
  }

  get documentTypeControl(): FormControl {
    return this.addDocumentForm.controls['documentType'] as FormControl;
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

    formData.append("informatieobjecttype", this.addDocumentForm.controls['documentType'].value);
    formData.append("file", this.addDocumentForm.controls['documentFile'].value);
    formData.append("zaak", this.mainZaakUrl);

    if (this.activity) {
      formData.append("beschrijving", `Document voor activiteit '${this.activity}'`);
    }

    this.isSubmitting = true;
    this.postDocument(formData).subscribe(res => {
      this.reload.emit(true);
      this.close.emit(true);
      if (!this.activity) {
        this.modalService.close("document-toevoegen-modal");
      }
      this.uploadedDocument.emit(res)
      this.addDocumentForm.reset();
      this.isSubmitting = false;
    }, errorRes => {
      console.log(errorRes);
    })
  }

  postDocument(formData: FormData): Observable<Document> {
    return this.http.Post<any>(encodeURI(`/api/core/cases/${this.bronorganisatie}/${this.identificatie}/document`), formData);
  }

  async handleFileSelect(file: File) {
    this.addDocumentForm.controls['documentFile'].setValue(file);
  }

}
