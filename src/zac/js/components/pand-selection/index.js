/**
 * Component to select a single pand based on adress entry with autocomplete.
 */
import { apiCall } from '../../utils/fetch';

import { Map } from './map';

const DEBOUNCE_MS = 200;

// TODO: should probably just be a React component
class PandSelection {
    constructor(node) {
        this.node = node;
        this.autocompleteInput = node.querySelector('.pand-selection__autocomplete');
        this.autocompleteContainer = node.querySelector('.pand-selection__autocomplete-results');
        this.valueInput = node.querySelector('.pand-selection__value');

        // parse config
        const { autocompleteUrl, adresPandUrl } = node.dataset;
        Object.assign(this, { autocompleteUrl, adresPandUrl });

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
        const nodes = this.autocompleteContainer.querySelectorAll('.pand-selection__result');
        nodes.forEach(result => {
            result.addEventListener('click', (event) => {
                event.preventDefault();
                const id = result.dataset.id;
                this.getPand(id);
            });
        });
    }

    bindReset() {
        const reset = this.node.querySelector('.pand-selection__reset');
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
                <a href="#" class="pand-selection__result"
                   data-id="${doc.id}" title="${doc.weergavenaam}"
                >${text}</a>
            `;
            return result;

        });
        this.autocompleteContainer.innerHTML = results.join('\n');
        this.autocompleteContainer.classList.add('pand-selection__autocomplete-results--active');
        this.bindResultClicks();
    }

    getPand(id) {
        if (!id) {
            throw new Error('You must provide an appropriate ID');
        }

        apiCall(`${this.adresPandUrl}?id=${id}`)
            .then(response => response.json())
            .then(json => this.showPand(json))
            .catch(console.error)
        ;
    }

    initMap() {
        const mapNode = this.node.querySelector('.pand-selection__map');
        const map = new Map(mapNode, {
            center: [52.1326332, 5.291266],
            zoom: 3,
        });
        map.draw();
        return map;
    }

    showPand(pandLookup) {
        const { pand, adres } = pandLookup;
        const feature = {
            type: 'Feature',
            properties: {
                url: pand.url,
                adres: adres,
                oorspronkelijkBouwjaar: pand.oorspronkelijkBouwjaar,
                status: pand.status,
            },
            geometry: pand.geometrie,
        };
        this.map.showFeature(feature);
        this.valueInput.value = pand.url;
        this.autocompleteContainer.classList.remove('pand-selection__autocomplete-results--active');
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
const selections = document.querySelectorAll('.pand-selection');
Array.from(selections).forEach(node => new PandSelection(node));
