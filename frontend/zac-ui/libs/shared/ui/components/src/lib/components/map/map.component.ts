import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output, ViewEncapsulation
} from '@angular/core';
import {Position} from '@gu/models';
import {MapGeometry, MapMarker} from './map';
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

  //
  // Angular lifecycle.
  //

  /**
   * A lifecycle hook that is called after Angular has initialized all data-bound properties of a directive. Define an
   * ngOnInit() method to handle any additional initialization tasks.
   */
  ngOnInit(): void {
    requestAnimationFrame(() => {
      this.getContextData();
    });
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
        crs: RD_CRS,
      };
    this.map = L.map('mapid', this.mapOptions)

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

    this.map.on('load', this.mapLoad.emit(this.map));

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
      const layer = L.geoJSON(mapGeometry.geometry, )

      if(mapGeometry.title) {
        layer.bindTooltip(mapGeometry.title);
      }

      layer.addEventListener('click', () => mapGeometry.onClick ? mapGeometry.onClick() : null);
      this.map.addLayer(layer);

      if (mapGeometry.editable) {
        // @ts-ignore
        layer.pm.enable({draggable: true});
      }

      if (mapGeometry.onChange) {
        layer.on('pm:edit', (e) => mapGeometry.onChange(e));
        layer.on('pm:update', (e) => mapGeometry.onChange(e));
        layer.on('pm:drag', (e) => mapGeometry.onChange(e));
        layer.on('pm:dragstart', (e) => mapGeometry.onChange(e));
        layer.on('pm:dragend', (e) => mapGeometry.onChange(e));
        layer.on('pm:rotate', (e) => mapGeometry.onChange(e));
      }
    })


    // Add markers
    this.mapMarkers.filter(v => v).map((mapMarker: MapMarker) => {
      const iconSize = (mapMarker.iconSize || [25, 41]) as L.PointExpression;
      const icon = new L.Icon({
        iconAnchor: (mapMarker.iconAnchor || [iconSize[0]/2, iconSize[1]]) as L.PointExpression,
        iconUrl: mapMarker.iconUrl,
        iconSize: iconSize,
        shadowAnchor: (mapMarker.shadowAnchor || [14, 62]) as L.PointExpression,
        shadowSize: (mapMarker.shadowSize || [50,64]) as L.PointExpression,
        shadowUrl: mapMarker.shadowUrl || `assets/images/map/marker-shadow.png`,
      })

      const markerOptions = {
        icon: mapMarker.iconUrl ? icon : undefined,
      }

      const marker = L.marker([mapMarker.coordinates[0], mapMarker.coordinates[1]] as L.LatLngExpression, markerOptions);

      if(mapMarker.title) {
        marker.bindTooltip(mapMarker.title);
      }

      marker.addEventListener('click', () => mapMarker.onClick ? mapMarker.onClick() : null);
      this.map.addLayer(marker);

      if (mapMarker.editable) {
        // @ts-ignore
        marker.pm.enable({draggable: true});
      }

      if (mapMarker.onChange) {
        marker.on('pm:edit', (e) => mapMarker.onChange(e));
        marker.on('pm:update', (e) => mapMarker.onChange(e));
        marker.on('pm:drag', (e) => mapMarker.onChange(e));
        marker.on('pm:dragstart', (e) => mapMarker.onChange(e));
        marker.on('pm:dragend', (e) => mapMarker.onChange(e));
        marker.on('pm:rotate', (e) => mapMarker.onChange(e));
      }
    });

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
}
