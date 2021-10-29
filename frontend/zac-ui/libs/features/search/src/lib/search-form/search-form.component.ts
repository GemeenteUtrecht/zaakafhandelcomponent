import {Component, EventEmitter, Input, Output} from '@angular/core';
import {PageEvent} from '@angular/material/paginator';
import {SnackbarService} from '@gu/components';
import {Zaak, TableSort, ZaakObject} from '@gu/models';
import {SearchService} from '../search.service';
import {MapGeometry, MapMarker} from "../../../../../shared/ui/components/src/lib/components/map/map";


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

  constructor(private searchService: SearchService, private snackbarService: SnackbarService) {
  }

  //
  // Events.
  //

  /**
   * Gets called when zaak (case) objects are searched for.
   */
  searchObjects() {
    this.loadResult.emit([]);
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

    this.searchService.searchZaken(search, page).subscribe(
      (data) => this.loadResult.emit(data.results as Zaak[]),
      this.reportError.bind(this)
    );
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
