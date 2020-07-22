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

    for (const node of nodes) {
        ReactDOM.render(
            <ZaaktypeSelect zaaktypen={zaaktypen} {...node.dataset} />,
            node
        );
    }
};


init();
