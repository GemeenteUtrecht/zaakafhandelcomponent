import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {
  Zaak,
  TableSort,
  ZaaktypeEigenschap,
  MetaZaaktypeResult,
  UserSearchResult
} from '@gu/models';
import { Search } from '../../../models/search';
import { SearchService } from '../../search.service';
import {tableHeadMapping} from "../../search-results/constants/table";
import { PageEvent } from '@angular/material/paginator';
import { AccountsService, MetaService } from '@gu/services';
import { Choice } from '@gu/components';


/**
 * This component allows the user to search Zaken dynamically by property.
 * Selecting a zaaktype will show its corresponding properties,
 * which can be choosed to further refine the search query.
 *
 * The user can also save the given search input as a report by
 * selecting the checkbox and give te report a name.
 */
@Component({
  selector: 'gu-property-search-form',
  templateUrl: './property-search-form.component.html',
  styleUrls: ['./property-search-form.component.scss'],
})
export class PropertySearchFormComponent implements OnInit, OnChanges {
  @Input() sortData: TableSort;
  @Input() pageData: PageEvent;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();
  @Output() resultLength: EventEmitter<number> = new EventEmitter<number>();
  @Output() showResults: EventEmitter<boolean> = new EventEmitter<boolean>();
  @Output() isLoadingResult: EventEmitter<boolean> = new EventEmitter<boolean>();

  searchForm: UntypedFormGroup
  search: Search;

  users: UserSearchResult[] = [];

  caseTypes: MetaZaaktypeResult[];
  domainChoices: Choice[];
  caseTypeChoices: Choice[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[] = [];

  selectedPropertyValue: ZaaktypeEigenschap;

  isLoading: boolean;
  isSubmitting: boolean;
  hasError: boolean;
  errorMessage: string;

  showReportNameField: boolean;
  reportName: string;
  saveReportIsSuccess: boolean;

  page = 1;

  constructor(
    private fb: UntypedFormBuilder,
    private accountsService: AccountsService,
    private searchService: SearchService,
    private metaService: MetaService,
    private router: Router,
    private datePipe: DatePipe,
    private ngZone: NgZone,
    private cdRef: ChangeDetectorRef,
  ) { }

  ngOnInit(): void {
    this.searchForm = this.fb.group({
      domain: [{label: 'UTRE', value: 'UTRE'}],
      zaaktype: [''],
      behandelaar: [''],
      omschrijving: [''],
      eigenschapnaam: [''],
      eigenschapwaarde: [''],
      saveReport: [''],
      queryName: [''],
      includeClosed: false,
    })
    this.fetchZaaktypen();
  }

  ngOnChanges(changes: SimpleChanges) {
    const pageHasChanged = changes.pageData?.previousValue !== this.pageData;
    const sortHasChanged = changes.sortData?.previousValue !== this.pageData;
    if (sortHasChanged || pageHasChanged) {
      this.page = (this.pageData?.pageIndex || 0) + 1;
      this.postSearchZaken(this.search, this.page, this.sortData);
    }
  }

  /**
   * Returns choices for case types.
   * @return {Choice[]}
   */
  getDomainChoices(): Choice[] {
    return [...new Set(this.caseTypes.map((caseType: MetaZaaktypeResult) => caseType.catalogus.domein))]
      .map((domain) => ({label: domain, value: domain}))
  }

  /**
   * Fetch all the different zaak types.
   * @param {string} [domain]
   */
  fetchZaaktypen(domain: string=this.domain.value?.value): void {
    this.isLoading = true;
    this.hasError = false;

    // Check if domain should be applied.
    const observable = (domain)
      ? this.metaService.getCaseTypesForDomain(domain)
      : this.metaService.getCaseTypes()

    observable.subscribe(res => {
      this.caseTypes = res.results;
      this.caseTypeChoices = this.caseTypes.map( type => {
        return {
          label: type.omschrijving,
          value: type,
        }
      })
      this.isLoading = false;
      this.cdRef.detectChanges();

      // Only update choices when all case types are loaded.
      if(!domain) {
        this.domainChoices = this.getDomainChoices();
      }
    }, error => {
      this.isLoading = false;
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaaktypen."
    })
  }

  /**
   * Gets called when domain is selected.
   */
  onDomainSelect(event) {
    this.caseTypes = [];
    this.fetchZaaktypen(event?.value);
  }

  /**
   * Fetch the properties of a case type based on the selection.
   * @param {MetaZaaktypeResult} zaaktype
   */
  onZaaktypeSelect(zaaktype) {
    if (zaaktype) {
      this.isLoading = true;
      this.hasError = false;

      const catalogus = zaaktype.value.catalogus.url;
      const identificatie = zaaktype.value.identificatie;

      this.metaService.getZaaktypeEigenschappenByCatalogus(catalogus, identificatie).subscribe(res => {
        this.zaaktypeEigenschappenData = res;
        this.eigenschapnaam.patchValue(undefined);
        this.isLoading = false;
        this.cdRef.detectChanges();
      }, error => {
        this.isLoading = false;
        this.hasError = true;
        this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaakeigenschappen."
      })
    } else {
      this.zaaktypeEigenschappenData = [];
    }
  }


  /**
   * Search users.
   * @param searchInput
   */
  onSearch(searchInput) {
    this.accountsService.getAccounts(searchInput).subscribe(res => {
        this.users = res.results;
      }
    );
  }

  /**
   * Set the selected property value
   * @param {ZaaktypeEigenschap} property
   */
  onPropertySelect(property: ZaaktypeEigenschap) {
    this.selectedPropertyValue = property;
  }

  /**
   * Show input for report name and set it as required for the form.
   */
  onSaveReportChange() {
    this.saveReportControl.updateValueAndValidity({ onlySelf: false, emitEvent: true });
    if (this.saveReportControl.value) {
      this.showReportNameField = true;
      this.queryNameControl.setValidators([Validators.required])
    } else {
      this.showReportNameField = false;
      this.queryNameControl.clearValidators();
    }
    this.queryNameControl.updateValueAndValidity();
  }

  /**
   * Create form data.
   */
  submitForm() {
    this.hasError = false;
    this.saveReportIsSuccess = false;

    // Check if zaaktype has been filled in
    let zaaktype;

    if (this.zaaktype.value) {
      zaaktype = {
        omschrijving: this.zaaktype.value.omschrijving,
        catalogus: this.zaaktype.value.catalogus.url
      }
    }

    // Create object for eigenschappen
    const eigenschapValue =
      this.selectedPropertyValue?.spec.format === 'date' ?
        this.datePipe.transform(this.eigenschapwaarde.value, "yyyy-MM-dd") :
        this.eigenschapwaarde.value;

    const eigenschappen = {
      [this.eigenschapnaam.value]: {
        value: eigenschapValue
      }
    }

    // Only add key with values if the values are present
    this.search = {
      ...zaaktype && {zaaktype: zaaktype},
      ...this.behandelaar.value && {behandelaar: this.behandelaar.value},
      ...this.omschrijving.value && {omschrijving: this.omschrijving.value},
      ...(this.eigenschapnaam.value && this.eigenschapwaarde.value) && {eigenschappen: eigenschappen}
    }

    this.postSearchZaken(this.search, this.page)

    // Check if the user wants to save the search query as a report
    if (this.saveReportControl.value) {
      this.reportName = this.queryNameControl.value;
      this.postCreateReport(this.reportName, this.search)
    }
  }

  /**
   * POST search query.
   * @param {Search} formData
   * @param {Number} page
   * @param {TableSort} sortData
   */
  postSearchZaken(formData: Search, page, sortData?: TableSort) {
    this.isSubmitting = true;
    this.isLoadingResult.emit(true);

    const orderingDirection = sortData?.order === 'desc' ? '-' : '';
    const orderingParam = sortData ? tableHeadMapping[sortData.value] : '';
    const ordering = sortData ? `${orderingDirection}${orderingParam}` : null;

    const search = {...formData, includeClosed: this.includeClosedControl.value}

    this.searchService.searchZaken(search, page, ordering).subscribe(res =>{
      this.loadResult.emit(res.results);
      this.resultLength.emit(res.count);
      this.showResults.emit(true);
      this.isSubmitting = false;
      this.isLoadingResult.emit(false);
    }, error => {
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het zoeken."
      this.isSubmitting = false;
      this.isLoadingResult.emit(false);
    })
  }

  /**
   * Save the current search query as a Report.
   * @param {string} name
   * @param {Search} query
   */
  postCreateReport(name: string, query: Search) {
    const formData = {
      name: name,
      query: query
    }
    this.searchService.postCreateReport(formData).subscribe(
      () => {
        this.saveReportIsSuccess = true;
        this.saveReportControl.patchValue(false);
        this.queryNameControl.patchValue('');
      },
      error => {
        console.error(error);
      }
    )
  }

  get domain(): UntypedFormControl {
    return this.searchForm.get('domain') as UntypedFormControl;
  };

  get zaaktype(): UntypedFormControl {
    return this.searchForm.get('zaaktype') as UntypedFormControl;
  };

  get behandelaar(): UntypedFormControl {
    return this.searchForm.get('behandelaar') as UntypedFormControl;
  };

  get omschrijving(): UntypedFormControl {
    return this.searchForm.get('omschrijving') as UntypedFormControl;
  };

  get eigenschapnaam(): UntypedFormControl {
    return this.searchForm.get('eigenschapnaam') as UntypedFormControl;
  };

  get eigenschapwaarde(): UntypedFormControl {
    return this.searchForm.get('eigenschapwaarde') as UntypedFormControl;
  };

  get saveReportControl(): UntypedFormControl {
    return this.searchForm.get('saveReport') as UntypedFormControl;
  };

  get queryNameControl(): UntypedFormControl {
    return this.searchForm.get('queryName') as UntypedFormControl;
  };

  get includeClosedControl(): UntypedFormControl {
    return this.searchForm.get('includeClosed') as UntypedFormControl;
  };
}
