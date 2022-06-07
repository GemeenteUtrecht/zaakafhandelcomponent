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
import { FormBuilder, FormControl, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import {Zaak, TableSort, ZaaktypeEigenschap} from '@gu/models';
import { Search } from '../../../models/search';
import { Result } from '../../../models/zaaktype';
import { SearchService } from '../../search.service';
import {tableHeadMapping} from "../../search-results/constants/table";
import { PageEvent } from '@angular/material/paginator';
import { MetaService } from '@gu/services';


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
})
export class PropertySearchFormComponent implements OnInit, OnChanges {
  @Input() sortData: TableSort;
  @Input() pageData: PageEvent;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();
  @Output() resultLength: EventEmitter<number> = new EventEmitter<number>();
  @Output() isLoadingResult: EventEmitter<boolean> = new EventEmitter<boolean>();

  searchForm: FormGroup
  search: Search;

  zaaktypenData: Result[];
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
    private fb: FormBuilder,
    private searchService: SearchService,
    private metaService: MetaService,
    private router: Router,
    private datePipe: DatePipe,
    private ngZone: NgZone,
    private cdRef: ChangeDetectorRef,
  ) { }

  ngOnInit(): void {
    this.searchForm = this.fb.group({
      zaaktype: [''],
      omschrijving: [''],
      eigenschapnaam: [''],
      eigenschapwaarde: [''],
      saveReport: [''],
      queryName: ['']
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
   * Fetch all the different zaak types.
   */
  fetchZaaktypen() {
    this.isLoading = true;
    this.hasError = false;
    this.searchService.getZaaktypen().subscribe(res => {
      this.zaaktypenData = res.results;
      this.isLoading = false;
      this.cdRef.detectChanges();
    }, error => {
      this.isLoading = false;
      this.hasError = true;
      this.errorMessage = error.error.detail ? error.error.detail : "Er is een fout opgetreden bij het ophalen van zaaktypen."
    })
  }

  /**
   * Fetch the properties of a case type based on the selection.
   * @param {Result} zaaktype
   */
  onZaaktypeSelect(zaaktype: Result) {
    if (zaaktype) {
      this.isLoading = true;
      this.hasError = false;

      const catalogus = zaaktype.catalogus;
      const omschrijving = zaaktype.omschrijving;

      this.metaService.getZaaktypeEigenschappenByCatalogus(catalogus, omschrijving).subscribe(res => {
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
   * Set the selected property value
   * @param {ZaaktypeEigenschap} property
   */
  onPropertySelect(property: ZaaktypeEigenschap) {
    this.selectedPropertyValue = property;
  }


  /**
   * Show input for report name and set it as required for the form.
   */
  onCheckboxChange() {
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
      this.zaaktypenData.forEach( zaaktypeElement => {
        if (zaaktypeElement.omschrijving === this.zaaktype.value)
          zaaktype = {
            omschrijving: zaaktypeElement.omschrijving,
            catalogus: zaaktypeElement.catalogus
          }
      });
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

    this.searchService.searchZaken(formData, page, ordering).subscribe(res =>{
      this.loadResult.emit(res.results);
      this.resultLength.emit(res.count);
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

  get saveReportControl(): FormControl {
    return this.searchForm.get('saveReport') as FormControl;
  };

  get queryNameControl(): FormControl {
    return this.searchForm.get('queryName') as FormControl;
  };
}
