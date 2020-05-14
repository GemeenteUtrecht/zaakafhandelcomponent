import * as L from 'leaflet';

import { RD_CRS } from './rd';

// fix leaflet images import - https://github.com/Leaflet/Leaflet/issues/4968
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});


const TILES = 'https://geodata.nationaalgeoregister.nl/tiles/service';
const ATTRIBUTION = `
    Kaartgegevens &copy;
    <a href="https://www.kadaster.nl">Kadaster</a> |
    <a href="https://www.verbeterdekaart.nl">Verbeter de kaart</a>
`;

const TILE_LAYERS = {
    brt: {
        url: `${TILES}/wmts/brtachtergrondkaart/EPSG:28992/{z}/{x}/{y}.png`,
        options: {
            minZoom: 1,
            maxZoom: 13,
            attribution: ATTRIBUTION,
        },
    },
};


const MAP_DEFAULTS = {
    continuousWorld: true,
    crs: RD_CRS,
    attributionControl: true,
};


class Map {
    constructor(node, options={}, tiles='brt') {
        this.node = node;
        this.tiles = tiles;
        this.options = Object.assign({}, MAP_DEFAULTS, options);

        this._map = null;
    }

    draw() {
        if (this._map) {
            return;
        }

        const tiles = L.tileLayer(
            TILE_LAYERS[this.tiles].url,
            TILE_LAYERS[this.tiles].options
        );

        this._map = L.map(this.node, this.options);
        this._map.addLayer(tiles);
    }

    showFeature(feature) {
        if (this._featureLayer) {
            this._map.removeLayer(this._featureLayer);
        }
        this._featureLayer = L.geoJSON(feature).addTo(this._map);
        this._map.fitBounds(this._featureLayer.getBounds());
    }

    reset() {
        if (this._featureLayer) {
            this._map.removeLayer(this._featureLayer);
        }
    }

}


export { Map };
