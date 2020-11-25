import { apiCall } from '../../utils/fetch';
import { initTab } from '../../components/tab';


const initTabs = (parentNode) => {
    const nodes = parentNode.querySelectorAll('.tab');
    for (const node of nodes) {
        initTab(node);
    }
};


const fetchZaakobjecten = (node) => {
    const { url, forZaak } = node.dataset;

    const fullUrl = `${url}?zaak=${forZaak}`;
    apiCall(fullUrl)
        .then(response => response.text())
        .then(content => {node.innerHTML = content;})
        .then(() => initTabs(node))
        .catch(console.error);
};

const nodes = document.querySelectorAll('.fetch-zaakobjecten');
Array.from(nodes).forEach(fetchZaakobjecten);
