import {
  ChangeDetectorRef,
  Component,
  ContentChild,
  OnInit,
  TemplateRef
} from '@angular/core';
import {ZaakService} from '@gu/services';
import {Zaak} from '@gu/models';
import {LandingService} from './landing.service';
import {LandingPage} from '../models/landing-page';
import {SnackbarService} from '@gu/components';
import { TitleCasePipe } from '@angular/common';
import { UntypedFormBuilder, UntypedFormControl, UntypedFormGroup } from '@angular/forms';
import { RecentlyViewed } from '../models/recently-viewed';
import { FeaturesWorkstackService } from '../../../workstack/src/lib/features-workstack.service';

/**
 * Landing page component.
 */
@Component({
  selector: 'gu-features-landing',
  templateUrl: './features-landing.component.html',
  styleUrls: ['./features-landing.component.scss']
})
export class FeaturesLandingComponent implements OnInit {
  @ContentChild(TemplateRef) template: TemplateRef<any> | undefined

  readonly errorMessage = 'Er is een fout opgetreden bij het laden van landingspagina.'

  /** @type {boolean} Whether the landing page is loading. */
  isLoading: boolean = true;

  notFoundText: string = 'Geen resultaten'

  /** @type {(LandingPage|null)} The landing page once retrieved. */
  landingPage: LandingPage | null = null;
  recentlyViewedCases: RecentlyViewed[] = [];
  activeCases: number = 0;

  searchResults: any = [];
  filteredResults: any = [];
  selectedFilter: 'Zaken' | 'Documenten' | 'Objecten' | 'all' = 'all';

  searchForm: UntypedFormGroup =  this.fb.group({
    query: this.fb.control(null),
  })

  /**
   * Constructor method.
   * @param {ChangeDetectorRef} cdRef
   * @param {FormBuilder} fb
   * @param {LandingService} landingService
   * @param {SnackbarService} snackbarService
   * @param {TitleCasePipe} titleCasePipe
   * @param {ZaakService} zaakService
   */
  constructor(
    private cdRef: ChangeDetectorRef,
    private fb: UntypedFormBuilder,
    private landingService: LandingService,
    private workstackService: FeaturesWorkstackService,
    private snackbarService: SnackbarService,
    private titleCasePipe: TitleCasePipe,
    private zaakService: ZaakService
  ) {
  }

  get queryControl(): UntypedFormControl {
    return this.searchForm.get('query') as UntypedFormControl;
  };

  //
  // Angular lifecycle.
  //

  ngOnInit() {
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Retrieves context
   */
  getContextData() {
    this.landingService.landingPageRetrieve().subscribe(
      (landingPage) => this.landingPage = landingPage,
      (error) => this.reportError(error),
      () => this.isLoading = false,
    )

    this.landingService.retrieveRecentlyViewedCases().subscribe(
      (recentlyViewedCases) => this.recentlyViewedCases = recentlyViewedCases.recentlyViewed,
      (error) => this.reportError(error),
      () => this.isLoading = false,
    )

    this.workstackService.getWorkstackSummary().subscribe(
      (res) => {
        this.activeCases = res?.userTasks;
      }
    );

  }

  /**
   * Formats API data to usable format for ng-select
   * @param res
   */
  formatSearchResForView(res: any) {
    this.searchResults = [];
    Object.keys(res).forEach((key, index) => {
      const results = res[key].map((v: any) => ({...v, disabled: true, typeIndex: key+index.toString(), type: this.titleCasePipe.transform(key)}))
      this.searchResults = this.searchResults.concat(results)
    });
    this.onFilterResults();
  }

  //
  // Events.
  //

  /**
   * Gets called when zaak (case) is selected.
   * @param {Zaak} zaak
   */
  onZaakSelectChange(zaak: Zaak) {
    this.zaakService.navigateToCase(zaak);
  }

  /**
   * Filters displayed results according to the selected filter toggle button
   */
  onFilterResults() {
    if (this.selectedFilter !== 'all') {
      this.filteredResults = this.searchResults.filter((res: { type: string; }) => {
        return res.type === this.selectedFilter
      })
    } else {
      this.filteredResults = this.searchResults;
    }
  }

  /**
   * On user search
   * @param value
   */
  onSearch(value: any) {
    if (value.term.length > 0) {
      this.landingService.quickSearch(value.term).subscribe(res => {
        this.formatSearchResForView(res)
      })
    }
    this.notFoundText = value.term.length > 2 ? 'Geen resultaten' : 'Voer minimaal 3 tekens in om te zoeken';
  }

  /**
   * @param term
   * @param item
   * @returns {any}
   */
  searchFunction(term: any, item: any) {
    return item
  }

  /**
   * Create url
   * @param item
   * @returns {string}
   */
  createRouteLink(item: any): string {
    return `/zaken/${item.bronorganisatie}/${item.identificatie}`
  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    const message = error.error?.value?.[0] || error.error?.detail || this.errorMessage;
    this.snackbarService.openSnackBar(message, 'Sluiten', 'warn');
    this.isLoading = false;
    console.error(error);
  }
}
