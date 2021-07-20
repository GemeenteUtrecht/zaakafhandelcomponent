import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Result } from '../../models/zaaktype';
import { ZaaktypeEigenschap } from '../../models/zaaktype-eigenschappen';
import { FeaturesSearchService } from '../features-search.service';
import { Search } from '../../models/search';
import { Zaak, TableSort } from '@gu/models';
import { Router } from '@angular/router';

@Component({
  selector: 'gu-search-form',
  templateUrl: './search-form.component.html',
  styleUrls: ['./search-form.component.scss']
})
export class SearchFormComponent implements OnInit, OnChanges {
  @Input() sortData: TableSort;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();

  searchForm: FormGroup
  formData: Search;

  zaaktypenData: Result[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[] = [];

  selectedPropertyValue: ZaaktypeEigenschap;

  isLoading: boolean;
  isSubmitting: boolean;
  hasError: boolean;
  errorMessage: string;

  showQueryNameField: boolean;
  reportName: string;
  saveReportIsSuccess: boolean;

  constructor(
    private fb: FormBuilder,
    private searchService: FeaturesSearchService,
    private router: Router,
  ) { }

  ngOnInit(): void {
    this.searchForm = this.fb.group({
      zaaktype: [''],
      omschrijving: [''],
      eigenschapnaam: [''],
      eigenschapwaarde: [''],
      saveQuery: [''],
      queryName: ['']
    })
    this.fetchZaaktypen();
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.sortData.previousValue !== this.sortData ) {
      this.postSearchZaken(this.formData, this.sortData);
    }
  }

  fetchZaaktypen() {
    this.isLoading = true;
    this.hasError = false;
    this.searchService.getZaaktypen().subscribe(res => {
      this.isLoading = false;
      this.zaaktypenData = res.results;
    }, error => {
      this.isLoading = false;
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaaktypen."
    })
  }

  /**
   * Navigate to the detail view directly if a zaak is selected using zaak select.
   * @param {Object} zaak
   */
  onZaakSelect(zaak: {bronorganisatie: string, identificatie: string}) {
    this.router.navigate([zaak.bronorganisatie, zaak.identificatie]);
  }

  onZaaktypeSelect(zaaktype: Result) {
    if (zaaktype) {
      this.isLoading = true;
      this.hasError = false;

      const catalogus = zaaktype.catalogus;
      const omschrijving = zaaktype.omschrijving;

      this.searchService.getZaaktypeEigenschappen(catalogus, omschrijving).subscribe(res => {
        this.zaaktypeEigenschappenData = res;
        this.eigenschapnaam.patchValue(undefined);
        this.isLoading = false;
      }, error => {
        this.isLoading = false;
        this.hasError = true;
        this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaakeigenschappen."
      })
    } else {
      this.zaaktypeEigenschappenData = [];
    }
  }

  onPropertySelect(property: ZaaktypeEigenschap) {
    this.selectedPropertyValue = property;
  }

  onCheckboxChange() {
    this.saveQueryControl.updateValueAndValidity({ onlySelf: false, emitEvent: true });
    const sub = this.saveQueryControl.statusChanges.subscribe((res) => {
      if (this.saveQueryControl.value) {
        this.showQueryNameField = true;
        this.queryNameControl.setValidators([Validators.required])
      } else {
        this.showQueryNameField = false;
        this.queryNameControl.clearValidators();
      }
      sub.unsubscribe();
      this.queryNameControl.updateValueAndValidity();
    });
  }

  updateFormValidity() {
    this.saveQueryControl.updateValueAndValidity()
  }

  submitForm() {
    this.hasError = false;
    this.saveReportIsSuccess = false;

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
    this.formData = {
      ...zaaktype && {zaaktype: zaaktype},
      ...this.omschrijving.value && {omschrijving: this.omschrijving.value},
      ...(this.eigenschapnaam.value && this.eigenschapwaarde.value) && {eigenschappen: eigenschappen}
    }

    this.postSearchZaken(this.formData)

    console.log(this.saveQueryControl.value);
    if (this.saveQueryControl.value) {
      this.reportName = this.queryNameControl.value;
      this.postCreateReport(this.reportName, this.formData)
    }
  }

  postSearchZaken(formData: Search, sortData?: TableSort) {
    this.isSubmitting = true;
    this.searchService.postSearchZaken(formData, sortData).subscribe(res =>{
      this.loadResult.emit(res.results);
      this.isSubmitting = false;
    }, error => {
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het zoeken."
      this.isSubmitting = false;
    })
  }

  postCreateReport(name: string, query: Search) {
    const formData = {
      name: name,
      query: query
    }
    this.searchService.postCreateReport(formData).subscribe(
      () => {
        this.saveReportIsSuccess = true;
        this.saveQueryControl.patchValue(false);
        this.queryNameControl.patchValue('');
      },
      error => {
        console.error(error);
      }
    )
  }

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

  get saveQueryControl(): FormControl {
    return this.searchForm.get('saveQuery') as FormControl;
  };

  get queryNameControl(): FormControl {
    return this.searchForm.get('queryName') as FormControl;
  };
}
