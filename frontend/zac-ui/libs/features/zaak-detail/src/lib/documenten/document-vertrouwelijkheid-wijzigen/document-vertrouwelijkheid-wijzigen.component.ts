import { Component, EventEmitter, Input, OnChanges, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { DocumentenService } from '../documenten.service';
import { Document } from '@gu/models';
import {ZaakService} from "@gu/services";

@Component({
  selector: 'gu-document-vertrouwelijkheid-wijzigen',
  templateUrl: './document-vertrouwelijkheid-wijzigen.component.html',
  styleUrls: ['./document-vertrouwelijkheid-wijzigen.component.scss']
})
export class DocumentVertrouwelijkheidWijzigenComponent implements OnInit, OnChanges {
  @Input() mainZaakUrl: string;
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() selectedDocument: Document;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() closeModal: EventEmitter<boolean> = new EventEmitter<boolean>();

  isLoading: boolean;
  hasError: boolean;
  errorMessage: string;

  currentConfidentialityType: any;
  confidentialityData: any;
  confidentialityForm: FormGroup;

  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private documentenService: DocumentenService,
    private fb: FormBuilder,
    private zaakService: ZaakService,
  ) {
    this.confidentialityForm = this.fb.group({
      confidentialityType: this.fb.control("", Validators.required),
      reason: this.fb.control("", Validators.required)
    })
  }

  ngOnInit() {
    if (this.selectedDocument) {
      this.fetchConfidentiality();
    }
  }

  ngOnChanges() {
    if (!this.confidentialityData) {
      this.fetchConfidentiality();
    } else if (this.confidentialityData && this.selectedDocument) {
      this.setConfidentialityType(this.selectedDocument.vertrouwelijkheidaanduiding);
    }
  }

  setConfidentialityType(value): void {
    this.currentConfidentialityType = this.confidentialityData.find( item =>
      item.label === value
    )
  }

  fetchConfidentiality() {
    this.hasError = false;
    this.documentenService.getConfidentiality().subscribe(data => {
      this.confidentialityData = data;
      if (this.selectedDocument) {
        this.setConfidentialityType(this.selectedDocument.vertrouwelijkheidaanduiding);
      }
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.hasError = true;
      this.errorMessage = error?.error?.detail ? error.error.detail : 'Vertrouwelijkheidaanduidingen konden niet worden opgehaald.';
      this.isLoading = false;
    })
  }

  get confidentialityTypeControl(): FormControl {
    return this.confidentialityForm.controls['confidentialityType'] as FormControl;
  }

  get reasonControl(): FormControl {
    return this.confidentialityForm.controls['reason'] as FormControl;
  }

  submitConfidentiality() {
    this.isSubmitting = true;
    const formData = new FormData();
    formData.append('vertrouwelijkheidaanduiding',  this.confidentialityTypeControl.value);
    formData.append('reden',  this.reasonControl.value);
    formData.append('url', this.selectedDocument.url);
    formData.append('zaak',  this.mainZaakUrl);

    this.zaakService.updateCaseDetails(this.bronorganisatie, this.identificatie, formData).subscribe( () => {
      this.setConfidentialityType(this.confidentialityTypeControl.value);
      this.confidentialityForm.reset();
      this.reload.emit(true);
      this.closeModal.emit(true);
      this.isSubmitting = false;
    }, error => {
      this.submitHasError = true;
      this.submitErrorMessage = error?.error?.detail ? error.error.detail : 'Er is een fout opgetreden';
      this.isSubmitting = false;
    })
  }
}
