import { loadAsync } from '../../utils/async-load';

const _getQuery = (node) => {
    const { forZaak } = node.dataset;
    return `zaak=${forZaak}`;
};

loadAsync('.fetch-messages', _getQuery);
