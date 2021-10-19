import {ChangeDetectionStrategy, ChangeDetectorRef, Component, OnChanges} from '@angular/core';
import {Geometry, TableSort, Zaak} from '@gu/models';
import {PageEvent} from '@angular/material/paginator';
import {MapMarker} from "../../../../shared/ui/components/src/lib/components/map/map";

@Component({
  selector: 'gu-features-search',
  templateUrl: './features-search.component.html',
  styleUrls: ['./features-search.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class FeaturesSearchComponent {
  mapGeometry: Geometry;
  mapMarkers: MapMarker[] = [];

  resultData: Zaak[] = [];
  resultLength: number;
  sortData: TableSort;
  pageData: PageEvent;

  constructor(private changeDetectorRef: ChangeDetectorRef) {}

  onMapGeometry(geometry): void {
    this.mapGeometry = geometry;
  }

  onMapMarkers(mapMarkers): void {
    this.mapMarkers = mapMarkers;
  }

  onLoadResult(data): void {
    this.resultData = data
    this.changeDetectorRef.detectChanges()
  }

  onResultLength(data): void {
    this.resultLength = data;
  }
}
