import {ChangeDetectionStrategy, Component, Input, OnChanges, OnInit} from '@angular/core';
import {geoJSON, latLng, LatLngExpression, MapOptions, marker, tileLayer} from 'leaflet';
import {Geometry, Position} from '@gu/models';
import {MapMarker} from './map';
import {RD_CRS} from './rd';


/**
 * <gu-map></gu-map>
 *
 * Shows a Leaflet map.
 *
 * Takes center: Position as coordinates (long lat).
 * Takes height: string as CSS value for the map's height.
 * Takes zoom: number as zoom value.

 * Takes geometries: Geometry[] as geometry layers.
 * Takes MapMarker: MapMarker[] as marker layers.
 */
@Component({
  selector: 'gu-map',
  templateUrl: 'map.component.html',
  styleUrls: ['map.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class MapComponent implements OnInit, OnChanges {
  @Input() center: Position = [5.1214, 52.0907] as Position;
  @Input() height: string;
  @Input() zoom = 10;

  @Input() geometries: Geometry[] = []
  @Input() mapMarkers: MapMarker[] = []

  /** @type {MapOptions} */
  mapOptions: MapOptions;

  /** @type {Object} The leaflet instance. */
  map = null;

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
  ngOnChanges(): void {
    this.getContextData()
  }

  //
  // Context.
  //

  /**
   * Sets the map context.
   */
  getContextData(): void {
    const MAP_DEFAULTS = {
      crs: RD_CRS,
    };

    const tilesService = 'https://geodata.nationaalgeoregister.nl/tiles/service';
    const attribution = `
      Kaartgegevens &copy;
      <a href="https://www.kadaster.nl">Kadaster</a> |
      <a href="https://www.verbeterdekaart.nl">Verbeter de kaart</a>
    `;

    const tileLayers = {
      brt: {
        url: `${tilesService}/wmts/brtachtergrondkaart/EPSG:28992/{z}/{x}/{y}.png`,
        options: {
          minZoom: 1,
          maxZoom: 13,
          attribution: attribution,
        },
      },
    };

    const layers = [
      tileLayer(tileLayers.brt.url, tileLayers.brt.options),
    ]

    this.mapOptions = Object.assign({}, MAP_DEFAULTS, {
      center: latLng(this.center[1], this.center[0]),
      zoom: this.zoom,
      layers: layers,
    });

    this.update();
  }

  //
  // Events.
  //

  /**
   * Binds events on the DOM and bind them to this.update().
   * This makes sure the map re-rendered when it's on a tab that gets activated.
   */
  bindDomEvents(): void {
    try {
      document.addEventListener('click', this.update.bind(this));
      document.addEventListener('keyup', this.update.bind(this));
    } catch (e) {
    }
  }

  /**
   * Gets called when the Leaflet map is ready.
   * @param {Object} map
   */
  onMapReady(map): void {
    this.map = map;
    this.bindDomEvents();
    this.update();
  }

  /**
   * Re-renders the map.
   */
  update(): void {
    if (!this.map) {
      return
    }

    requestAnimationFrame(() => {
      this.map.invalidateSize();
    });

    this.map.eachLayer((layer) => {
      if (!!layer.toGeoJSON) {
        this.map.removeLayer(layer);
      }
    });

    // @ts-expect-error
    this.geometries.map((geometry) => geoJSON(geometry))
      .forEach((layer) => this.map.addLayer(layer));

    this.mapMarkers.map((mapMarker: MapMarker) => {
      const _marker = marker([mapMarker.coordinates[0], mapMarker.coordinates[1]] as LatLngExpression);
      _marker.addEventListener('click', () => mapMarker.onClick ? mapMarker.onClick() : null);
      return _marker;
    })
      .forEach((layer) => this.map.addLayer(layer));
  }
}
