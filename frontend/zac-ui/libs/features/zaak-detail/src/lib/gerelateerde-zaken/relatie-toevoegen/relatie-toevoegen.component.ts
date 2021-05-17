import { Component, Input, OnInit, Output, EventEmitter } from '@angular/core';
import { Observable } from 'rxjs';
import { HttpResponse } from '@angular/common/http';
import { ApplicationHttpClient } from '@gu/services';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { ModalService } from '@gu/components';

@Component({
  selector: 'gu-relatie-toevoegen',
  templateUrl: './relatie-toevoegen.component.html',
  styleUrls: ['./relatie-toevoegen.component.scss']
})
export class RelatieToevoegenComponent implements OnInit {

  @Input() mainZaakUrl: string;
  @Output() reload: EventEmitter<boolean> = new EventEmitter<boolean>();

  readonly AARD_RELATIES = [
    {
      value: 'vervolg',
      label: 'Vervolg'
    },
    {
      value: 'bijdrage',
      label: 'Bijdrage'
    },
    {
      value: 'onderwerp',
      label: 'Onderwerp'
    }
  ];

  zaken: any = []
  addRelationForm: FormGroup;

  isSubmitting: boolean;

  constructor(
    private http: ApplicationHttpClient,
    private fb: FormBuilder,
    private modalService: ModalService
  ) { }

  ngOnInit(): void {
    this.addRelationForm = this.fb.group({
      identificatie: this.fb.control("", Validators.required),
      aard_relaties: this.fb.control("", Validators.required),
    })
  }

  get identificatieControl(): FormControl {
    return this.addRelationForm.controls['identificatie'] as FormControl;
  }

  get aardRelatiesControl(): FormControl {
    return this.addRelationForm.controls['aard_relaties'] as FormControl;
  }

  handleSearch(searchValue) {
    if (searchValue) {
      this.getSearchZaken(searchValue.toUpperCase()).subscribe( res => {
        this.zaken = res;
      })
    }
  }

  getSearchZaken(searchValue): Observable<HttpResponse<any>> {
    const endpoint = encodeURI(`/api/search/zaken/autocomplete?identificatie=${searchValue}`);
    return this.http.Get<any>(endpoint);
  }

  submitForm(): void {
    let formData;

    formData = {
      main_zaak: this.mainZaakUrl,
      relation_zaak: this.addRelationForm.controls['identificatie'].value,
      aard_relatie: this.addRelationForm.controls['aard_relaties'].value
    }

    this.isSubmitting = true;
    this.postRelation(formData).subscribe(() => {
      this.reload.emit(true);
      this.modalService.close("gerelateerde-zaken-modal");
      this.addRelationForm.reset();
      this.isSubmitting = false;
    }, errorRes => {
      console.log(errorRes);
    })
  }

  postRelation(formData: any): Observable<any> {
    return this.http.Post<any>(encodeURI("/api/core/cases/related-case"), formData);
  }

}
