import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApplicationHttpClient } from '@gu/services';
import { ModalService } from '@gu/components';
import { convertBlobToString } from '@gu/utils';
import { FileUpload } from '@gu/models';

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
  ) {
    this.addDocumentForm = this.fb.group({
      documentType: this.fb.control("", Validators.required),
      documentFile: this.fb.control("", Validators.required),
    })
  }

  ngOnInit() {
    this.fetchDocumentTypes()
  }

  fetchDocumentTypes() {
    this.isLoading = true;
    if (this.mainZaakUrl) {
      this.getDocumentTypes().subscribe( res => {
        console.log(res)
        this.documentTypes = res;
      })
    }
  }

  getDocumentTypes(): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/core/api/documents/get-informatieobjecttypen?zaak=${this.mainZaakUrl}`);
    return this.http.Get<any>(endpoint);
  }

  submitForm(): void {
    let formData;

    formData = {
      informatieobjecttype: this.addDocumentForm.controls['documentType'].value,
      file: this.addDocumentForm.controls['documentFile'].value,
      zaak: this.mainZaakUrl
    }

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

  postDocument(formData: any): Observable<any> {
    return this.http.Post<any>(encodeURI("/core/api/documents/upload"), formData);
  }

  async handleFileSelect(file: File) {
    console.log(file);
    const convertedFile = await convertBlobToString(file);
    this.addDocumentForm.controls['documentFile'].setValue(convertedFile);
  }

}
