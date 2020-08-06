import React from 'react';
import ReactDOM from 'react-dom';

import Modal from 'react-modal';

import { CaseActivityApp } from './CaseActivityApp';

const CLASS_NAME = 'case-activities';


const init = () => {
    const nodes = document.querySelectorAll(`.${CLASS_NAME}`);

    if (!nodes.length) return;

    // accessibility
    Modal.setAppElement('main.main');

    // TODO: what if multiple nodes are available?
    const pageControls = document.querySelector('.page-controls');

    for (const node of nodes) {

        const props = {
            zaak: node.dataset.zaak,
            endpoint: node.dataset.endpoint,
        };

        ReactDOM.render(
            <CaseActivityApp controlsNode={pageControls} {...props} />,
            node
        );
    }
};

init();
