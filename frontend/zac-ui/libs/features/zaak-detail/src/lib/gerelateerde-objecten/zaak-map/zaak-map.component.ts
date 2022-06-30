import {AfterViewInit, Component, Input, OnInit, ViewChild} from '@angular/core';
import {debounceTime, distinctUntilChanged, filter, tap} from 'rxjs/operators';
import {Subject} from 'rxjs';
import * as L from 'leaflet';
import proj4 from 'proj4';
import {MapGeometry, MapMarker, SnackbarService} from '@gu/components';
import {Geometry, Position, RelatedCase, Zaak, ZaakObject, ZaakObjectGroup} from '@gu/models';
import {KadasterService, ZaakObjectService, ZaakService} from '@gu/services';


@Component({
  selector: 'gu-zaak-map',
  templateUrl: './zaak-map.component.html',
  styleUrls: ['./zaak-map.component.scss']
})
export class ZaakMapComponent implements OnInit, AfterViewInit {
  @Input() bronorganisatie: string;
  @Input() identificatie: string;

  /** @type {Zaak} The case (zaak) to show geographical information for. */
  zaak: Zaak = null;

  /** @type {Object} The map instance. */
  map: any = null;

  /** @type {MapGeometry[]} The map geometries to draw on the map. */
  mapGeometries: MapGeometry[] = [];

  /** @type {MapGeometry[]} The map geometry that is being changed. */
  updatedMapGeometry: MapGeometry;

  /** @type {mapMarkers[]} The map markers to draw on the map. */
  mapMarkers: MapMarker[] = [];

  /** @type {number[]} The map's center coordinates. */
  center = null;

  /** @type {Subject} The suggestion query subject. */
  suggestionsQuerySubject: Subject<string> = new Subject<string>();

  /** @type {Object[]} The suggestions from the BAG api. */
  suggestions = [];

  /** @type {string} Possible error message. */
  readonly errorMessage = 'Er is een fout opgetreden bij het ophalen van zaakinformatie.'

  constructor(
    private snackbarService: SnackbarService,
    private zaakService: ZaakService,
    private zaakObjectService: ZaakObjectService,
    private kadasterService: KadasterService,
  ) {
  }

  @ViewChild('inputRef') inputRef;

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.getContextData();
  }

  /**
   * A lifecycle hook that is called after Angular has fully initialized a component's view. Define an ngAfterViewInit()
   * method to handle any additional initialization tasks.
   */
  ngAfterViewInit() {
    this.suggestionsQuerySubject.pipe(
      filter(Boolean),
      debounceTime(300),
      distinctUntilChanged(),
      tap(this.listBAGSuggestions.bind(this))
    ).subscribe()
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
    // List related objects.
    this.zaakService.listRelatedObjects(this.bronorganisatie, this.identificatie).subscribe(
      (zaakObjectGroups: ZaakObjectGroup[]) => {
        const zaakObjects = zaakObjectGroups
          .reduce((acc: ZaakObject[], zaakObjectGroup: ZaakObjectGroup) => {
            return [...acc, ...zaakObjectGroup.items]
          }, [])


        this.mapMarkers = [];

        zaakObjects.forEach((zaakObject, index) => {
          // Async zaakObjectToMapMarker
          this.zaakObjectService.zaakObjectToMapMarker(zaakObject).subscribe((mapMarker) => {
              // Add map marker.
              this.mapMarkers = [...this.mapMarkers, mapMarker];
            },

            // Report error.
            this.reportError.bind(this)
          );
        })
      },
      this.reportError.bind(this),
    );
  }

  /**
   * Gets suggestions from the BAG API.
   * @param {string} query
   */
  listBAGSuggestions(query: string): void {
    this.kadasterService.listBAGAddressSuggestions(query).subscribe((data) => {
      this.suggestions = data.response.docs;
    }, this.reportError.bind(this));
  }

  /**
   * Fetches a pand from the BAG API.
   * @param {string} query
   */
  fetchBAGPand(query: string): void {
    if (!query) {
      return;
    }

    this.kadasterService.listBAGAddressSuggestions(query).subscribe((data) => {
      const docs = data.response.docs;

      if (!docs.length) {
        return
      }

      const id = docs[0].id;
      this.kadasterService.retrievePand(id).subscribe((pand) => {
        const geometry: Geometry = pand.bagObject.geometrie;
        const position28992 = [geometry.coordinates[0][0][0], geometry.coordinates[0][0][1]] as Position;
        const position4326 = this.transformPosition(position28992);

        const lLatLng = L.latLng([position4326[1], position4326[0]] as any);
        this.map.setView(lLatLng, 13);

        this.mapGeometries = [...this.mapGeometries, {
          geometry: this.transformGeometry(pand.bagObject.geometrie),
          title: `${pand.adres.straatnaam} ${pand.adres.nummer}`,
          actions: [{
            label: 'Gebruik als zaakgeometrie',
            onClick: (mapGeometry) => this.updateCaseGeometry(mapGeometry.geometry),
          }]
        } as MapGeometry]
      }, this.reportError.bind(this));
    }, this.reportError.bind(this));
  }

  /**
   * Returns the datalist values with suggestions.
   * @return {string[]}
   */
  getDatalist(): string[] {
    return this.suggestions.map((suggestion) => suggestion.weergavenaam);
  }

  /**
   * Converts a Geometry with coordinates in EPSG:28992 format to EPSG:4326.
   * @param {Geometry} geometry
   */
  transformGeometry(geometry: Geometry): Geometry {
    const _geometry = JSON.parse(JSON.stringify(geometry));

    switch (_geometry.type) {
      case 'Point':
        _geometry.coordinates = this.transformPosition(_geometry.coordinates as Position);
        break;
      case 'MultiPoint':
        _geometry.coordinates = this.transformPositions(_geometry.coordinates as Position[]);
        break;
      case 'LineString':
        _geometry.coordinates = this.transformPositions(_geometry.coordinates as Position[]);
        break
      case 'MultiLineString':
        _geometry.coordinates = this.transformNestedPositions(_geometry.coordinates as Position[][]);
        break
      case 'Polygon':
        _geometry.coordinates = this.transformNestedPositions(_geometry.coordinates as Position[][]);
        break
      case 'MultiPolygon':
        _geometry.coordinates = this.transformDoubleNestedPositions(_geometry.coordinates as Position[][][]);
        break
    }

    return _geometry;
  }

  transformPosition(position28992: Position): Position {
    return proj4('EPSG:28992', 'EPSG:4326', [position28992[0], position28992[1]]);
  }

  transformPositions(positions28992: Position[]): Position[] {
    return positions28992.map((position28992: Position) => this.transformPosition(position28992))
  }

  transformNestedPositions(nestedPositions28992: Position[][]): Position[][] {
    return nestedPositions28992.map((positions2899: Position[]) => this.transformPositions(positions2899));
  }

  transformDoubleNestedPositions(doubleNestedPositions28992: Position[][][]): Position[][][] {
    return doubleNestedPositions28992.map((nestedPositions28992: Position[][]) => this.transformNestedPositions(nestedPositions28992));
  }

  //
  // Events.
  //

  /**
   * Gets called when the map is loaded.
   * @param {Object} map
   */
  onMapLoad(map): void {
    this.map = map;
  }

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

    this.updateCaseGeometry(geometry);
  }

  /**
   * Updates the zaak (case) geometry.
   * @param geometry
   */
  updateCaseGeometry(geometry): void {
    this.zaakService.updateCaseDetails(this.bronorganisatie, this.identificatie, {
      reden: 'SYSTEM: geolocation change.',
      vertrouwelijkheidaanduiding: this.zaak.vertrouwelijkheidaanduiding,
      zaakgeometrie: geometry
    }).subscribe(this.getContextData.bind(this), this.reportError.bind(this));
  }


  /**
   * Handles input "input" event.
   * @param {Event} e
   */
  onInputInput(e): void {
    const query = e.target.value;
    this.suggestionsQuerySubject.next(query);
  }

  /**
   * Handles input "change" event.
   * @param {Event} e
   */
  onInputChange(e): void {
    const query = e.target.value;
    this.fetchBAGPand(query);
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
