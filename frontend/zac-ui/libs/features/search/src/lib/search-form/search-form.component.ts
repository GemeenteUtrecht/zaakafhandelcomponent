import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { Result } from '../../models/zaaktype';
import { ZaaktypeEigenschap } from '../../models/zaaktype-eigenschappen';
import { FeaturesSearchService } from '../features-search.service';
import { Search } from '../../models/search';
import { Zaak } from '@gu/models';
import { Router } from '@angular/router';

@Component({
  selector: 'gu-search-form',
  templateUrl: './search-form.component.html',
  styleUrls: ['./search-form.component.scss']
})
export class SearchFormComponent implements OnInit {
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();

  searchForm: FormGroup

  zaaktypenData: Result[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[] = [];

  selectedPropertyValue: ZaaktypeEigenschap;

  isLoading: boolean;
  isSubmitting: boolean;
  hasError: boolean;
  errorMessage: string;

  isNotLoggedIn: boolean;
  readonly NOT_LOGGED_IN_MESSAGE = "Authenticatiegegevens zijn niet opgegeven.";

  loginUrl: string;

  constructor(
    private fb: FormBuilder,
    private searchService: FeaturesSearchService,
    private router: Router
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

  setLoginUrl(): void {
    const currentPath = this.router.url;
    this.loginUrl = `/accounts/login/?next=/ui${currentPath}`;
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
      if (this.errorMessage === this.NOT_LOGGED_IN_MESSAGE) {
        this.setLoginUrl()
        this.isNotLoggedIn = true;
      } else {
        this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaaktypen."
      }
    })
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

  submitForm() {
    this.hasError = false;

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
      this.loadResult.emit(res);
      this.isSubmitting = false;
    }, error => {
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het zoeken."
      this.isSubmitting = false;
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
