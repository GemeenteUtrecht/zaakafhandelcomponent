import {Component, EventEmitter, Input, Output} from '@angular/core';
import {PageEvent} from '@angular/material/paginator';
import {SnackbarService} from '@gu/components';
import {Zaak, TableSort, ZaakObject} from '@gu/models';
import {SearchService} from '../search.service';
import {MapGeometry, MapMarker} from "../../../../../shared/ui/components/src/lib/components/map/map";
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';


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
  readonly errorMessage = 'Er is een fout opgetreden bij het zoeken naar zaken.'

  @Input() sortData: TableSort;

  @Input() pageData: PageEvent;
  @Output() loadResult: EventEmitter<Zaak[]> = new EventEmitter<Zaak[]>();
  @Output() resultLength: EventEmitter<number> = new EventEmitter<number>();

  @Output() mapGeometry: EventEmitter<MapGeometry> = new EventEmitter<MapGeometry>();
  @Output() mapMarkers: EventEmitter<MapMarker[]> = new EventEmitter<MapMarker[]>();

  isLoading: boolean;

  /** Tabs */
  tabs: object[] = [
    {
      link: 'zaak',
      title: 'Zoeken op zaak'
    },
    {
      link: 'object',
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
   * Gets called when zaak (case) objects are searched for.
   */
  searchObjects() {
    this.loadResult.emit([]);
    this.resultLength.emit(0);
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
      },
      this.reportError.bind(this)
    );
  }

  /**
   * Create tab link
   * @param tab
   * @returns {string}
   */
  getTabLink(tab) {
    return `/zoeken/${tab}`;
  }

  /**
   * Redirect to url
   * @param tab
   */
  setUrl(tab) {
    this.location.go(this.getTabLink(tab))
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
