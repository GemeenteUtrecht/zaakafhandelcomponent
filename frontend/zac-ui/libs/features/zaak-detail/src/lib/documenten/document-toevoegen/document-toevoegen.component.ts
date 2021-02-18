import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-document-toevoegen',
  templateUrl: './document-toevoegen.component.html',
  styleUrls: ['./document-toevoegen.component.scss']
})
export class DocumentToevoegenComponent implements OnInit {
  @Input() mainZaakUrl: string;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

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

    this.isSubmitting = true;
    this.postDocument(formData).subscribe(() => {
      this.reload.emit(true);
      this.modalService.close("document-toevoegen-modal");
      this.addDocumentForm.reset();
      this.isSubmitting = false;
    }, errorRes => {
      console.log(errorRes);
    })
  }

  postDocument(formData: FormData): Observable<any> {
    return this.http.Post<any>(encodeURI("/api/core/cases/document"), formData);
  }

  async handleFileSelect(file: File) {
    this.addDocumentForm.controls['documentFile'].setValue(file);
  }

}
