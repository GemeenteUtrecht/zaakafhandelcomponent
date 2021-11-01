import {Component, Input, OnInit} from '@angular/core';
import * as L from 'leaflet';
import {SnackbarService} from '@gu/components';
import {ZaakObjectService, ZaakService} from '@gu/services';
import {RelatedCase, Zaak, ZaakObject, ZaakObjectGroup} from '@gu/models';
import {MapGeometry, MapMarker} from '../../../../../shared/ui/components/src/lib/components/map/map';

@Component({
  selector: 'gu-zaak-map',
  templateUrl: './zaak-map.component.html'
})
export class ZaakMapComponent implements OnInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  /** @type {Zaak} The case (zaak) to show geographical information for. */
  zaak: Zaak = null;

  /** @type {MapGeometry[]} The map geometries to draw on the map. */
  mapGeometries: MapGeometry[] = [];

  /** @type {MapGeometry[]} The map geometry that is being changed. */
  updatedMapGeometry: MapGeometry;

  /** @type {mapMarkers[]} The map markers to draw on the map. */
  mapMarkers: MapMarker[] = [];

  /** @type {number[]} The map's center coordinates. */
  center = null;

  /** @type {string} Possible error message. */
  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van zaakinformatie.'

  constructor(private snackbarService: SnackbarService, private zaakService: ZaakService, private zaakObjectService: ZaakObjectService) {
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
   * Fetches the case (zaak) and sets geometrical data.
   */
  getContextData(): void {
    this.mapGeometries = [];
    this.getZaakMapGeometries();
    this.getRelatedZaakMapGeometries();
    this.getRelatedObjectGeometries();
  }

  /**
   * Fetches case (zaak) geometries.
   */
  getZaakMapGeometries(): void {
    this.zaakService.retrieveCaseDetails(this.bronorganisatie, this.identificatie).subscribe(
      (zaak) => {
        if (zaak.zaakgeometrie?.coordinates) {
          const latLng = L.polygon([zaak.zaakgeometrie.coordinates] as L.LatLngExpression[]).getBounds().getCenter()
          this.center = [latLng.lat, latLng.lng];
          this.mapGeometries = [...this.mapGeometries, this.zaakService.zaakToMapGeometry(zaak, {
            onChange: this.onMapShapeChange.bind(this),
          })];
        }
        this.zaak = zaak;
      },
      this.reportError.bind(this)
    );
  }
  /**
   * Fetches related case (zaak) geometries.
   */
  getRelatedZaakMapGeometries() {
    this.zaakService.listRelatedCases(this.bronorganisatie, this.identificatie).subscribe(
      (relatedCases: RelatedCase[]) => {
        const cases = relatedCases.map((relatedCase: RelatedCase) => relatedCase.zaak);

        cases.forEach((zaak: Zaak) => {
          this.mapGeometries = [...this.mapGeometries, this.zaakService.zaakToMapGeometry(zaak, {
            onChange: this.onMapShapeChange.bind(this),
          })];
        });
      }
    );
  }

  /**
   * Fetches related object geometries.
   */
  getRelatedObjectGeometries(): void {
    this.zaakService.listRelatedObjects(this.bronorganisatie, this.identificatie).subscribe(
      (zaakObjectGroups: ZaakObjectGroup[]) => {
        this.mapMarkers = zaakObjectGroups
          .reduce((acc: ZaakObject[], zaakObjectGroup: ZaakObjectGroup) => {
            return [...acc, ...zaakObjectGroup.items]
          }, [])
          .map(this.zaakObjectService.zaakObjectToMapMarker)
      },
      this.reportError.bind(this),
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
    const layer = event.layer;
    const geoJSON = layer?.toGeoJSON();

    if (!geoJSON) {
      return;
    }

    const geometry = (event.type) === 'pm:remove' ? null : geoJSON?.geometry;

    this.updatedMapGeometry = {
      geometry: geometry,
      onChange: this.onMapShapeChange.bind(this),
    };
  }

  /**
   * Gets called when the shape is done editing.
   * Submits new shape to the API.
   * @param {Event} event
   */
  onMapShapeComplete(event): void {
    const layer = event.layer;
    const geoJSON = layer?.toGeoJSON();
    let geometry = geoJSON?.geometry;

    if (!geometry && this.updatedMapGeometry) {
      geometry = this.updatedMapGeometry.geometry;
      this.updatedMapGeometry = null;
    }

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
