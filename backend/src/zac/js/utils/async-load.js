import { apiCall } from './fetch';


const loadAndRender = (node, query) => {
    const { url } = node.dataset;

    const fullUrl = `${url}?${query}`;
    return apiCall(fullUrl)
        .then(response => response.text())
        .then(content => {
            node.innerHTML = content;
        })
        .catch(console.error);
};


const _getQuery = () => '';

const loadAsync = (className, getQuery = _getQuery ) => {
    const nodes = document.querySelectorAll('.fetch-messages');
    Array.from(nodes).forEach((node) => {
        loadAndRender(node, getQuery(node));
    });
};


export { loadAsync };
