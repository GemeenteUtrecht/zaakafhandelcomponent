import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { FeaturesSearchService } from './features-search.service';
import { Result} from '../models/zaaktype';
import { ZaaktypeEigenschap } from '../models/zaaktype-eigenschappen';
import { Search } from '../models/search';

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss']
})
export class FeaturesSearchComponent implements OnInit {

  searchForm: FormGroup

  zaaktypenData: Result[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[] = [];

  selectedPropertyValue: ZaaktypeEigenschap;

  isSubmitting: boolean;
  hasError: boolean;
  errorMessage: string;

  constructor(
    private fb: FormBuilder,
    private searchService: FeaturesSearchService
  ) { }

  ngOnInit(): void {
    this.searchForm = this.fb.group({
      identificatie: [''],
      zaaktype: [''],
      omschrijving: [''],
      eigenschapnaam: [''],
      eigenschapwaarde: ['']
    })
    this.fetchZaaktypen();
  }

  fetchZaaktypen() {
    this.searchService.getZaaktypen().subscribe(res => {
      console.log(res);
      this.zaaktypenData = res.results;
    })
  }

  onZaaktypeSelect(zaaktype: Result) {
    if (zaaktype) {
      const catalogus = zaaktype.catalogus;
      const omschrijving = zaaktype.omschrijving;

      this.searchService.getZaaktypeEigenschappen(catalogus, omschrijving).subscribe(res => {
        this.zaaktypeEigenschappenData = res;
        this.eigenschapnaam.patchValue(undefined);
      })
    } else {
      this.zaaktypeEigenschappenData = [];
    }
  }

  onPropertySelect(property: ZaaktypeEigenschap) {
    this.selectedPropertyValue = property;
  }

  submitForm() {
    let zaaktype;
    if (this.zaaktype.value) {
      this.zaaktypenData.forEach( zaaktypeElement => {
        if (zaaktypeElement.identificatie === this.zaaktype.value)
          zaaktype = {
            omschrijving: zaaktypeElement.omschrijving,
            catalogus: zaaktypeElement.catalogus
          }
      });
    }
    const eigenschappen = {
      [this.eigenschapnaam.value]: {
        value: this.eigenschapwaarde.value
      }
    }
    const formData: Search = {
      ...this.identificatie.value && {identificatie: this.identificatie.value},
      ...zaaktype && {zaaktype: zaaktype},
      ...this.omschrijving.value && {omschrijving: this.omschrijving.value},
      ...(this.eigenschapnaam.value && this.eigenschapwaarde.value) && {eigenschappen: eigenschappen}
    }

    this.postSearchZaken(formData)
  }

  postSearchZaken(formData: Search) {
    this.isSubmitting = true;
    this.searchService.postSearchZaken(formData).subscribe(res =>{
      console.log(res)
      this.isSubmitting = false;
    }, error => {
      this.errorMessage = error.detail ? error.detail : "Er is een fout opgetreden."
    })
  }

  get identificatie(): FormControl {
    return this.searchForm.get('identificatie') as FormControl;
  };

  get zaaktype(): FormControl {
    return this.searchForm.get('zaaktype') as FormControl;
  };


  get omschrijving(): FormControl {
    return this.searchForm.get('omschrijving') as FormControl;
  };

  get eigenschapnaam(): FormControl {
    return this.searchForm.get('eigenschapnaam') as FormControl;
  };

  get eigenschapwaarde(): FormControl {
    return this.searchForm.get('eigenschapwaarde') as FormControl;
  };
}
