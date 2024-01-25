import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  NgZone,
  OnChanges,
  OnDestroy,
  OnInit,
  Output, ViewEncapsulation
} from '@angular/core';
import {Position} from '@gu/models';
import {MapGeometry, MapMarker, MapAction} from './map';
import {RD_CRS} from './rd';
import * as L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';

/** @type {string} path to leaflet assets. */
const LEAFLET_ASSETS = 'assets/vendor/leaflet/'

/**
 * <gu-map></gu-map>
 *
 * Shows a Leaflet map.
 *
 * Takes center: Position as coordinates (long lat).
 * Takes height: string as CSS value for the map's height.
 * Takes zoom: number as zoom value.

 * Takes mapGeometries: MapGeometry[] as geometry layers.
 * Takes mapMarkers: MapMarker[] as marker layers.

 * Takes editable: boolean|L.PM.ToolbarOptions whether to allow creating/editing shapes.
 */
@Component({
  selector: 'gu-map',
  templateUrl: 'map.component.html',
  styleUrls: ['./map.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class MapComponent implements OnInit, OnChanges, OnDestroy {
  @Input() center: Position;
  @Input() height: string;
  @Input() zoom = 9;

  @Input() mapGeometries: MapGeometry[] = []
  @Input() mapMarkers: MapMarker[] = []

  @Input() editable: boolean | L.PM.ToolbarOptions = false;

  @Output() mapLoad: EventEmitter<any> = new EventEmitter<any>();
  @Output() shapeChange: EventEmitter<any> = new EventEmitter<any>();
  @Output() shapeChangeComplete: EventEmitter<any> = new EventEmitter<any>();

  /** @type {MapOptions} */
  mapOptions: L.MapOptions;

  /** @type {Object} The leaflet instance. */
  map = null;

  /** @type {boolean} Whether the map is in edit mode. */
  editMode = false;

  /** @type {L.Layer} Temporary maker layer (used when creating a marker). */
  temporaryMarkerLayer: L.Layer;

  constructor(private zone: NgZone) {
  }

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    this.zone.runOutsideAngular(() => {
      requestAnimationFrame(() => {
        this.getContextData();
      });
    })
  }

  /**
   * A lifecycle hook that is called after Angular has fully initialized a component's view. Define an ngAfterViewInit()
   * method to handle any additional initialization tasks.
   */
  ngOnChanges(): void {
    this.update()
  }

  /**
   * A lifecycle hook that is called when a directive, pipe, or service is destroyed. Use for any custom cleanup that
   * needs to occur when the instance is destroyed.
   */
  ngOnDestroy() {
    this.map.remove();
  }

  //
  // Context.
  //

  /**
   * Sets the map context.
   */
  getContextData(): void {
    L.Icon.Default.imagePath = LEAFLET_ASSETS,

      // Map.
      this.mapOptions = {
        center: (this.center?.length > 1) ? L.latLng(this.center[1], this.center[0]) : L.latLng([52.0907, 5.1214]),
        zoom: this.zoom,
        crs: RD_CRS
      };

    this.map = L.map('mapid', this.mapOptions).whenReady(() => {
      setTimeout(() => {
        this.onMapReady(this.map);
        this.mapLoad.emit(this.map)
      })
    })

    // Tiles.
    const tileConfig = {
      url: `https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:28992/{z}/{x}/{y}.png`,
      options: {
        minZoom: 1,
        maxZoom: 13,
        attribution: `
          Kaartgegevens &copy;
            <a href="https://www.kadaster.nl">Kadaster</a> |
            <a href="https://www.verbeterdekaart.nl">Verbeter de kaart</a>
            `,
      },
    };
    const tileLayer = L.tileLayer(tileConfig.url, tileConfig.options);
    tileLayer.addTo(this.map)

    // Leaflet-geoman.
    if (this.editable) {

      const onDrawEnd = (e) => {
        this.shapeChange.emit(e);

        if (e.shape.toUpperCase() === 'MARKER') {
          this.removeTemporaryMarkerLayer();
          this.shapeChangeComplete.emit(e);
        }
      };

      this.map.on('pm:create', (e) => {
        this.shapeChange.emit(e);

        if (e.shape.toUpperCase() === 'MARKER') {
          this.removeTemporaryMarkerLayer();
          this.temporaryMarkerLayer = e.layer;
        }

        if (e.shape.toUpperCase() === 'POLYGON') {
          this.shapeChangeComplete.emit(e);
        }
      });

      this.map.on('pm:drawstart', (e) => this.shapeChange.emit(e));
      this.map.on('pm:drawend', onDrawEnd);

      this.map.on('pm:remove', (e) => {
        this.shapeChange.emit(e);
        this.shapeChangeComplete.emit(e);
      });

      this.map.on('pm:actionclick', (e) => {
        if (e.action.text.toUpperCase() === 'CANCEL') {
          this.removeTemporaryMarkerLayer();
          this.map.off('pm:drawend');
          setTimeout(() => this.map.on('pm:drawend', onDrawEnd));
          return;
        }

        if (e.action.text.toUpperCase() === 'FINISH') {
          this.shapeChangeComplete.emit(e);
        }
      });
    }

    // Update.
    this.update();
  }

  /**
   * Removes this.temporaryMarkerLayer (if set) from this.map.
   */
  removeTemporaryMarkerLayer(): void {
    if (!this.temporaryMarkerLayer) {
      return;
    }
    this.map.removeLayer(this.temporaryMarkerLayer);
  }

  /**
   * Scale map to fit markers
   */
  fitMapBounds() {
    // Get all visible Markers
    const visibleMarkers = [];
    this.map.eachLayer(layer => {
      if (layer instanceof L.Marker) {
        const latInNetherlands = layer.getLatLng().lng >= 4 && layer.getLatLng().lng <= 7;
        const lngInNetherlands = layer.getLatLng().lat >= 51 && layer.getLatLng().lat <= 53
        if (latInNetherlands && lngInNetherlands) {
          visibleMarkers.push(layer);
        }
      }
    });

    // Ensure there's at least one visible Marker
    if (visibleMarkers.length > 0) {

      // Create bounds from first Marker then extend it with the rest
      const markersBounds = L.latLngBounds([visibleMarkers[0].getLatLng()]);
      visibleMarkers.forEach((marker) => {
        markersBounds.extend(marker.getLatLng());
      });

      // Fit the map with the visible markers bounds
      this.map.flyToBounds(markersBounds, {
        padding: L.point(0, 0.5), animate: true,
      });
    }
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
      Array.from(document.querySelectorAll('.collapse__button, .mat-tab-link'))
        .forEach((node) => {
          node.addEventListener('click', this.update.bind(this));
        });
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

    // Invalidate size.
    requestAnimationFrame(() => {
      this.map.invalidateSize();
    });

    // Remove all layers.
    this.map.eachLayer((layer) => {
      if (!!layer.toGeoJSON) {
        this.map.removeLayer(layer);
      }
    });

    // @ts-ignore
    // Add geometries
    this.mapGeometries.filter(v => v).forEach((mapGeometry) => {
      // @ts-ignore
      const mapGeometryLayer = L.geoJSON(mapGeometry.geometry);
      this.addPopUp(mapGeometry, mapGeometryLayer);

      mapGeometryLayer.addEventListener('click', () => mapGeometry.onClick ? mapGeometry.onClick() : null);
      this.map.addLayer(mapGeometryLayer);

      if (mapGeometry.editable) {
        // @ts-ignore
        mapGeometryLayer.pm.enable({draggable: true});
      }

      if (mapGeometry.onChange) {
        mapGeometryLayer.on('pm:edit', (e) => mapGeometry.onChange(e));
        mapGeometryLayer.on('pm:update', (e) => mapGeometry.onChange(e));
        mapGeometryLayer.on('pm:drag', (e) => mapGeometry.onChange(e));
        mapGeometryLayer.on('pm:dragstart', (e) => mapGeometry.onChange(e));
        mapGeometryLayer.on('pm:dragend', (e) => mapGeometry.onChange(e));
        mapGeometryLayer.on('pm:rotate', (e) => mapGeometry.onChange(e));
      }
    })


    // Add markers
    this.mapMarkers.filter(v => v).map((mapMarker: MapMarker) => {
      const iconSize = (mapMarker.iconSize || [25, 41]) as L.PointExpression;
      const icon = new L.Icon({
        iconAnchor: (mapMarker.iconAnchor || [iconSize[0] / 2, iconSize[1]]) as L.PointExpression,
        iconUrl: mapMarker.iconUrl,
        iconSize: iconSize,
        shadowAnchor: (mapMarker.shadowAnchor || [14, 62]) as L.PointExpression,
        shadowSize: (mapMarker.shadowSize || [50, 64]) as L.PointExpression,
        shadowUrl: mapMarker.shadowUrl || `assets/vendor/leaflet/marker-shadow.png`,
      })

      const markerOptions = {
        icon: mapMarker.iconUrl ? icon : undefined,
      }

      const mapMarkerlayer = L.marker([mapMarker.coordinates[0], mapMarker.coordinates[1]] as L.LatLngExpression, markerOptions);
      this.addPopUp(mapMarker, mapMarkerlayer);


      mapMarkerlayer.addEventListener('click', () => mapMarker.onClick ? mapMarker.onClick() : null);
      this.map.addLayer(mapMarkerlayer);

      if (mapMarker.editable) {
        // @ts-ignore
        mapMarkerlayer.pm.enable({draggable: true});
      }

      if (mapMarker.onChange) {
        mapMarkerlayer.on('pm:edit', (e) => mapMarker.onChange(e));
        mapMarkerlayer.on('pm:update', (e) => mapMarker.onChange(e));
        mapMarkerlayer.on('pm:drag', (e) => mapMarker.onChange(e));
        mapMarkerlayer.on('pm:dragstart', (e) => mapMarker.onChange(e));
        mapMarkerlayer.on('pm:dragend', (e) => mapMarker.onChange(e));
        mapMarkerlayer.on('pm:rotate', (e) => mapMarker.onChange(e));
      }
    });

    this.fitMapBounds();

    if (this.editable) {
      this.map.pm.removeControls();
      this.map.pm.addControls((typeof this.editable === 'boolean')
        ? {
          drawControls: this.editMode,
          editControls: this.editMode,

          position: 'topleft',

          drawRectangle: false,
          drawCircle: false,
          drawCircleMarker: false,
          drawPolyline: false,

          cutPolygon: false,
          rotateMode: false,

          positions: {
            draw: 'topright',
            edit: 'topright',
          }
        }
        : this.editable
      );

      if (typeof this.editable === 'boolean' && this.map.pm.Toolbar.getControlOrder().indexOf('Edit') === -1) {
        this.map.pm.Toolbar.createCustomControl({
          block: 'custom',
          className: 'leaflet-pm-icon-edit',
          name: 'Edit',
          title: 'Edit',
          toggle: false,
          onClick: () => {
            this.editMode = !this.editMode;
            this.update();
          },
        });
        this.map.pm.Toolbar.changeControlOrder(['Edit'])
      }
    }
  }

  /**
   * Adds a popup to a MapGeometry or MapMarker.
   * @param {MapGeometry | MapMarker} mapGeometryOrMapMarker
   * @param layer
   */
  addPopUp(mapGeometryOrMapMarker: MapGeometry | MapMarker, layer): void {
    const popUp = L.popup()
    const popUpContent = document.createElement('div');

    if (mapGeometryOrMapMarker.title) {
      const title = document.createElement('h4');
      title.innerHTML = mapGeometryOrMapMarker.title;
      popUpContent.appendChild(title)
    }

    if (mapGeometryOrMapMarker.contentProperties) {
      const table = document.createElement('table');
      let stringRepresentation;
      mapGeometryOrMapMarker.contentProperties.forEach(([key, value]) => {
        let formattedKey;
        let formattedValue;
        if (key === 'stringRepresentation') {
          stringRepresentation = value
        } else {
          if (key === 'start-case') {
            const anchor = document.createElement('a');
            anchor.href = `/ui/zaak-starten?objectUrl=${value}&stringRepresentation=${stringRepresentation}`;
            anchor.textContent = 'Zaak starten met dit object';

            formattedKey = '';
            formattedValue = anchor.outerHTML
          } else {
            formattedKey = this.formatProperty(key);
            formattedValue = this.formatValue(value);
          }

          const tr = document.createElement('tr');
          const th = document.createElement('th');
          th.textContent = formattedKey;

          const td = document.createElement('td');
          td.innerHTML = formattedValue;

          tr.appendChild(th);
          tr.appendChild(td);
          table.appendChild(tr);
        }
      });

      popUpContent.appendChild(table);
    }

    if (mapGeometryOrMapMarker.actions) {
      mapGeometryOrMapMarker.actions.forEach((mapAction: MapAction) => {
        const button = document.createElement('button');
        button.innerText = mapAction.label
        button.addEventListener('click', () => {
          mapAction.onClick(mapGeometryOrMapMarker);
          popUp.closePopup();

        });
        popUpContent.appendChild(button);
      })
    }

    if (popUpContent.innerHTML) {
      popUp.setContent(popUpContent)
      layer.bindPopup(popUp)
    }
  }

  /**
   * Attempts to format a property.
   * @param {string} propertyName
   * @return {string}
   */
  formatProperty(propertyName: string): string {
    return propertyName.replace(/[-_]/g, ' ');
  }

  /**
   * Attempts to format a value.
   * @param {string} propertyValue
   * @return {string}
   */
  formatValue(propertyValue: string): string {
    const unsafeValue = propertyValue;
    const safeValue = new DOMParser().parseFromString(unsafeValue, 'text/html').body.textContent;

    if (!safeValue.match(/^http/)) {
      return safeValue;
    }

    const anchor = document.createElement('a');
    anchor.href = safeValue;
    anchor.target = '_blank';
    anchor.textContent = safeValue;

    return anchor.outerHTML;
  }
}
