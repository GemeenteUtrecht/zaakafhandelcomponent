/**
 * Component to select a single bag object based on adress entry with autocomplete.
 */
import { apiCall } from '../../utils/fetch';

import { Map } from './map';

const DEBOUNCE_MS = 200;

// TODO: should probably just be a React component
class BagObjectSelection {
    constructor(node) {
        this.node = node;
        this.autocompleteInput = node.querySelector('.bag-object-selection__autocomplete');
        this.autocompleteContainer = node.querySelector('.bag-object-selection__autocomplete-results');
        this.valueInput = node.querySelector('.bag-object-selection__value');

        // parse config
        const { autocompleteUrl, adresBagObjectUrl } = node.dataset;
        Object.assign(this, { autocompleteUrl, adresBagObjectUrl });

        this.bindAutoComplete();
        this._keyupDebounce = null;

        this.bindReset();

        this.map = this.initMap();

        this.installMutationObserver();
    }

    // hacky way to redraw map if parent changes visibility via display attribute
    installMutationObserver() {
        const container = this.node.parentNode;
        const observer = new MutationObserver(() => {
            this.map._map.invalidateSize();
        });
        observer.observe(container, {attributes: true});
    }

    bindAutoComplete() {
        this.autocompleteInput.addEventListener('keyup', (event) => this.onKeyUp(event));
    }

    bindResultClicks() {
        const nodes = this.autocompleteContainer.querySelectorAll('.bag-object-selection__result');
        nodes.forEach(result => {
            result.addEventListener('click', (event) => {
                event.preventDefault();
                const id = result.dataset.id;
                this.getBagObject(id);
            });
        });
    }

    bindReset() {
        const reset = this.node.querySelector('.bag-object-selection__reset');
        reset.addEventListener('click', (event) => {this.reset(event);});
    }

    onKeyUp(event) {
        if (this._keyupDebounce) {
            window.clearTimeout(this._keyupDebounce);
        }

        const q = event.target.value;
        if (!q) {
            this.autocompleteContainer.innerHTML = '';
            return;
        }

        this._keyupDebounce = window.setTimeout(() => {
            this
                .getAutocompleteResults(q)
                .then((json) => this.renderAutocompleteResults(json))
            ;
        }, DEBOUNCE_MS);
    }

    getAutocompleteResults(q = '') {
        if (!q) {
            throw new Error('You must provide a search query');
        }
        return apiCall(`${this.autocompleteUrl}?q=${q}`)
            .then(response => response.json())
            .catch(console.error)
        ;
    }

    renderAutocompleteResults(json) {
        const docs = json.response.docs;
        const results = docs.map(doc => {
            const text = json.highlighting[doc.id].suggest;
            const result = `
                <a href="#" class="bag-object-selection__result"
                   data-id="${doc.id}" title="${doc.weergavenaam}"
                >${text}</a>
            `;
            return result;

        });
        this.autocompleteContainer.innerHTML = results.join('\n');
        this.autocompleteContainer.classList.add('bag-object-selection__autocomplete-results--active');
        this.bindResultClicks();
    }

    getBagObject(id) {
        if (!id) {
            throw new Error('You must provide an appropriate ID');
        }

        apiCall(`${this.adresBagObjectUrl}?id=${id}`)
            .then(response => response.json())
            .then(json => this.showBagObject(json))
            .catch(console.error)
        ;
    }

    initMap() {
        const mapNode = this.node.querySelector('.bag-object-selection__map');
        const map = new Map(mapNode, {
            center: [52.1326332, 5.291266],
            zoom: 3,
        });
        map.draw();
        return map;
    }

    showBagObject(bagObjectLookup) {
        const { bagObject, adres } = bagObjectLookup;
        const feature = {
            type: 'Feature',
            properties: {
                url: bagObject.url,
                adres: adres,
                status: bagObject.status,
            },
            geometry: bagObject.geometrie,
        };
        this.map.showFeature(feature);
        this.valueInput.value = bagObject.url;
        this.autocompleteContainer.classList.remove('bag-object-selection__autocomplete-results--active');
    }

    reset(event) {
        event.preventDefault();

        if (this._keyupDebounce) {
            window.clearTimeout(this._keyupDebounce);
        }

        this.autocompleteInput.value = '';
        this.valueInput.value = '';
        this.autocompleteContainer.innerHTML = '';

        this.map.reset();
    }
}


// initialize
const selections = document.querySelectorAll('.bag-object-selection');
Array.from(selections).forEach(node => new BagObjectSelection(node));
