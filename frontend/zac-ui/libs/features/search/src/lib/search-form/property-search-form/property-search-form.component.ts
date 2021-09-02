import {DatePipe} from '@angular/common';
import {Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges} from '@angular/core';
import {FormBuilder, FormControl, FormGroup, Validators} from '@angular/forms';
import {Router} from '@angular/router';
import {PageEvent} from '@angular/material/paginator';
import {SnackbarService} from '@gu/components';
import {Zaak, TableSort} from '@gu/models';
import {Search} from '../../../models/search';
import {Result} from '../../../models/zaaktype';
import {ZaaktypeEigenschap} from '../../../models/zaaktype-eigenschappen';
import {tableHeadMapping} from '../../search-results/constants/table';
import {SearchService} from '../../search.service';


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

  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken.'

  searchForm: FormGroup
  search: Search;

  zaaktypenData: Result[];
  zaaktypeEigenschappenData: ZaaktypeEigenschap[] = [];

  selectedPropertyValue: ZaaktypeEigenschap;

  isLoading: boolean;
  isSubmitting: boolean;
  showReportNameField: boolean;
  reportName: string;
  saveReportIsSuccess: boolean;

  page = 1;

  /**
   * Constructor method.
   * @param {DatePipe} datePipe
   * @param {FormBuilder} fb
   * @param {Router} router
   * @param {SearchService} searchService
   * @param {SnackbarService} snackbarService
   */
  constructor(
    private datePipe: DatePipe,
    private fb: FormBuilder,
    private router: Router,
    private searchService: SearchService,
    private snackbarService: SnackbarService,
  ) {
  }

  //
  // Getters / setters.
  //

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

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
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

  /**
   * A lifecycle hook that is called when any data-bound property of a directive changes. Define an ngOnChanges() method
   * to handle the changes.
   */
  ngOnChanges(changes: SimpleChanges) {
    const pageHasChanged = changes.pageData?.previousValue !== this.pageData;
    const sortHasChanged = changes.sortData?.previousValue !== this.pageData;
    if (sortHasChanged || pageHasChanged) {
      this.page = this.pageData.pageIndex + 1;
      this.postSearchZaken(this.search, this.page, this.sortData);
    }
  }

  //
  // Context.
  //

  /**
   * Fetch all the different zaak types.
   */
  fetchZaaktypen() {
    this.isLoading = true;

    this.searchService.getZaaktypen().subscribe(res => {
      this.isLoading = false;
      this.zaaktypenData = res.results;
    }, this.reportError.bind(this))
  }

  /**
   * POST search query.
   * @param {Search} formData
   * @param {Number} page
   * @param {TableSort} sortData
   */
  postSearchZaken(formData: Search, page, sortData?: TableSort) {
    this.isSubmitting = true;

    const orderingDirection = sortData?.order === 'desc' ? '-' : '';
    const orderingParam = sortData ? tableHeadMapping[sortData.value] : '';
    const ordering = sortData ? `${orderingDirection}${orderingParam}` : null;

    this.searchService.searchZaken(formData, page, ordering).subscribe(res => {
      this.loadResult.emit(res.results);
      this.resultLength.emit(res.count);
      this.isSubmitting = false;
    }, this.reportError.bind(this))
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

  //
  // Events.
  //

  /**
   * Fetch the properties of a case type based on the selection.
   * @param {Result[]} results
   */
  onZaaktypeSelect(results: Result[]) {
    if (!results?.length) {
      this.zaaktypeEigenschappenData = [];
      return;
    }

    this.isLoading = true;

    const catalogs = results.map((result: Result) => result.catalogus);
    const descriptions = results.map((result: Result) => result.omschrijving);

    this.searchService.getZaaktypeEigenschappen(catalogs, descriptions).subscribe(
      (res: ZaaktypeEigenschap[]) => {
        this.zaaktypeEigenschappenData = res;
        this.eigenschapnaam.patchValue(undefined);
        this.isLoading = false;
      },
      this.reportError.bind(this),
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
  onCheckboxChange() {
    this.saveReportControl.updateValueAndValidity({onlySelf: false, emitEvent: true});
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
    this.saveReportIsSuccess = false;

    // Check if zaaktype has been filled in
    let zaaktype;
    if (this.zaaktype.value) {
      this.zaaktypenData.forEach(zaaktypeElement => {
        if (zaaktypeElement.identificatie === this.zaaktype.value)
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

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.isLoading = false;
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
