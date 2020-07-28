import React from 'react';
import ReactDOM from 'react-dom';

import { ZaaktypeSelect } from '../../components/ZaaktypeSelect';
import { jsonScriptToVar } from '../../utils/json-script';


const init = () => {
    const nodes = document.querySelectorAll('.zaaktypen-select');
    if (!nodes.length) {
        return;
    }

    const zaaktypen = jsonScriptToVar('zaaktypeChoices');
    const selected = jsonScriptToVar('selectedZaaktypen') ?? [];

    for (const node of nodes) {
        ReactDOM.render(
            <ZaaktypeSelect zaaktypen={zaaktypen} selected={selected} {...node.dataset} />,
            node
        );
    }
};


init();
