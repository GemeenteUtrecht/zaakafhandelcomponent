import React from 'react';
import ReactDOM from 'react-dom';

import { CaseActivityList } from './CaseActivityList';

const CLASS_NAME = 'case-activities';


const init = () => {
    const nodes = document.querySelectorAll(`.${CLASS_NAME}`);

    if (!nodes.length) return;

    for (const node of nodes) {

        const props = {
            zaak: node.dataset.zaak,
            endpoint: node.dataset.endpoint,
        };

        ReactDOM.render(
            <CaseActivityList {...props} />,
            node
        );
    }
};

init();
