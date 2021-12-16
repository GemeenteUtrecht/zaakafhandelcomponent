import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import {FormBuilder, FormControl, FormGroup, Validators} from '@angular/forms';
import {DocumentenService} from '../documenten.service';
import {Document} from '@gu/models';
import {MetaService} from '@gu/services';
import {SnackbarService} from "@gu/components";

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

  readonly errorMessage = 'Er is een fout opgetreden.';

  isLoading: boolean;
  hasError: boolean;

  currentConfidentialityType: any;
  confidentialityData: any;
  confidentialityForm: FormGroup;

  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private documentenService: DocumentenService,
    private fb: FormBuilder,
    private metaService: MetaService,
    private snackbarService: SnackbarService,
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

  ngOnChanges(changes: SimpleChanges) {
    if (!this.confidentialityData) {
      this.fetchConfidentiality();
    } else if (this.confidentialityData && (changes.selectedDocument.previousValue !== this.selectedDocument)) {
      this.setConfidentialityType(this.selectedDocument.vertrouwelijkheidaanduiding);
    }
  }

  setConfidentialityType(value): void {
    this.currentConfidentialityType = this.confidentialityData.find(item =>
      item.label === value
    );
    this.confidentialityTypeControl.patchValue(value);
  }

  fetchConfidentiality() {
    this.hasError = false;
    this.metaService.listConfidentialityClassifications().subscribe(
      (data) => {
        this.confidentialityData = data;
        if (this.selectedDocument) {
          this.setConfidentialityType(this.selectedDocument.vertrouwelijkheidaanduiding);
        }
        this.isLoading = false;
      },
      this.reportError.bind(this)
    )
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
    formData.append('vertrouwelijkheidaanduiding', this.confidentialityTypeControl.value);
    formData.append('reden', this.reasonControl.value);
    formData.append('url', this.selectedDocument.url);
    formData.append('zaak', this.mainZaakUrl);

    this.documentenService.setConfidentiality(this.selectedDocument.url, this.confidentialityTypeControl.value, this.reasonControl.value, this.mainZaakUrl).subscribe(() => {
      this.setConfidentialityType(this.confidentialityTypeControl.value);
      this.confidentialityForm.reset();
      this.reload.emit(true);
      this.closeModal.emit(true);
      this.isSubmitting = false;
    }, this.reportError.bind(this))
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const submitErrorMessage = error?.error?.detail ? error.error.detail : this.errorMessage;
    this.snackbarService.openSnackBar(submitErrorMessage, 'Sluiten', 'warn');
    console.error(error);

    this.isLoading = false
    this.isSubmitting = false;
    this.submitHasError = true;
    this.submitErrorMessage = submitErrorMessage
  }
}
