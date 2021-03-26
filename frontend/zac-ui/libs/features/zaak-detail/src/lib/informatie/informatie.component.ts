import { Component, Input, OnInit, OnChanges } from '@angular/core';
import { InformatieService } from './informatie.service';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Zaak } from '@gu/models';

@Component({
  selector: 'gu-informatie',
  templateUrl: './informatie.component.html',
  styleUrls: ['./informatie.component.scss']
})
export class InformatieComponent implements OnInit, OnChanges {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;
  @Input() zaakData: Zaak;

  propertiesData: any;
  isLoading: boolean;
  confidentialityData: any = [];

  currentConfidentialityType: any;
  confInEditMode = false;
  confidentialityForm: FormGroup;

  isSubmitting: boolean;
  submitHasError: boolean;
  submitErrorMessage: string;

  constructor(
    private informatieService: InformatieService,
    private fb: FormBuilder
  ) {
    this.confidentialityForm = this.fb.group({
      confidentialityType: this.fb.control("", Validators.required),
      reason: this.fb.control("", Validators.required),
    })
  }

  ngOnInit() {
    this.fetchConfidentiality();
  }

  ngOnChanges(): void {
    this.fetchProperties();
  }

  setConfidentialityType(value): void {
    this.currentConfidentialityType = this.confidentialityData.find( item =>
      item.value === value
    )
  }

  get confidentialityTypeControl(): FormControl {
    return this.confidentialityForm.controls['confidentialityType'] as FormControl;
  }

  get reasonControl(): FormControl {
    return this.confidentialityForm.controls['reason'] as FormControl;
  }

  fetchConfidentiality() {
    this.informatieService.getConfidentiality().subscribe(data => {
      this.confidentialityData = data;
      this.setConfidentialityType(this.zaakData.vertrouwelijkheidaanduiding);
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  fetchProperties() {
    this.isLoading = true;
    this.informatieService.getProperties(this.bronorganisatie, this.identificatie).subscribe(data => {
      this.propertiesData = data;
      this.isLoading = false;
    }, error => {
      console.log(error);
      this.isLoading = false;
    })
  }

  submitConfidentiality() {
    this.isSubmitting = true;
    const formData = {
      vertrouwelijkheidaanduiding: this.confidentialityTypeControl.value,
      reden: this.reasonControl.value
    }
    this.informatieService.patchConfidentiality(this.bronorganisatie, this.identificatie, formData).subscribe( () => {
      this.setConfidentialityType(this.confidentialityTypeControl.value);
      this.confInEditMode = false;
      this.isSubmitting = false;
    }, error => {
      this.submitHasError = true;
      this.submitErrorMessage = error?.error?.detail ? error.error.detail : 'Er is een fout opgetreden';
      this.isSubmitting = false;
    })
  }
}
