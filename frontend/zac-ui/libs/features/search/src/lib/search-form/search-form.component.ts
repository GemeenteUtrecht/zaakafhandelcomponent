import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import {PageEvent} from '@angular/material/paginator';
import {SnackbarService} from '@gu/components';
import {Zaak, TableSort, ZaakObject} from '@gu/models';
import {SearchService} from '../search.service';
import {MapGeometry, MapMarker} from "../../../../../shared/ui/components/src/lib/components/map/map";
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { ZaakObjectSearchFormComponent } from './object-search-form/zaak-object-search-form.component';


/**
 * This component allows the user to search Zaken dynamically.
 * Selecting a zaaktype will show its corresponding properties,
 * which can be chosen to further refine the search query.
 *
 * The user can also save the given search input as a report by
 * selecting the checkbox and give te report a name.
 */
@Component({
  selector: 'gu-search-form',
  templateUrl: './search-form.component.html',
  styleUrls: ['./search-form.component.scss']
})
export class SearchFormComponent {
  @ViewChild(ZaakObjectSearchFormComponent) zaakObjectSearchFormComponent: ZaakObjectSearchFormComponent;
  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar zaken.'

  @Input() sortData: TableSort;

  @Input() pageData: PageEvent;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();
  @Output() resultLength: EventEmitter<number> = new EventEmitter<number>();
  @Output() showResults: EventEmitter<boolean> = new EventEmitter<boolean>();

  @Output() mapGeometry: EventEmitter<MapGeometry> = new EventEmitter<MapGeometry>();
  @Output() mapMarkers: EventEmitter<MapMarker[]> = new EventEmitter<MapMarker[]>();

  isLoading: boolean;

  /** Tabs */
  tabs: object[] = [
    {
      link: '/zoeken/zaak',
      title: 'Zoeken op zaak'
    },
    {
      link: '/zoeken/object',
      title: 'Zoeken op object'
    }
  ]

  /** Active tab */
  activatedChildRoute: string;

  constructor(
    private location: Location,
    private route: ActivatedRoute,
    private searchService: SearchService,
    private snackbarService: SnackbarService) {
    route.url.subscribe(() => {
      this.activatedChildRoute = route.snapshot.url[0].path;
    });
  }

  //
  // Events.
  //

  /**
   * Resets results.
   */
  resetResults() {
    this.loadResult.emit([]);
    this.resultLength.emit(0);
    this.showResults.emit(false);
  }

  /**
   * Gets called when a ZaakObject is selected.
   * @param {ZaakObject} zaakObject
   */
  selectZaakObject(zaakObject: ZaakObject) {
    const page = (this.pageData?.pageIndex || 0) + 1
    const search = {
      object: zaakObject.url
    }

    this.isLoading = true;
    this.searchService.searchZaken(search, page).subscribe(
      (data) => {
        this.isLoading = false;
        this.loadResult.emit(data.results as Zaak[]);
        this.resultLength.emit(data.count);
        this.showResults.emit(true);
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Handle tab click
   * @param event
   * @param tab
   * @returns {string}
   */
  handleTabClick(event, tab) {
    event.preventDefault();
    this.setUrl(tab.link);
    this.activatedChildRoute = tab.link.split('/')[2];
    this.resetResults();
    this.zaakObjectSearchFormComponent.resetForm();
  }

  /**
   * Redirect to url
   * @param url
   */
  setUrl(url) {
    this.location.go(url)
  }

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
