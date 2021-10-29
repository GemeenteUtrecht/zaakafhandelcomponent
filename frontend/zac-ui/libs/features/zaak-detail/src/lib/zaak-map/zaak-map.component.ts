import {Component, Input, OnInit} from '@angular/core';
import * as L from 'leaflet';
import {ZaakService} from '@gu/services';
import {SnackbarService} from '@gu/components';
import {Zaak} from "@gu/models";
import {MapGeometry} from "../../../../../shared/ui/components/src/lib/components/map/map";

@Component({
  selector: 'gu-zaak-map',
  templateUrl: './zaak-map.component.html'
})
export class ZaakMapComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  zaak: Zaak = null;
  mapGeometries: MapGeometry[] = []
  center = null;

  /** @type {string} Possible error message. */
  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van zaakinformatie.'

  constructor(private snackbarService: SnackbarService, private zaakService: ZaakService) {
  }

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData();
  }

  //
  // Context.
  //

  /**
   * Fetches the zaak (case) and sets geometrical data.
   */
  getContextData(): void {
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak) => {
        if (zaak.zaakgeometrie?.coordinates) {
          const latLng = L.polygon([zaak.zaakgeometrie.coordinates] as L.LatLngExpression[]).getBounds().getCenter()
          this.center = [latLng.lat, latLng.lng];
          this.mapGeometries = [{
            geometry: zaak.zaakgeometrie,
            onChange: this.onMapShapeChange.bind(this),
          }]

        }
        this.zaak = zaak;
      },
      this.reportError.bind(this)
    );
  }

  //
  // Events.
  //

  /**
   * Gets called when a shape is either created or modified.
   * @param event
   */
  onMapShapeChange(event): void {
    if (['pm:dragstart', 'pm:drag', 'pm:edit'].indexOf(event.type) > -1) {
      return;
    }

    const layer = event.layer;
    const geoJSON = layer?.toGeoJSON();

    if (!geoJSON) {
      return;
    }

    const geometry = (event.type) === 'pm:remove' ? null : geoJSON?.geometry;

    this.zaakService.updateCaseDetails(this.bronorganisatie, this.identificatie, {
      reden: 'SYSTEM: geolocation change.',
      vertrouwelijkheidaanduiding: this.zaak.vertrouwelijkheidaanduiding,
      zaakgeometrie: geometry
    }).subscribe(this.getContextData.bind(this), this.reportError.bind(this));

  }

  //
  // Error handling.
  //

  /**
   * Error callback.
   * @param {*} error
   */
  reportError(error: any): void {
    this.snackbarService.openSnackBar(this.errorMessage, 'Sluiten', 'warn');
    console.error(error);
  }
}
