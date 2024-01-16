import {ChangeDetectionStrategy, ChangeDetectorRef, Component, Inject, OnInit, Renderer2} from '@angular/core';
import {TableSort, Zaak} from '@gu/models';
import {PageEvent} from '@angular/material/paginator';
import {MapGeometry, MapMarker} from "../../../../shared/ui/components/src/lib/components/map/map";
import {ZaakService} from "@gu/services";

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeaturesSearchComponent {
  mapGeometries: MapGeometry[] = [];
  mapMarkers: MapMarker[] = [];

  resultData: Zaak[] = [];
  isVisible = false;
  resultLength: number;
  sortData: TableSort;
  pageData: PageEvent;

  constructor(
    private changeDetectorRef: ChangeDetectorRef,
    private zaakService: ZaakService
  ) { }

  //
  // Context.
  //

  /**
   * Returns whether geo information is available.
   * @return {boolean}
   */
  hasGeoInformation() {
    return this.mapGeometries.filter(g=>g.geometry).length || this.mapMarkers.length;
  }

  /**
   * Gets the map geometreis to show on the map.
   * @return {MapGeometry[]}
   */
  getZaakMapGeometries(): MapGeometry[] {
    return this.resultData.map((zaak) => this.zaakService.zaakToMapGeometry(zaak, {
      onClick: () => {
        this.zaakService.navigateToCase(zaak);
      },
    }));
  }

  //
  // Events.
  //

  /**
   * Gets called when a map geometry callback is triggered.
   * @param {MapGeometry} mapGeometry
   */
  onMapGeometry(mapGeometry: MapGeometry): void {
    this.mapGeometries = [...this.getZaakMapGeometries(), mapGeometry];
  }

  /**
   * Gets called when a map marker callback is triggered.
   * @param {MapMarker[]} mapMarkers
   */
  onMapMarkers(mapMarkers: MapMarker[]): void {
    this.mapMarkers = mapMarkers;
  }

  /**
   * Gets called when the result is loaded.
   * @param {Zaak[]} cases
   */
  onLoadResult(cases: Zaak[]): void {
    this.resultData = cases
    this.changeDetectorRef.detectChanges()
  }

  /**
   * Gets called on result length.
   * @param data
   */
  onResultLength(data): void {
    this.resultLength = data;
  }

  /**
   * Check if results need to be shown
   * @param isVisible
   */
  onShowResults(isVisible): void {
    this.isVisible = isVisible;
  }
}
